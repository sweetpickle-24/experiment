"""
Receptor to glomerulus map: the published one-to-one assignment.

Why this exists
---------------
``DoorClient`` compresses the DoOR receptor responses into 20 channels with PCA
(or, historically, uncentred SVD). That compression is a computational choice
with no biological counterpart, and it damages the input in four measurable
ways:

  * **The ReLU stops meaning anything.** DoOR responses are signed (478 negative
    entries in the shipped matrix: the receptor is inhibited below its
    spontaneous rate). ``map_to_glomerular_pattern`` applies
    ``np.maximum(projected, 0)``. Principal-component signs are arbitrary, so
    after a PCA projection the ReLU discards whichever half of each mixed
    component happens to come out negative. Under a one-to-one map the same
    ReLU is interpretable: an inhibited receptor contributes no drive.
  * **Sparsity is destroyed.** The response matrix is 28.1 % non-zero, which is
    the combinatorial code. A dense projection makes every odorant non-zero on
    nearly every component.
  * **It interacts with the concentration clip.** ``set_activation`` clips
    ``pattern * concentration`` to 1.0. A dense pattern drives many channels to
    the ceiling together, which erases the differences between them.
  * **The channel labels were fiction.** ``GLOM_LABELS`` names channels
    ``ester_fruit``, ``sulfur_mold`` and so on. A principal component is a
    direction of variance over whichever odorant panel was loaded, not a
    molecular class.

In the animal the relationship is one-to-one and it is known: each olfactory
sensory neuron expresses one tuning receptor, and all neurons expressing the
same receptor converge on a single glomerulus (Vosshall et al. 2000, Cell
102:147). So the projection does not need to be learned or approximated; it can
be looked up.

Source of the assignments
-------------------------
Primary source for every entry below is:

    Couto A., Alenius M. & Dickson B.J. (2005) Molecular, anatomical, and
    functional organization of the Drosophila olfactory system.
    Current Biology 15(17):1535-1547. doi:10.1016/j.cub.2005.07.034

specifically its **Table 1, "Molecular and Connectivity Maps of the Adult
Olfactory System"**, which lists sensillum and target glomerulus for 44
receptors validated by Or-mCD8-GFP reporter plus in-situ hybridisation.
Cross-checked against:

    Fishilevich E. & Vosshall L.B. (2005) Genetic and functional subdivision of
    the Drosophila antennal lobe. Current Biology 15(17):1548-1553.

    Munch D. & Galizia C.G. (2016) DoOR 2.0 - Comprehensive Mapping of
    Drosophila melanogaster Odorant Responses. Scientific Reports 6:21841,
    Table 1, which lists each DoOR responding unit against its glomerulus.

Selection rule, applied without exception
-----------------------------------------
**A receptor whose glomerulus cannot be sourced is excluded, not guessed.** This
is the same standard ``docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md`` applied
to benchmark targets, and it is the reason four receptors that carry real data in
the shipped matrix are nonetheless dropped: see ``EXCLUDED_RECEPTORS``.
"""

from __future__ import annotations

import csv
import gzip
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np

#: Primary citation, quoted once rather than repeated on all 29 entries.
COUTO_2005 = (
    "Couto, Alenius & Dickson (2005) Curr Biol 15:1535-1547, Table 1"
)
COUTO_2005_TEXT = (
    "Couto, Alenius & Dickson (2005) Curr Biol 15:1535-1547, Table 1 legend"
)


@dataclass(frozen=True)
class Assignment:
    """One receptor's glomerular target, with the source it came from."""

    glomerulus: str
    sensillum: str
    citation: str
    #: 'primary'   - in Couto 2005 Table 1, reporter plus in-situ validated.
    #: 'secondary' - stated in the source but not in-situ validated there.
    confidence: str = "primary"
    note: str = ""


#: Receptor -> glomerulus. Keys match the receptor names in
#: ``data/door_consensus_matrix.npy``.
#:
#: Only receptors present in that matrix are listed. The full Couto Table 1
#: covers 44 receptors; the shipped DoOR matrix has 33 with data, and the ones
#: it lacks (Or2a, Or7a, Or9a, Or19a/b, Or23a, Or33c, Or59c, Or67d, Or83c) are
#: omitted here rather than carried as dead entries.
RECEPTOR_GLOMERULUS: Dict[str, Assignment] = {
    "Or10a": Assignment("DL1", "ab1", COUTO_2005),
    "Or13a": Assignment("DC2", "ai1", COUTO_2005),
    "Or22a": Assignment(
        "DM2", "ab3", COUTO_2005,
        note="Or22a and Or22b are co-expressed in ab3A and target the same "
             "glomerulus; only Or22a is in the DoOR matrix",
    ),
    "Or35a": Assignment(
        "VC3", "ac3", COUTO_2005,
        note="Couto Table 1 records the sensillum as ac1; the coeloconic "
             "nomenclature was later revised to ac3. The glomerulus is "
             "unaffected. Bates et al. 2020 (eLife 9:e66018) renamed VC3l to "
             "VC3 in hemibrain v1.3, which is the name used here",
    ),
    "Or42a": Assignment(
        "VM7", "pb1", COUTO_2005,
        note="Couto Table 1 predates the split of VM7 into VM7d and VM7v. "
             "Handled by GLOMERULUS_ALIASES rather than by choosing one",
    ),
    "Or42b": Assignment("DM1", "ab1", COUTO_2005),
    "Or43a": Assignment("DA4l", "at3", COUTO_2005),
    "Or43b": Assignment("VM2", "ab8", COUTO_2005),
    "Or46a": Assignment(
        "VA7l", "pb2", COUTO_2005,
        note="listed as Or46aA in Couto Table 1; the DoOR matrix column is "
             "named Or46a",
    ),
    "Or47a": Assignment("DM3", "ab5", COUTO_2005),
    "Or47b": Assignment("VA1v", "at4", COUTO_2005),
    "Or49a": Assignment(
        "DL4", "ab10", COUTO_2005,
        note="shares DL4 with Or85f; see COMBINATION_RULE",
    ),
    "Or49b": Assignment("VA5", "ab6", COUTO_2005),
    "Or59b": Assignment("DM4", "ab2", COUTO_2005),
    "Or65a": Assignment(
        "DL3", "at4", COUTO_2005,
        note="Or65a, Or65b and Or65c all target DL3; only Or65a is in the "
             "DoOR matrix",
    ),
    "Or67a": Assignment("DM6", "ab10", COUTO_2005),
    "Or67b": Assignment("VA3", "ab9", COUTO_2005),
    "Or67c": Assignment("VC4", "ab7", COUTO_2005),
    "Or69a": Assignment(
        "D", "ab9", COUTO_2005,
        note="listed as Or69aA and Or69aB in Couto Table 1, both targeting D",
    ),
    "Or71a": Assignment("VC2", "pb1", COUTO_2005),
    "Or82a": Assignment("VA6", "ab5", COUTO_2005),
    "Or85a": Assignment("DM5", "ab2", COUTO_2005),
    "Or85b": Assignment(
        "VM5d", "ab3", COUTO_2005_TEXT, confidence="secondary",
        note="Couto Table 1 legend: 'Reporters for Or85b and Or98b both target "
             "the glomerulus VM5d, but neither has been validated by in situ "
             "hybridization.' Kept because the assignment is stated in the "
             "source and is uncontested in later work; flagged secondary "
             "because that source declines to call it validated",
    ),
    "Or85d": Assignment("VA4", "pb3", COUTO_2005),
    "Or85e": Assignment(
        "VC1", "pb2", COUTO_2005,
        note="co-expressed with Or33c in pb2A (Goldman et al. 2005); Or33c is "
             "not in the DoOR matrix, so VC1 is driven by Or85e alone here. "
             "Or85e has responses for only 11 odorants",
    ),
    "Or85f": Assignment(
        "DL4", "ab10", COUTO_2005,
        note="co-expressed with Or49a in ab10B; shares DL4. See "
             "COMBINATION_RULE",
    ),
    "Or88a": Assignment("VA1d", "at4", COUTO_2005),
    "Or92a": Assignment("VA2", "ab1", COUTO_2005),
    "Or98a": Assignment("VM5v", "ab7", COUTO_2005),
}


#: Receptors present in the shipped matrix that are deliberately NOT mapped.
#: Each entry says why. Nothing here is a guess that was rejected; these are
#: receptors for which no glomerular assignment could be sourced at all.
EXCLUDED_RECEPTORS: Dict[str, str] = {
    "Or83b": (
        "Orco, the obligate co-receptor. Expressed in essentially every "
        "olfactory sensory neuron rather than defining one, so it has no "
        "glomerulus. Absent from Couto Table 1 for that reason. (Its column in "
        "the shipped matrix is all-zero in any case.)"
    ),
    "Or45a": (
        "not in Couto 2005 Table 1. DoOR 2.0 Table 1 lists Or45a among "
        "'other responding units' rather than against a glomerulus; it is a "
        "larval receptor. 55 odorants measured, excluded rather than guessed."
    ),
    "Or45b": (
        "not in Couto 2005 Table 1, same as Or45a. 48 odorants measured, "
        "excluded rather than guessed."
    ),
    "Or59a": (
        "not in Couto 2005 Table 1. DoOR 2.0 Table 1 lists Or59a among "
        "'other responding units'. 54 odorants measured, excluded rather than "
        "guessed."
    ),
    "Or85c": (
        "not in Couto 2005 Table 1. Later work pairs it parenthetically with "
        "Or85b in VM5d - 'VM5d (Or85b/(Or85c))' - but that is a secondary, "
        "parenthetical assignment and Or85c has responses for only 51 "
        "odorants. Excluded under the citation rule; revisit if a primary "
        "source is found."
    ),
    "Or56a": "all-zero column in the shipped matrix (no DoOR data merged).",
    "Or63a": "all-zero column in the shipped matrix (no DoOR data merged).",
    "Or83a": "all-zero column in the shipped matrix (no DoOR data merged).",
    "Or98b": "all-zero column in the shipped matrix (no DoOR data merged).",
    "Gr21a": (
        "CO2 co-receptor, targets glomerulus V together with Gr63a "
        "(Couto Table 1). All-zero column in the shipped matrix, so it "
        "contributes nothing regardless."
    ),
    "Gr63a": (
        "CO2 co-receptor, partner of Gr21a, same glomerulus V. All-zero "
        "column in the shipped matrix."
    ),
}


#: Glomerulus names in Couto 2005 that were later subdivided. The connectome
#: annotations use the post-split names, so a Couto name has to fan out to the
#: names that actually exist in the data.
#:
#: Driving both halves is the conservative choice: picking one would silently
#: assert a subdivision the primary source does not make.
GLOMERULUS_ALIASES: Dict[str, Tuple[str, ...]] = {
    "VM7": ("VM7D", "VM7V"),
}


#: How multiple receptors mapping to one glomerulus are combined.
COMBINATION_RULE = (
    "mean of the contributing receptors' responses. Two glomeruli in this map "
    "receive more than one measured receptor: DL4 (Or49a and Or85f, which are "
    "co-expressed in the same ab10B neuron) and, in principle, VC1 (Or85e with "
    "Or33c, though Or33c is absent from the matrix). The mean is used rather "
    "than the sum so that a glomerulus is not made systematically stronger "
    "merely because more of its receptors happen to have been measured. Both "
    "are defensible; the choice is recorded because it is a choice."
)


#: Cell-type naming convention for uniglomerular olfactory projection neurons in
#: the FlyWire / hemibrain annotations: ``<GLOMERULUS>_<subtype>PN``, e.g.
#: ``DA1_lPN``, ``DM2_adPN``, ``VM5d_adPN``.
GLOM_PN_PATTERN = re.compile(
    r'^(D|V|DA\d[a-z]?|DC\d|DL\d[a-z]?|DM\d|DP1[lm]|VA\d[a-z]{0,2}'
    r'|VC\d[a-z]?|VL\d[a-z]?|VM\d[a-z]?|VP\d[a-z]?\+?)_'
    r'((?:ad|l|lv|v|l2|il)?PN)$', re.I)

#: Cached result of annotated_glomeruli(); the file does not change at runtime.
_ANNOTATED_CACHE: Dict[str, Dict[str, int]] = {}


def annotated_glomeruli(connectome_dir: Optional[Path] = None
                        ) -> Dict[str, int]:
    """
    Glomeruli that have uniglomerular projection neurons in the connectome, with
    a PN count for each, read from the cell-type annotations.

    This is the set the projection is restricted to. A channel whose glomerulus
    has no projection neuron would still occupy a slot in the stimulus vector
    and drive nothing, so it is dropped rather than carried.

    Args:
        connectome_dir: directory holding ``consolidated_cell_types.csv.gz``.
            Defaults to the repository's ``Fly Brain Female``.

    Returns:
        ``{GLOMERULUS: n_pns}`` with glomerulus names in canonical upper case.
        Empty if the annotation file is absent, which lets callers fall back
        rather than crash on a partial checkout.
    """
    if connectome_dir is None:
        connectome_dir = Path(__file__).resolve().parents[2] / 'Fly Brain Female'
    key = str(connectome_dir)
    if key in _ANNOTATED_CACHE:
        return dict(_ANNOTATED_CACHE[key])

    path = Path(connectome_dir) / 'consolidated_cell_types.csv.gz'
    counts: Dict[str, int] = {}
    if path.exists():
        with gzip.open(path, 'rt') as f:
            for row in csv.DictReader(f):
                match = GLOM_PN_PATTERN.match(
                    (row.get('primary_type') or '').strip())
                if match:
                    name = match.group(1).upper()
                    counts[name] = counts.get(name, 0) + 1
    _ANNOTATED_CACHE[key] = counts
    return dict(counts)


def normalise_glomerulus(name: str) -> str:
    """
    Canonical form for comparing glomerulus names across sources.

    The literature writes ``DA4l``, ``VM5d``, ``VA1v``; the FlyWire cell-type
    annotations write ``DA4L``, ``VM5D``, ``VA1V``. Upper-casing makes the two
    comparable without having to normalise either source in place.
    """
    return str(name).strip().upper()


def mapped_receptors(receptor_names: Sequence[str]) -> List[str]:
    """Which of *receptor_names* have a sourced glomerular assignment."""
    return [r for r in receptor_names if r in RECEPTOR_GLOMERULUS]


def glomeruli_for(receptor: str) -> Tuple[str, ...]:
    """
    Glomerulus name(s) driven by *receptor*, after alias expansion.

    Returns a tuple because a pre-split Couto name can correspond to more than
    one glomerulus in the connectome annotations (see GLOMERULUS_ALIASES).
    """
    assignment = RECEPTOR_GLOMERULUS[receptor]
    canonical = normalise_glomerulus(assignment.glomerulus)
    return GLOMERULUS_ALIASES.get(canonical, (canonical,))


def build_projection(
    receptor_names: Sequence[str],
    restrict_to: Iterable[str] | None = None,
) -> Tuple[np.ndarray, List[str], Dict[str, object]]:
    """
    Build the receptor -> glomerular-channel projection matrix.

    Args:
        receptor_names: receptor names in matrix-column order, as loaded from
            ``door_consensus_matrix.npy``.
        restrict_to: optional set of glomerulus names to keep, normally the
            glomeruli that actually have projection neurons in the connectome.
            Channels outside it are dropped, because a channel with no neuron
            to drive is dead weight that would still consume a slot in the
            stimulus vector.

    Returns:
        ``(projection, channel_names, report)`` where ``projection`` has shape
        ``(len(receptor_names), len(channel_names))``. Column *j* has the
        combination weights for channel *j*, so ``response @ projection`` gives
        the glomerular pattern. ``channel_names`` are glomerulus names in
        canonical (upper-case) form, sorted, so the channel order is a pure
        function of the inputs and not of dict iteration order.
    """
    allowed = None
    if restrict_to is not None:
        allowed = {normalise_glomerulus(g) for g in restrict_to}

    # glomerulus -> receptor column indices feeding it
    contributors: Dict[str, List[int]] = {}
    dropped_no_pn: Dict[str, List[str]] = {}
    for col, receptor in enumerate(receptor_names):
        if receptor not in RECEPTOR_GLOMERULUS:
            continue
        for glom in glomeruli_for(receptor):
            if allowed is not None and glom not in allowed:
                dropped_no_pn.setdefault(glom, []).append(receptor)
                continue
            contributors.setdefault(glom, []).append(col)

    channel_names = sorted(contributors)
    projection = np.zeros((len(receptor_names), len(channel_names)),
                          dtype=np.float32)
    for j, glom in enumerate(channel_names):
        cols = contributors[glom]
        # COMBINATION_RULE: mean, so a glomerulus is not stronger merely for
        # having had more of its receptors measured.
        weight = 1.0 / len(cols)
        for col in cols:
            projection[col, j] += weight

    unmapped = [r for r in receptor_names if r not in RECEPTOR_GLOMERULUS]
    report: Dict[str, object] = {
        "n_receptors_in_matrix": len(receptor_names),
        "n_receptors_mapped": len(mapped_receptors(receptor_names)),
        "n_channels": len(channel_names),
        "channel_names": list(channel_names),
        "receptors_per_channel": {
            g: [receptor_names[c] for c in contributors[g]]
            for g in channel_names
        },
        "multi_receptor_channels": {
            g: [receptor_names[c] for c in contributors[g]]
            for g in channel_names if len(contributors[g]) > 1
        },
        "unmapped_receptors": {
            r: EXCLUDED_RECEPTORS.get(r, "no assignment in this map")
            for r in unmapped
        },
        "channels_dropped_no_projection_neurons": {
            g: rs for g, rs in sorted(dropped_no_pn.items())
        },
        "combination_rule": COMBINATION_RULE,
        "aliases_applied": {
            k: list(v) for k, v in GLOMERULUS_ALIASES.items()
        },
        "primary_source": COUTO_2005,
    }
    return projection, channel_names, report


def coverage_report(receptor_names: Sequence[str],
                    annotated_glomeruli: Iterable[str] | None = None) -> Dict:
    """
    Human-readable coverage summary, for the diagnostic and the findings doc.

    ``annotated_glomeruli`` is the set of glomeruli that have projection
    neurons in the connectome, normally derived from the cell-type annotations.
    """
    _, channels, report = build_projection(receptor_names,
                                           restrict_to=annotated_glomeruli)
    wanted = {g for r in mapped_receptors(receptor_names)
              for g in glomeruli_for(r)}
    have = set(channels)
    out = dict(report)
    out["glomeruli_wanted_by_map"] = sorted(wanted)
    out["glomeruli_reachable"] = sorted(have)
    out["glomeruli_wanted_but_unreachable"] = sorted(wanted - have)
    if annotated_glomeruli is not None:
        annotated = {normalise_glomerulus(g) for g in annotated_glomeruli}
        out["n_glomeruli_annotated_in_connectome"] = len(annotated)
        out["annotated_but_no_mapped_receptor"] = sorted(annotated - wanted)
    return out


def assignment_table() -> List[Dict[str, str]]:
    """Flat, citable table of the map, for embedding in a result file."""
    return [
        {
            "receptor": r,
            "glomerulus": a.glomerulus,
            "sensillum": a.sensillum,
            "confidence": a.confidence,
            "citation": a.citation,
            "note": a.note,
        }
        for r, a in sorted(RECEPTOR_GLOMERULUS.items())
    ]


if __name__ == "__main__":
    import json
    from pathlib import Path

    data = np.load(
        Path(__file__).resolve().parents[2] / "data" /
        "door_consensus_matrix.npy", allow_pickle=True).item()
    receptors = list(data["receptors"])
    proj, channels, rep = build_projection(receptors)
    print(f"receptors in matrix : {len(receptors)}")
    print(f"receptors mapped    : {rep['n_receptors_mapped']}")
    print(f"channels built      : {len(channels)}")
    print(f"channels            : {channels}")
    print(f"multi-receptor      : {rep['multi_receptor_channels']}")
    print(f"unmapped            : {sorted(rep['unmapped_receptors'])}")
    print()
    print(json.dumps(assignment_table()[:3], indent=2))
