"""
SmellDatabase — Unified Chemical Space for Smell Synthesis
==========================================================

**Date**: 2026-03-24

Wraps DoorClient + precomputed KC fingerprints into a single object that:
  - Provides O(1) lookup of any odorant's glomerular and KC patterns
  - Runs cosine-similarity search over the KC fingerprint space
  - Encodes new odorants on-demand using a SparseProbabilisticBrain

This is the data backbone for the /api/smell/* endpoints and the
SmellSynthesisPanel frontend component.

Usage
-----
    from hive.data.smell_database import SmellDatabase

    db = SmellDatabase()                 # loads door_consensus_matrix.npy
    db.load_kc_fingerprints("data/digital_smell_database_full.json")

    entry = db.find_by_name("benzaldehyde")
    matches = db.find_by_kc_pattern(kc_vector, top_k=5)
"""

import json
import time
import numpy as np
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

# ── Default paths ──────────────────────────────────────────────────────
_REPO_ROOT   = Path(__file__).parent.parent.parent
_DOOR_NPY    = _REPO_ROOT / "data" / "door_consensus_matrix.npy"
_KC_JSON     = _REPO_ROOT / "data" / "digital_smell_database_full.json"

CHEMICAL_FAMILIES = {
    "ester":    ["acetate", "butyrate", "propionate", "lactate", "hexanoate",
                 "valerate", "formate", "benzoate"],
    "alcohol":  ["ethanol", "methanol", "butanol", "hexanol", "octanol",
                 "heptanol", "pentanol", "geraniol", "linalool", "borneol",
                 "menthol", "citronellol", "nerol"],
    "ketone":   ["ketone", "acetone", "butanone", "pentanone", "heptanone",
                 "hexanone", "acetophenone"],
    "aldehyde": ["aldehyde", "aldehyd", "benzaldehyde", "propanal", "butanal",
                 "pentanal", "hexanal", "heptanal", "citral", "nonanal"],
    "acid":     ["acid", "formic", "acetic", "propionic", "butyric", "valeric",
                 "hexanoic", "octanoic"],
    "terpene":  ["limonene", "pinene", "myrcene", "ocimene", "terpineol",
                 "camphor", "carvone", "fenchone", "pulegone", "geranyl"],
    "aromatic": ["benzene", "toluene", "phenol", "guaiacol", "eugenol",
                 "anisole", "cresol", "thymol", "safrole", "indole"],
    "amine":    ["amine", "putrescine", "cadaverine", "trimethylamine",
                 "ethanolamine", "phenylethylamine", "tyramine"],
    "aversive": ["co2", "geosmin", "mercaptan", "sulfide", "disulfide",
                 "skatole", "hydrogen_sulfide"],
    "pheromone":["vaccenyl", "pheromone", "cis-vaccenyl", "7-tricosene"],
    "lactone":  ["lactone", "butyrolactone", "valerolactone", "caprolactone"],
    "other":    [],  # catch-all
}


def classify_family(name: str) -> str:
    nl = name.lower()
    for family, keywords in CHEMICAL_FAMILIES.items():
        if family == "other":
            continue
        for kw in keywords:
            if kw in nl:
                return family
    return "other"


# ── Data classes ────────────────────────────────────────────────────────

@dataclass
class SmellEntry:
    """One odorant in the database."""
    name:          str
    family:        str
    glom_pattern:  list[float]           # 20-dim glomerular pattern
    kc_pattern:    list[float] | None = None   # 5279-dim KC fingerprint (if encoded)
    kc_sparsity:   float             = 0.0
    kc_active:     int               = 0

    def to_dict(self, include_kc: bool = True) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name":         self.name,
            "family":       self.family,
            "glom_pattern": self.glom_pattern,
            "kc_sparsity":  self.kc_sparsity,
            "kc_active":    self.kc_active,
        }
        if include_kc and self.kc_pattern is not None:
            d["kc_pattern"] = self.kc_pattern
        return d


@dataclass
class OdorMatch:
    """A hit from a similarity search."""
    name:       str
    family:     str
    similarity: float          # cosine similarity [0, 1]
    glom_pattern: list[float] | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "name":       self.name,
            "family":     self.family,
            "similarity": float(self.similarity),
        }
        if self.glom_pattern is not None:
            d["glom_pattern"] = self.glom_pattern
        return d


# ── SmellDatabase ─────────────────────────────────────────────────────

class SmellDatabase:
    """
    Unified chemical-space database for smell synthesis.

    Attributes
    ----------
    entries       : dict[name → SmellEntry]
    kc_matrix     : np.ndarray (n_odorants × n_kc)  — only rows with KC data
    kc_names      : list[str]  — row-aligned with kc_matrix
    """

    def __init__(self, door_npy: str | Path = _DOOR_NPY,
                 kc_json: str | Path | None = _KC_JSON):
        self.entries:    dict[str, SmellEntry] = {}
        self.kc_matrix:  np.ndarray | None     = None
        self.kc_names:   list[str]             = []

        self._load_door(Path(door_npy))
        if kc_json and Path(kc_json).exists():
            self.load_kc_fingerprints(Path(kc_json))

    # ── Loading ────────────────────────────────────────────────────────

    def _load_door(self, path: Path) -> None:
        """Load glomerular patterns from door_consensus_matrix.npy."""
        if not path.exists():
            print(f"⚠ SmellDatabase: door file not found at {path}")
            return

        data = np.load(path, allow_pickle=True).item()
        responses:  np.ndarray  = data["responses"]   # (n_odorants, n_receptors)
        odorant_names: list[str] = data["odorants"]

        # PCA: 40 receptors → 20 glomerular channels
        glom_patterns = self._receptors_to_glom(responses)

        for i, name in enumerate(odorant_names):
            glom = glom_patterns[i].tolist()
            self.entries[name] = SmellEntry(
                name=name,
                family=classify_family(name),
                glom_pattern=glom,
            )

        source = data.get("source", "unknown")
        print(f"✓ SmellDatabase: loaded {len(self.entries)} odorants "
              f"(source: {source})")

    def _receptors_to_glom(self, responses: np.ndarray,
                            n_components: int = 20) -> np.ndarray:
        """Map n_receptors → 20 glomerular channels via SVD projection."""
        from numpy.linalg import svd

        n_odorants = responses.shape[0]
        if responses.shape[1] <= n_components:
            # Already ≤ 20 dims; zero-pad
            pad = np.zeros((n_odorants, n_components - responses.shape[1]),
                           dtype=np.float32)
            proj = np.concatenate([responses, pad], axis=1)
        else:
            U, S, Vt = svd(responses, full_matrices=False)
            proj_matrix = Vt[:n_components].T         # (n_receptors, n_components)
            proj = responses @ proj_matrix            # (n_odorants, n_components)

        # ReLU + L2 normalise
        proj = np.maximum(proj, 0).astype(np.float32)
        norms = np.linalg.norm(proj, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        return proj / norms

    def load_kc_fingerprints(self, path: Path) -> int:
        """
        Load precomputed KC fingerprints from batch_encode_odors output.

        Returns number of entries updated.
        """
        if not path.exists():
            return 0

        with open(path) as f:
            payload = json.load(f)

        # Two shapes are accepted. Since 2026-09-05 the encoder writes
        # {"config": {...}, "entries": [...]} so the artifact carries the
        # pipeline it was produced under; before that it wrote a bare list.
        if isinstance(payload, dict):
            records = payload.get("entries", [])
            self.kc_source_config = payload.get("config")
        else:
            records = payload
            self.kc_source_config = None

        updated = 0
        kc_rows:   list[np.ndarray] = []
        kc_names_: list[str]        = []

        for rec in records:
            name = rec.get("odor_name") or rec.get("name", "")
            kc   = rec.get("kc_pattern") or rec.get("kc_response", {}).get("pattern")
            if not name or kc is None:
                continue

            kc_arr = np.array(kc, dtype=np.float32)

            # Update entry
            if name not in self.entries:
                glom = rec.get("glomerular_pattern", [0.0] * 20)
                self.entries[name] = SmellEntry(
                    name=name,
                    family=classify_family(name),
                    glom_pattern=glom,
                )

            entry = self.entries[name]
            entry.kc_pattern  = kc_arr.tolist()
            entry.kc_active   = int(np.sum(kc_arr > 0.01))
            entry.kc_sparsity = float(entry.kc_active / len(kc_arr))

            kc_rows.append(kc_arr)
            kc_names_.append(name)
            updated += 1

        if kc_rows:
            self.kc_matrix = np.stack(kc_rows, axis=0)   # (n, kc_dim)
            self.kc_names  = kc_names_
            # L2-normalise for cosine similarity
            norms = np.linalg.norm(self.kc_matrix, axis=1, keepdims=True)
            norms = np.where(norms == 0, 1.0, norms)
            self.kc_matrix /= norms

        print(f"✓ SmellDatabase: loaded {updated} KC fingerprints")
        return updated

    # ── Queries ────────────────────────────────────────────────────────

    def get_all_entries(self, include_kc: bool = False) -> list[dict]:
        return [e.to_dict(include_kc=include_kc) for e in self.entries.values()]

    def find_by_name(self, name: str) -> SmellEntry | None:
        return self.entries.get(name)

    def find_by_kc_pattern(self, kc: np.ndarray,
                            top_k: int = 5) -> list[OdorMatch]:
        """
        Cosine-similarity search over precomputed KC fingerprint matrix.

        Args
            kc    : Query KC pattern (any length; will be truncated/padded).
            top_k : Number of results to return.

        Returns
            List of OdorMatch sorted by descending similarity.
        """
        if self.kc_matrix is None or len(self.kc_names) == 0:
            return self._glom_fallback(kc, top_k)

        # Align dimensions
        q = np.array(kc, dtype=np.float32).flatten()
        n = self.kc_matrix.shape[1]
        if len(q) < n:
            q = np.pad(q, (0, n - len(q)))
        else:
            q = q[:n]

        norm = np.linalg.norm(q)
        if norm < 1e-9:
            return []
        q_unit = q / norm

        sims   = self.kc_matrix @ q_unit           # (n_entries,)
        top_idx = np.argsort(sims)[::-1][:top_k]

        results = []
        for idx in top_idx:
            name  = self.kc_names[idx]
            entry = self.entries.get(name)
            results.append(OdorMatch(
                name=name,
                family=entry.family if entry else "other",
                similarity=float(sims[idx]),
                glom_pattern=entry.glom_pattern if entry else None,
            ))
        return results

    def find_by_glom_pattern(self, glom: np.ndarray,
                              top_k: int = 5) -> list[OdorMatch]:
        """Cosine-similarity search over glomerular patterns."""
        q = np.array(glom, dtype=np.float32).flatten()
        norm = np.linalg.norm(q)
        if norm < 1e-9:
            return []
        q_unit = q / norm

        names   = list(self.entries.keys())
        gloms   = np.stack([np.array(e.glom_pattern, dtype=np.float32)
                            for e in self.entries.values()], axis=0)
        g_norms = np.linalg.norm(gloms, axis=1, keepdims=True)
        g_norms = np.where(g_norms == 0, 1.0, g_norms)
        gloms_u = gloms / g_norms

        sims    = gloms_u @ q_unit
        top_idx = np.argsort(sims)[::-1][:top_k]

        results = []
        for idx in top_idx:
            name  = names[idx]
            entry = self.entries[name]
            results.append(OdorMatch(
                name=name,
                family=entry.family,
                similarity=float(sims[idx]),
                glom_pattern=entry.glom_pattern,
            ))
        return results

    def _glom_fallback(self, kc: np.ndarray, top_k: int) -> list[OdorMatch]:
        """Fall back to glomerular search when KC matrix unavailable."""
        return self.find_by_glom_pattern(kc[:20] if len(kc) >= 20 else kc, top_k)

    # ── On-demand encoding ─────────────────────────────────────────────

    def encode_odor(self, name: str, brain,
                    duration_ms: float = 100.0,
                    cache: bool = True) -> np.ndarray | None:
        """
        Encode a single odorant by running a forward simulation.

        Args
            name        : Odorant name (must exist in self.entries).
            brain       : SparseProbabilisticBrain instance.
            duration_ms : Simulation window (ms).
            cache       : If True, store result back into the entry.

        Returns
            KC pattern as np.ndarray, or None if odorant not found.
        """
        entry = self.entries.get(name)
        if entry is None:
            return None

        # Return cached result if available
        if entry.kc_pattern is not None:
            return np.array(entry.kc_pattern, dtype=np.float32)

        glom = np.array(entry.glom_pattern, dtype=np.float32)

        brain.reset(deterministic=True)
        brain.inject_odor(glom)
        brain.evolve(duration_ms)
        kc = brain.get_region_activity("KC")

        if cache:
            entry.kc_pattern  = kc.tolist()
            entry.kc_active   = int(np.sum(kc > 0.01))
            entry.kc_sparsity = float(entry.kc_active / len(kc))

        return kc

    # ── Summary ────────────────────────────────────────────────────────

    def stats(self) -> dict[str, Any]:
        n_total    = len(self.entries)
        n_kc       = len(self.kc_names)
        fam_counts: dict[str, int] = {}
        for e in self.entries.values():
            fam_counts[e.family] = fam_counts.get(e.family, 0) + 1

        return {
            "total_odorants":       n_total,
            "odorants_with_kc":     n_kc,
            "families":             fam_counts,
            "kc_matrix_shape":      list(self.kc_matrix.shape) if self.kc_matrix is not None else None,
        }
