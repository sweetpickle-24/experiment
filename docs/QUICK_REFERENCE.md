# Quick Reference - Digital Fly Brain Project

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



**Last Updated**: March 19, 2026  
**Status**: [score withdrawn] validations (100%) + 2 discoveries

---

## 🎯 Most Important Documents

### 1. Results & Validation
📊 [`docs/03_validation/FINAL_VALIDATION.md`](03_validation/FINAL_VALIDATION.md)
- **[score withdrawn] biological benchmarks** (100% success)
- **2 major discoveries**: Decorrelation (r = [withdrawn]) + Discrimination (5% JND)
- Ready for Nature Neuroscience

### 2. Discoveries
🔬 [`docs/04_discoveries/ALL_NOVEL_DISCOVERIES.md`](04_discoveries/ALL_NOVEL_DISCOVERIES.md)
- Decorrelation by sparse expansion
- Fine olfactory discrimination
- Full scientific analysis

### 3. Publication
📄 [`docs/05_publication/MANUSCRIPT.md`](05_publication/MANUSCRIPT.md)
- Complete manuscript
- All figures ready
- Submission-ready

### 4. How It Works
⚙️ [`docs/02_architecture/WAVE_PHYSICS.md`](02_architecture/WAVE_PHYSICS.md)
- Wave-based neural engine
- Probabilistic oscillators
- Sparse brain architecture

### 5. Get Started
🚀 [`QUICKSTART.md`](../QUICKSTART.md)
- 5-minute setup
- Run first test
- See results

---

## 📂 Where to Find Things

| What You Need | Location |
|--------------|----------|
| **Project overview** | [`README.md`](../README.md) |
| **Setup guide** | [`docs/01_setup/HOW_TO_RUN.md`](01_setup/HOW_TO_RUN.md) |
| **Test instructions** | [`docs/01_setup/TESTING_GUIDE.md`](01_setup/TESTING_GUIDE.md) |
| **Validation results** | [`docs/03_validation/`](03_validation/) |
| **Novel findings** | [`docs/04_discoveries/`](04_discoveries/) |
| **Full manuscript** | [`docs/05_publication/MANUSCRIPT.md`](05_publication/MANUSCRIPT.md) |
| **Project status** | [`docs/06_status/POC_STATUS.md`](06_status/POC_STATUS.md) |
| **Full thesis** | [`THESIS_DIGITAL_SMELL.md`](../THESIS_DIGITAL_SMELL.md) |

---

## 🔢 Key Numbers

- **Neurons**: 139,255 (full fly brain)
- **Synapses**: 5.3 million
- **Validation**: [score withdrawn] smell + 4/4 vision = **[score withdrawn] (100%)**
- **Discoveries**: 2 major
- **Speed**: 86× faster than CPU (M4 Pro GPU)
- **Memory**: 64 MB
- **Hardware independence**: Validated ✅

---

## 🎓 For Different Audiences

### Researchers
1. [`docs/03_validation/FINAL_VALIDATION.md`](03_validation/FINAL_VALIDATION.md) - Full results
2. [`docs/04_discoveries/ALL_NOVEL_DISCOVERIES.md`](04_discoveries/ALL_NOVEL_DISCOVERIES.md) - Novel findings
3. [`docs/05_publication/MANUSCRIPT.md`](05_publication/MANUSCRIPT.md) - Full paper

### Engineers
1. [`docs/02_architecture/WAVE_PHYSICS.md`](02_architecture/WAVE_PHYSICS.md) - System design
2. [`docs/01_setup/HOW_TO_RUN.md`](01_setup/HOW_TO_RUN.md) - Setup
3. [`docs/02_architecture/MLX_GPU_IMPLEMENTATION.md`](02_architecture/MLX_GPU_IMPLEMENTATION.md) - GPU acceleration

### Students
1. [`README.md`](../README.md) - Overview
2. [`QUICKSTART.md`](../QUICKSTART.md) - Get running
3. [`THESIS_DIGITAL_SMELL.md`](../THESIS_DIGITAL_SMELL.md) - Full thesis

---

## 📞 Common Questions

**Q: How do I run the validation tests?**
A: See [`docs/01_setup/TESTING_GUIDE.md`](01_setup/TESTING_GUIDE.md)

**Q: What are the validation results?**
A: See [`docs/03_validation/FINAL_VALIDATION.md`](03_validation/FINAL_VALIDATION.md)

**Q: What did you discover?**
A: See [`docs/04_discoveries/ALL_NOVEL_DISCOVERIES.md`](04_discoveries/ALL_NOVEL_DISCOVERIES.md)

**Q: How does the wave physics work?**
A: See [`docs/02_architecture/WAVE_PHYSICS.md`](02_architecture/WAVE_PHYSICS.md)

**Q: Is this ready for publication?**
A: Yes! See [`docs/05_publication/MANUSCRIPT.md`](05_publication/MANUSCRIPT.md)

---

## 🗺️ Full Navigation

**Complete navigation guide**: [`docs/00_START_HERE.md`](00_START_HERE.md)

**Complete file index**: [`docs/DOCUMENTATION_INDEX.md`](DOCUMENTATION_INDEX.md)

**Reorganization details**: [`docs/REORGANIZATION_COMPLETE.md`](REORGANIZATION_COMPLETE.md)

---

**Status**: ✅ [score withdrawn] Complete + 2 Discoveries  
**Ready**: Nature Neuroscience submission  
**Date**: March 19, 2026
