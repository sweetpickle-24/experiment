#!/usr/bin/env python3
"""
Measure the difference between the two receptor -> glomerular projections.

DoorClient._compute_pca_projection runs mean-centred PCA when scikit-learn is
importable and uncentred SVD otherwise. scikit-learn is pinned in
requirements.txt but is not installed in this environment, so every recorded
run used the uncentred path.

This script does NOT install scikit-learn and does NOT change which path the
runtime takes. It reproduces sklearn's PCA arithmetic with numpy
(mean-centre, then SVD, components = Vt) purely to quantify what would change,
and writes the comparison to results/final/projection_path_comparison.json.

sklearn.decomposition.PCA.fit computes exactly this: it subtracts the column
mean, takes the SVD of the centred matrix, and stores Vt as components_. So the
numpy reconstruction below is arithmetically the same projection sklearn would
produce, up to per-component sign.
"""

import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from hive.data.door_client import DoorClient  # noqa: E402
from validation_utils import results_path, run_metadata, set_seed  # noqa: E402

N_COMPONENTS = 20
SEED = 42

# Odorants the concentration-invariance run uses, plus two more for spread.
PROBE_ODORANTS = [
    'benzaldehyde', '2-heptanone', 'isopentyl_acetate',
    'ethyl_acetate', 'acetic_acid', '1-octanol',
]


def uncentered_svd_projection(matrix, k):
    """Exactly what DoorClient does when scikit-learn is absent."""
    U, S, Vt = np.linalg.svd(matrix, full_matrices=False)
    total = float(np.sum(S ** 2))
    return Vt[:k].T, (float(np.sum(S[:k] ** 2) / total) if total > 0 else 0.0)


def sklearn_equivalent_pca_projection(matrix, k):
    """
    Mean-centred PCA, arithmetically equivalent to sklearn PCA(n_components=k).

    sklearn subtracts the column mean, takes the SVD of the centred matrix and
    keeps Vt as components_; explained_variance_ratio_ is the share of centred
    squared singular values.
    """
    mean = matrix.mean(axis=0, keepdims=True)
    centred = matrix - mean
    U, S, Vt = np.linalg.svd(centred, full_matrices=False)
    total = float(np.sum(S ** 2))
    return Vt[:k].T, (float(np.sum(S[:k] ** 2) / total) if total > 0 else 0.0)


def project(response, basis):
    """The same post-processing map_to_glomerular_pattern applies."""
    pattern = response @ basis
    pattern = np.maximum(pattern, 0)
    norm = np.linalg.norm(pattern)
    if norm > 0:
        pattern = pattern / norm
    return pattern.astype(np.float32)


def main():
    set_seed(SEED)
    client = DoorClient()
    # Force the runtime projection so projection_method is populated and the
    # metadata records which path this environment actually takes.
    client.map_to_glomerular_pattern(
        np.zeros(len(client.receptor_names), dtype=np.float32)
    )
    matrix = np.asarray(client.response_matrix, dtype=np.float64)

    svd_basis, svd_var = uncentered_svd_projection(matrix, N_COMPONENTS)
    pca_basis, pca_var = sklearn_equivalent_pca_projection(matrix, N_COMPONENTS)

    per_odorant = {}
    corrs, cosines, sparsity_delta = [], [], []
    for name in PROBE_ODORANTS:
        resolved = client.resolve_odorant_name(name)
        response = np.asarray(client.get_odorant_response(resolved), dtype=np.float64)

        p_svd = project(response, svd_basis)
        p_pca = project(response, pca_basis)

        if np.std(p_svd) > 0 and np.std(p_pca) > 0:
            r = float(np.corrcoef(p_svd, p_pca)[0, 1])
        else:
            r = float('nan')
        denom = np.linalg.norm(p_svd) * np.linalg.norm(p_pca)
        cos = float(np.dot(p_svd, p_pca) / denom) if denom > 0 else float('nan')

        nz_svd = int(np.count_nonzero(p_svd))
        nz_pca = int(np.count_nonzero(p_pca))

        per_odorant[resolved] = {
            'pearson_r_between_paths': r,
            'cosine_between_paths': cos,
            'nonzero_channels_uncentered_svd': nz_svd,
            'nonzero_channels_sklearn_pca': nz_pca,
            'pattern_uncentered_svd': [float(x) for x in p_svd],
            'pattern_sklearn_pca': [float(x) for x in p_pca],
        }
        corrs.append(r)
        cosines.append(cos)
        sparsity_delta.append(nz_pca - nz_svd)

    # Pairwise odour-to-odour structure under each projection. This is what
    # downstream similarity and decorrelation measures actually consume.
    def pairwise(basis):
        pats = [project(np.asarray(client.get_odorant_response(n), dtype=np.float64), basis)
                for n in PROBE_ODORANTS]
        out = []
        for i in range(len(pats)):
            for j in range(i + 1, len(pats)):
                a, b = pats[i], pats[j]
                d = np.linalg.norm(a) * np.linalg.norm(b)
                out.append(float(np.dot(a, b) / d) if d > 0 else 0.0)
        return out

    pw_svd = pairwise(svd_basis)
    pw_pca = pairwise(pca_basis)
    pw_shift = [float(b - a) for a, b in zip(pw_svd, pw_pca)]

    results = {
        'purpose': (
            'Quantify the difference between the uncentered-SVD projection that '
            'runs when scikit-learn is absent and the mean-centred PCA that runs '
            'when it is present. scikit-learn was NOT installed and the runtime '
            'path was NOT changed; the PCA basis here is reconstructed with numpy '
            'using the same arithmetic sklearn.decomposition.PCA performs.'
        ),
        'config': run_metadata(duration_ms=None, seed=SEED, door_client=client,
                               n_components=N_COMPONENTS,
                               probe_odorants=PROBE_ODORANTS),
        'runtime_projection_method': client.projection_method,
        'variance_retained': {
            'uncentered_svd_squared_magnitude_fraction': svd_var,
            'sklearn_pca_explained_variance_ratio': pca_var,
            'note': (
                'These two are not the same quantity. The uncentered figure is the '
                'share of total squared magnitude, which includes the mean; the PCA '
                'figure is the share of variance about the mean. They are reported '
                'side by side only because the code prints one in place of the other.'
            ),
        },
        'per_odorant': per_odorant,
        'summary': {
            'mean_pearson_r_between_paths': float(np.nanmean(corrs)),
            'min_pearson_r_between_paths': float(np.nanmin(corrs)),
            'mean_cosine_between_paths': float(np.nanmean(cosines)),
            'min_cosine_between_paths': float(np.nanmin(cosines)),
            'mean_nonzero_channel_change': float(np.mean(sparsity_delta)),
            'pairwise_cosine_uncentered_svd': pw_svd,
            'pairwise_cosine_sklearn_pca': pw_pca,
            'max_abs_pairwise_cosine_shift': float(np.max(np.abs(pw_shift))),
            'mean_abs_pairwise_cosine_shift': float(np.mean(np.abs(pw_shift))),
        },
    }

    out = results_path('projection_path_comparison.json')
    with open(out, 'w') as f:
        json.dump(results, f, indent=2)

    print(f"\nRuntime projection path: {client.projection_method}")
    print(f"Variance/magnitude retained: uncentered SVD {svd_var:.4f}, PCA {pca_var:.4f}")
    print("\nPer-odorant agreement between the two projections:")
    for name, d in per_odorant.items():
        print(f"  {name:20s} r={d['pearson_r_between_paths']:+.4f} "
              f"cos={d['cosine_between_paths']:.4f} "
              f"nonzero {d['nonzero_channels_uncentered_svd']} -> "
              f"{d['nonzero_channels_sklearn_pca']}")
    s = results['summary']
    print(f"\nmean r  = {s['mean_pearson_r_between_paths']:+.4f}")
    print(f"min r   = {s['min_pearson_r_between_paths']:+.4f}")
    print(f"mean cos= {s['mean_cosine_between_paths']:.4f}")
    print(f"max |pairwise cosine shift| = {s['max_abs_pairwise_cosine_shift']:.4f}")
    print(f"\nWritten to {out}")


if __name__ == '__main__':
    main()
