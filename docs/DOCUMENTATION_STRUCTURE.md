# Documentation Structure

<!-- STALE-BANNER-2026-09-05 -->
> **SUPERSEDED — do not cite.** This document predates the September 2026 audits and
> has not been rewritten. Corrections that apply to it:
>
> - The scored suite is **5/5** (`results/final/all_validations_G2.json`). Scores of
>   9/9, 13/13, 14/14 or 27/27 appearing anywhere were **never produced by any run**;
>   the recorded history is 3/5, then 1/5, then 2/5, then 5/5.
> - GPU speedup is **10.00×**, not 86×.
> - Kenyon cell sparsity is **imposed by the readout** (310 of 5,177 cells) rather
>   than measured, so "1.65 % matching Turner et al. 2008" is withdrawn.
> - Concentration invariance is **0.6603 and deliberately unscored**; the 0.70
>   threshold it used to be compared against is not in the paper it was cited to.
> - The decorrelation result **`r = −0.51` is withdrawn** — a six-point regression
>   from a run recorded as FAIL, measured at `+0.632` on a later run.
> - Vision and auditory "firsts" are **not** part of the scored suite, and several
>   come from hand-written filters rather than the wave engine.
>
> Current: [README](../README.md) ·
> [ARCHITECTURE](../ARCHITECTURE.md) ·
> [LIMITATIONS](../docs/03_validation/LIMITATIONS.md) ·
> [audit](../docs/03_validation/BENCHMARK_VALIDITY_AUDIT.md) ·
> [projection repair](../docs/03_validation/GLOMERULAR_PROJECTION_REPAIR.md).
> Tracked in [OUTDATED_FILES.md](../OUTDATED_FILES.md).



**Date**: March 19, 2026  
**Status**: Complete reorganization of all project documentation

---

## Directory Structure

```
/experiment/
├── README.md                          # Main entry point
├── QUICKSTART.md                      # Quick setup guide
│
├── docs/                              # All documentation
│   ├── 00_START_HERE.md              # Navigation guide
│   ├── 01_setup/                     # Setup & installation
│   │   ├── INSTALLATION.md
│   │   ├── GPU_SETUP.md
│   │   └── TESTING_GUIDE.md
│   ├── 02_architecture/              # System architecture
│   │   ├── WAVE_PHYSICS.md
│   │   ├── SPARSE_BRAIN.md
│   │   └── CONNECTOME.md
│   ├── 03_validation/                # Validation results
│   │   ├── FINAL_VALIDATION.md       # [score withdrawn] results
│   │   ├── SMELL_VALIDATION.md
│   │   └── VISION_VALIDATION.md
│   ├── 04_discoveries/               # Novel findings
│   │   ├── DECORRELATION.md
│   │   ├── DISCRIMINATION.md
│   │   └── ALL_DISCOVERIES.md
│   ├── 05_publication/               # Publication materials
│   │   ├── MANUSCRIPT.md
│   │   ├── FIGURES/
│   │   └── EXECUTIVE_SUMMARY.md
│   └── 06_status/                    # Project status
│       ├── POC_STATUS.md
│       └── TIMELINE.md
│
├── research/                          # Research documents
│   ├── smell/                        # Olfaction research
│   ├── vision/                       # Vision research
│   ├── validation/                   # Validation studies
│   └── findings/                     # Research findings
│
├── thesis/                            # Thesis documents
│   └── THESIS_MAIN.md
│
├── patents/                           # Patent applications
│   ├── PATENT_1_DIGITAL_SMELL.md
│   ├── PATENT_2_NEUROMORPHIC_BCI.md
│   └── PATENT_3_REALTIME_SYSTEM.md
│
└── archive/                           # Historical documents
    ├── old_experiments/
    └── deprecated/
```

---

## Document Categories

### 1. Entry Points (Root)
- `README.md` - Main project overview
- `QUICKSTART.md` - Fast setup for new users

### 2. Setup & Configuration (`docs/01_setup/`)
- Installation guides
- GPU/MLX setup
- Testing procedures

### 3. Core Documentation (`docs/02_architecture/`)
- Wave-based neural engine
- Sparse probabilistic brain
- Connectome integration

### 4. Validation (`docs/03_validation/`)
- [score withdrawn] biological benchmarks
- Smell validation ([score withdrawn])
- Vision validation (4/4)

### 5. Discoveries (`docs/04_discoveries/`)
- Decorrelation (r = [withdrawn])
- Fine discrimination (5% JND)
- All novel findings

### 6. Publication (`docs/05_publication/`)
- Manuscript drafts
- Figure generation
- Submission materials

### 7. Status (`docs/06_status/`)
- Current POC status
- Project timeline
- Completion checklists

---

## Navigation

**New to the project?**
1. Start with `README.md`
2. Read `QUICKSTART.md`
3. Follow `docs/00_START_HERE.md`

**Need validation results?**
→ `docs/03_validation/FINAL_VALIDATION.md`

**Looking for discoveries?**
→ `docs/04_discoveries/ALL_DISCOVERIES.md`

**Publishing?**
→ `docs/05_publication/MANUSCRIPT.md`

---

## Maintenance

- Keep root directory clean (only README + QUICKSTART)
- Use `docs/` for all documentation
- Archive old/deprecated files to `archive/`
- Update this structure guide when adding new categories
