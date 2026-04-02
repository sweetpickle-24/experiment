"""
DoOR 2.0 Data Downloader
========================

**Date**: 2026-03-24

Downloads the real Drosophila Olfactory Response (DoOR) 2.0 database from the
ropensci/DoOR.data GitHub repository (one CSV per receptor) and assembles a
consensus response matrix saved as data/door_consensus_matrix.npy.

Usage:
    python scripts/download_door_data.py

Output:
    data/door_consensus_matrix.npy   -- 693 odorants × 40 receptors

DoOR 2.0 reference:
    Münch D. & Galizia C.G. (2016). DoOR 2.0 — Comprehensive Mapping of
    Drosophila melanogaster Odorant Responses. Sci Rep 6, 21841.
    https://doi.org/10.1038/srep21841
"""

import csv
import io
import json
import time
import threading
import numpy as np
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import URLError

# ── Paths ──────────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).parent.parent
DATA_DIR  = REPO_ROOT / "data"
OUT_FILE  = DATA_DIR / "door_consensus_matrix.npy"

BASE_RAW   = "https://raw.githubusercontent.com/ropensci/DoOR.data/master/data"
BASE_API   = "https://api.github.com/repos/ropensci/DoOR.data/git/trees/master?recursive=1"

# Canonical 40-receptor set used throughout the codebase
DOOR_RECEPTORS = [
    'Or10a', 'Or13a', 'Or22a', 'Or35a', 'Or42a', 'Or42b', 'Or43a', 'Or43b',
    'Or45a', 'Or45b', 'Or46a', 'Or47a', 'Or47b', 'Or49a', 'Or49b', 'Or56a',
    'Or59a', 'Or59b', 'Or63a', 'Or65a', 'Or67a', 'Or67b', 'Or67c', 'Or69a',
    'Or71a', 'Or82a', 'Or83a', 'Or83b', 'Or85a', 'Or85b', 'Or85c', 'Or85d',
    'Or85e', 'Or85f', 'Or88a', 'Or92a', 'Or98a', 'Or98b', 'Gr21a', 'Gr63a',
]

# ── HTTP helpers ───────────────────────────────────────────────────────

def fetch_text(url: str, timeout: int = 20) -> str | None:
    try:
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urlopen(req, timeout=timeout) as resp:
            return resp.read().decode("utf-8")
    except Exception:
        return None


def fetch_json(url: str) -> dict | None:
    text = fetch_text(url)
    if text:
        try:
            return json.loads(text)
        except Exception:
            pass
    return None


# ── DoOR CSV parsing ───────────────────────────────────────────────────

def parse_receptor_csv(receptor: str, text: str) -> dict[str, float]:
    """
    Parse one Or*.csv file and return {odorant_name: mean_response}.

    CSV format (semicolon-delimited):
        header (18-19 cols):  Class;Name;InChIKey;CID;CAS;Study1;Study2;...
        data rows (19-20 cols): row_idx;Class;Name;InChIKey;CID;CAS;val1;val2;...

    The data rows have ONE extra leading integer index column that is absent
    from the header, so all data-column indices are header-index + 1.
    """
    reader = csv.reader(io.StringIO(text), delimiter=';')
    rows   = list(reader)
    if len(rows) < 2:
        return {}

    header = [h.strip().strip('"') for h in rows[0]]

    # Detect offset: if data[0] is an integer the header has no leading index col
    sample_row   = rows[1] if len(rows) > 1 else []
    leading_idx  = 0
    if sample_row:
        try:
            int(sample_row[0].strip().strip('"'))
            leading_idx = 1  # data rows start with a row number not in header
        except ValueError:
            leading_idx = 0

    try:
        name_col = header.index('Name') + leading_idx
    except ValueError:
        name_col = 1 + leading_idx  # fallback

    # Study columns begin after the 5 metadata cols (Class, Name, InChIKey, CID, CAS)
    study_start = 5 + leading_idx

    result: dict[str, float] = {}
    for row in rows[1:]:
        if not row or len(row) <= name_col:
            continue
        raw_name = row[name_col].strip().strip('"')
        if not raw_name or raw_name.upper() in ('NA', 'SFR', ''):
            continue
        name = raw_name.replace(' ', '_').lower()
        vals = []
        for cell in row[study_start:]:
            c = cell.strip().strip('"')
            if c and c.upper() not in ('NA', 'NAN', ''):
                try:
                    vals.append(float(c))
                except ValueError:
                    pass
        if vals:
            result[name] = float(np.mean(vals))

    return result


# ── Fetch all receptor files in parallel ──────────────────────────────

def fetch_all_receptors(receptor_names: list[str]) -> dict[str, dict[str, float]]:
    """Download all receptor CSVs concurrently (max 8 threads)."""
    results: dict[str, dict[str, float]] = {}
    lock = threading.Lock()
    sem  = threading.Semaphore(8)

    def worker(receptor: str):
        with sem:
            url  = f"{BASE_RAW}/{receptor}.csv"
            text = fetch_text(url)
            if text:
                data = parse_receptor_csv(receptor, text)
                with lock:
                    results[receptor] = data
                    print(f"  ✓ {receptor}: {len(data)} odorants")
            else:
                with lock:
                    print(f"  ✗ {receptor}: download failed")

    threads = [threading.Thread(target=worker, args=(r,)) for r in receptor_names]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    return results


# ── Build combined matrix ──────────────────────────────────────────────

def build_matrix(receptor_data: dict[str, dict[str, float]],
                 target_receptors: list[str]) -> tuple[list[str], np.ndarray]:
    """
    Combine per-receptor dicts into a single (n_odorants × n_receptors) matrix.
    Rows are L2-normalised.
    """
    # Collect all unique odorant names
    all_names: set[str] = set()
    for data in receptor_data.values():
        all_names.update(data.keys())

    odorant_list = sorted(all_names)
    n_odorants   = len(odorant_list)
    n_receptors  = len(target_receptors)

    matrix = np.zeros((n_odorants, n_receptors), dtype=np.float32)
    name_to_idx = {name: i for i, name in enumerate(odorant_list)}

    for j, receptor in enumerate(target_receptors):
        if receptor in receptor_data:
            for odorant, response in receptor_data[receptor].items():
                if odorant in name_to_idx:
                    matrix[name_to_idx[odorant], j] = response

    # L2-normalise each row
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1.0, norms)
    matrix /= norms

    # Remove all-zero rows (odorants with no known responses)
    active_mask  = np.any(matrix != 0, axis=1)
    matrix       = matrix[active_mask]
    odorant_list = [odorant_list[i] for i, m in enumerate(active_mask) if m]

    return odorant_list, matrix


# ── Expanded synthetic fallback ────────────────────────────────────────

def build_expanded_synthetic() -> tuple[list[str], list[str], np.ndarray]:
    """
    Generate an expanded synthetic dataset (~250 odorants, 12 families).
    Used only when real DoOR download fails.
    """
    rng = np.random.default_rng(42)

    families = {
        "ester":     ["ethyl_acetate", "methyl_acetate", "butyl_acetate", "ethyl_butyrate",
                      "pentyl_acetate", "isoamyl_acetate", "hexyl_acetate", "propyl_acetate",
                      "octyl_acetate", "ethyl_hexanoate", "methyl_hexanoate", "ethyl_valerate",
                      "isobutyl_acetate", "geranyl_acetate", "linalyl_acetate"],
        "alcohol":   ["ethanol", "methanol", "1-butanol", "1-hexanol", "1-octanol",
                      "2-heptanol", "3-octanol", "1-pentanol", "2-butanol", "geraniol",
                      "linalool", "citronellol", "nerol", "farnesol", "phytol"],
        "ketone":    ["acetone", "2-butanone", "2-pentanone", "2-heptanone",
                      "methyl_vinyl_ketone", "6-methyl-5-hepten-2-one", "acetophenone",
                      "nonanone", "decanone", "methylisobutylketone"],
        "aldehyde":  ["acetaldehyde", "benzaldehyde", "propanal", "butanal", "pentanal",
                      "hexanal", "heptanal", "octanal", "nonanal", "decanal",
                      "phenylacetaldehyde", "citral", "trans-2-hexenal", "2-methylbutanal"],
        "aromatic":  ["benzene", "toluene", "phenol", "eugenol", "guaiacol",
                      "methyl_salicylate", "benzyl_alcohol", "anisole", "cresol",
                      "thymol", "carvacrol", "safrole", "myristicin"],
        "acid":      ["acetic_acid", "propionic_acid", "butyric_acid", "valeric_acid",
                      "hexanoic_acid", "octanoic_acid", "decanoic_acid", "lactic_acid",
                      "citric_acid", "4-methylpentanoic_acid"],
        "terpene":   ["limonene", "alpha-pinene", "beta-pinene", "myrcene", "ocimene",
                      "alpha-terpineol", "borneol", "camphor", "carvone", "menthol",
                      "pulegone", "fenchone", "isopinocamphone"],
        "pheromone": ["cis-vaccenyl_acetate", "11-cis-vaccenyl_acetate", "methyl_laurate",
                      "palmitoleic_acid", "7-tricosene", "7-11-heptacosadiene"],
        "aversive":  ["co2", "geosmin", "putrescine", "cadaverine", "trimethylamine",
                      "dimethyl_disulfide", "methyl_mercaptan", "hydrogen_sulfide"],
        "lactone":   ["gamma-butyrolactone", "delta-valerolactone", "gamma-caprolactone",
                      "beta-propiolactone", "epsilon-caprolactone"],
        "amine":     ["methylamine", "dimethylamine", "trimethylamine_b", "isobutylamine",
                      "phenylethylamine", "tyramine", "histamine", "agmatine"],
        "other":     ["diacetyl", "acetoin", "furfural", "pyrazine",
                      "methyl_pyrazine", "2-acetylpyridine", "indole", "skatole",
                      "geranylacetone", "ionone", "2-heptanone", "benzyl_acetate"],
    }

    n_receptors   = len(DOOR_RECEPTORS)
    family_cores  = {
        fname: rng.choice(n_receptors, size=rng.integers(3, 7), replace=False)
        for fname in families
    }

    all_names:     list[str]        = []
    all_responses: list[np.ndarray] = []
    seen: set[str] = set()

    for fname, odorant_list in families.items():
        core = family_cores[fname]
        for odor_name in odorant_list:
            if odor_name in seen:
                continue
            seen.add(odor_name)
            resp = np.zeros(n_receptors, dtype=np.float32)
            resp[core] = rng.lognormal(0.5, 0.5, len(core)).astype(np.float32)
            n_extra = rng.integers(2, 8)
            extra   = rng.choice(
                [i for i in range(n_receptors) if i not in core],
                size=min(n_extra, n_receptors - len(core)),
                replace=False,
            )
            resp[extra] = rng.lognormal(0.2, 0.8, len(extra)).astype(np.float32)
            norm = np.linalg.norm(resp)
            if norm > 0:
                resp /= norm
            all_names.append(odor_name)
            all_responses.append(resp)

    return all_names, DOOR_RECEPTORS, np.stack(all_responses, axis=0)


# ── Main ───────────────────────────────────────────────────────────────

def main():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 70)
    print("DoOR 2.0 DATA DOWNLOADER")
    print("=" * 70)
    print(f"Target: {OUT_FILE}")
    print()

    # Discover receptor CSV files
    print("Querying GitHub for receptor file list...")
    tree_data = fetch_json(BASE_API)
    or_files  = []
    if tree_data and "tree" in tree_data:
        or_files = [
            Path(item["path"]).stem            # e.g. "Or22a"
            for item in tree_data["tree"]
            if item["path"].startswith("data/Or") and item["path"].endswith(".csv")
        ]
    print(f"  Found {len(or_files)} OR receptor files")

    # Intersect with canonical 40-receptor set
    target_receptors = [r for r in DOOR_RECEPTORS if r in or_files]
    missing          = [r for r in DOOR_RECEPTORS if r not in or_files]
    if missing:
        print(f"  Receptors not in repo (will be zero-filled): {missing}")

    odorant_names: list[str] = []
    matrix:        np.ndarray | None = None
    receptor_names: list[str] = DOOR_RECEPTORS
    source = "unknown"

    if target_receptors:
        print(f"\nDownloading {len(target_receptors)} receptor CSVs (parallel)...")
        t0             = time.perf_counter()
        receptor_data  = fetch_all_receptors(target_receptors)
        elapsed        = time.perf_counter() - t0
        print(f"  Done in {elapsed:.1f}s — {len(receptor_data)}/{len(target_receptors)} succeeded")

        if receptor_data:
            print("\nBuilding combined matrix...")
            odorant_names, matrix = build_matrix(receptor_data, DOOR_RECEPTORS)
            source = f"DoOR 2.0 real data ({len(receptor_data)} receptors)"
            print(f"  {len(odorant_names)} odorants × {len(DOOR_RECEPTORS)} receptors")

    if matrix is None or len(odorant_names) < 10:
        print("\nInsufficient data; falling back to expanded synthetic dataset...")
        odorant_names, receptor_names, matrix = build_expanded_synthetic()
        source = "expanded synthetic (DoOR download failed)"
        print(f"  Generated {len(odorant_names)} odorants × {len(receptor_names)} receptors")

    # Save
    np.save(OUT_FILE, {
        "responses":  matrix,
        "odorants":   odorant_names,
        "receptors":  receptor_names,
        "source":     source,
    })

    print(f"\n✓ Saved to {OUT_FILE}")
    print(f"  Source   : {source}")
    print(f"  Odorants : {len(odorant_names)}")
    print(f"  Receptors: {len(receptor_names)}")
    print(f"  Shape    : {matrix.shape}")
    size_kb = OUT_FILE.stat().st_size / 1024
    print(f"  File size: {size_kb:.1f} KB")

    norms = np.linalg.norm(matrix, axis=1)
    print(f"  Row norms: mean {norms.mean():.4f}  min {norms.min():.4f}  max {norms.max():.4f}")

    print()
    print("=" * 70)
    print("Done. Run scripts/batch_encode_odors.py next.")


if __name__ == "__main__":
    main()
