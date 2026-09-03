"""
Adapter for the four standalone validation scripts in tests/.

tests/validate_odor_similarity.py, validate_odor_mixtures.py,
validate_discrimination_threshold.py and validate_learning_plasticity.py were
written against an engine API that never existed in this repository, so none of
them had ever executed. Each one failed in the same four ways:

  1. ``SparseProbabilisticBrain(num_neurons=..., dt=..., use_mlx=...)`` — the
     constructor takes a ``connectome``; there are no ``num_neurons`` or ``dt``
     keywords. This raised TypeError first, before any of the others could.
  2. ``brain.load_connectome_simple(synapses)`` — never defined. Coupling is
     built inside the constructor from the connectome.
  3. ``door_client.project_to_pca_basis(name)`` — never defined. It is now a
     documented alias of ``get_glomerular_pattern``.
  4. ``brain.inject_external_input('ORN', pattern, strength=...)`` — never
     defined. The engine's entry point is ``inject_odor``, which drives
     PROJECTION NEURONS, not ORNs. That is a real difference in what is being
     stimulated, not just a rename, and it is recorded here rather than hidden:
     these scripts intended to inject at the receptor stage and the engine
     injects one stage downstream.

They also referenced odorants absent from the DoOR matrix ('geosmin',
'E2-hexenal'), which now raises OdorantNotFoundError instead of degrading to a
zero vector. See ODOR_AUDIT.md.

This module supplies the missing pieces once so the fix is not copied into four
files, and keeps the scripts on exactly the same engine configuration as
scripts/run_all_validations.py, so their numbers are comparable with the
suite's rather than being a second, differently-configured measurement.
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from validation_utils import init_olfactory_brain  # noqa: E402
from hive.data.door_client import OdorantNotFoundError  # noqa: E402

#: Odorants these scripts named that are not keys in the DoOR matrix, with the
#: substitution used by scripts/run_all_validations.py so the two are
#: comparable. 'geosmin' has no entry at all; before 2026-09-03 the lookup
#: returned a zero vector and a zero pattern correlates with itself at exactly
#: 1.0, which silently inflated every score computed over it.
ABSENT_ODORANTS = {
    'geosmin': 'isopentyl_acetate',
    'E2-hexenal': None,          # no comparable substitute; dropped
}


def build_brain(use_mlx=False, seed=42, projection='sklearn_pca',
                glomerular_mapping='position'):
    """
    Build the engine the way the suite builds it.

    Returns (brain, door_client, connectome). Defaults to CPU because these
    scripts write reported numbers.
    """
    return init_olfactory_brain(use_mlx=use_mlx, seed=seed,
                               projection=projection,
                               glomerular_mapping=glomerular_mapping)


def resolve_odor_list(door_client, names, logger=None):
    """
    Reduce a script's hardcoded odour list to names the matrix actually has.

    Returns (resolved, report). Substitutions and drops are returned rather
    than applied silently, so a result file can record which odours were
    actually measured instead of which ones the source code names.
    """
    resolved, report = [], []
    for name in names:
        target = ABSENT_ODORANTS.get(name, name)
        if target is None:
            report.append({'requested': name, 'used': None,
                           'reason': 'absent from DoOR matrix, no substitute'})
            continue
        try:
            actual = door_client.resolve_odorant_name(target)
        except OdorantNotFoundError as exc:
            report.append({'requested': name, 'used': None,
                           'reason': f'unresolvable: {exc}'})
            continue
        if actual in resolved:
            report.append({'requested': name, 'used': None,
                           'reason': f'duplicate of {actual}'})
            continue
        resolved.append(actual)
        if actual != name:
            report.append({'requested': name, 'used': actual,
                           'reason': 'substituted' if name in ABSENT_ODORANTS
                                     else 'name normalised'})

    if logger is not None:
        for r in report:
            logger.warning("odour %r -> %r (%s)", r['requested'], r['used'],
                           r['reason'])
    return resolved, report


def inject(brain, pattern, strength=50.0):
    """
    Stand-in for the scripts' ``inject_external_input('ORN', ...)``.

    Drives projection neurons, because that is where the engine injects. The
    scripts asked for the ORN stage; the difference is documented in this
    module's docstring and in each script's header.
    """
    brain.inject_odor(pattern, strength=strength)


def kc_mbon_weight_stats(brain, connectome):
    """
    Summarise KC->MBON synaptic weights.

    tests/validate_learning_plasticity.py iterated ``brain.synapses`` as
    ``(pre_idx, post_idx, weight)`` triples and identified KC->MBON synapses by
    hardcoded index ranges ("ORNs: 0-2278, PNs: 2279-4476, ... KCs: 5198-10476,
    MBONs: 10477-10572"). Neither existed: the engine stores parallel
    ``pre_indices`` / ``post_indices`` / ``syn_weights`` arrays, and neuron
    order is connectome iteration order, not grouped by cell type, so those
    ranges select an arbitrary set of neurons.

    Cell type is resolved here through the same classifier the rest of the
    repository uses.
    """
    from hive.substrate.olfactory_subgraph import classify_olfactory_neuron

    region_of_idx = {}
    for nid, neuron in connectome.neurons.items():
        i = brain.id_to_idx.get(nid)
        if i is not None:
            region_of_idx[i] = classify_olfactory_neuron(neuron)

    pre = np.asarray(brain.pre_indices)
    post = np.asarray(brain.post_indices)
    w = np.asarray(brain.syn_weights.tolist() if hasattr(brain.syn_weights, 'tolist')
                   else brain.syn_weights, dtype=np.float64)

    is_kc = np.array([region_of_idx.get(int(i)) == 'KC' for i in pre])
    is_mbon = np.array([region_of_idx.get(int(i)) == 'MBON' for i in post])
    sel = is_kc & is_mbon

    if not sel.any():
        return {'n_kc_to_mbon_synapses': 0}
    ws = w[sel]
    return {
        'n_kc_to_mbon_synapses': int(sel.sum()),
        'weight_mean': float(ws.mean()),
        'weight_sum': float(ws.sum()),
        'weight_max': float(ws.max()),
        'weight_min': float(ws.min()),
    }
