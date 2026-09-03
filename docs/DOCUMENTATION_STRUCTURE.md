# Documentation Structure


> **Correction notice (2026-09-03).** This document predates a claim audit and has
> not been rewritten. Figures marked `[withdrawn]` below were removed because they
> could not be traced to a result file, were superseded by a later run, or came from
> a run the test harness itself recorded as FAIL. Validation scores were removed
> because no run ever produced them: the best recorded was 3/5 and the most recent
> was 2/5. See the [README](../README.md) for the current state and `results/README.md` for
> which artifact backs which claim.

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
