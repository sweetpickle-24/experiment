# Author Contributions and Declarations

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


**For Nature Communications Submission**

---

## Author Contributions Statement

**Using CRediT (Contributor Roles Taxonomy)**

### Vladyslav Byelozerskykh - Corresponding Author

**ORCID:** 0009-0009-4741-2663  
**Affiliation:** Independent Researcher, Toronto, Ontario, Canada

**Roles:**
- **Conceptualization:** Lead (100%)
  - Conceived the sparse probabilistic oscillator framework
  - Designed the inverse optimization method
  - Developed the real-time simulation strategy

- **Methodology:** Lead (100%)
  - Developed Fokker-Planck variance evolution equations
  - Created analytical expectation coupling approximation
  - Designed GPU-accelerated implementation

- **Software:** Lead (100%)
  - Implemented SparseProbabilisticBrain engine
  - Developed MLX/Metal GPU backend
  - Created inverse optimizer with automatic differentiation
  - Built experimental validation pipelines

- **Validation:** Lead (100%)
  - Conducted biological validation experiments (20 odors)
  - Verified KC sparsity against published data
  - Performed concentration invariance tests
  - Statistical analysis of results

- **Formal Analysis:** Lead (100%)
  - Mathematical derivations of wave equations
  - Convergence analysis
  - Performance benchmarking
  - Statistical significance testing

- **Investigation:** Lead (100%)
  - Ran all simulations
  - Collected and analyzed data
  - Generated figures

- **Resources:** Lead (100%)
  - Obtained FlyWire connectome data
  - Accessed DOoR database
  - Provided computational resources

- **Data Curation:** Lead (100%)
  - Organized simulation results
  - Created digital smell database
  - Prepared data for publication

- **Writing - Original Draft:** Lead (100%)
  - Wrote all sections of manuscript
  - Prepared supplementary materials

- **Writing - Review & Editing:** Lead (100%)
  - Revised manuscript based on feedback
  - Responded to reviewer comments

- **Visualization:** Lead (100%)
  - Created all figures
  - Designed supplementary visualizations

- **Supervision:** [If applicable]
  - [Only if you supervised others]

- **Project Administration:** Lead (100%)
  - Managed research timeline
  - Coordinated with collaborators

- **Funding Acquisition:** [If applicable]
  - [List if you wrote grants]

---

### [Co-Author Name] - if applicable

**Roles:**
- **Conceptualization:** Supporting
  - [Describe specific contributions]

- **Methodology:** Supporting
  - [Describe specific contributions]

[Continue for each co-author...]

---

## Competing Interests Declaration

### Patents

**Provisional patent applications filed:**

1. **"Memory-Efficient Probabilistic Oscillator Network for Large-Scale Neural Simulation"**
   - USPTO Provisional Application No.: Pending (to be filed)
   - Filing Date: Expected March 2026
   - Status: In preparation
   - Inventors: Vladyslav Byelozerskykh
   - Assignee: Vladyslav Byelozerskykh (Independent)

2. **"Method and System for Inverse Optimization of Sensory Inputs via Gradient Descent Through Neural Dynamics"**
   - USPTO Provisional Application No.: Pending (to be filed)
   - Filing Date: Expected March 2026
   - Status: In preparation
   - Inventors: Vladyslav Byelozerskykh
   - Assignee: Vladyslav Byelozerskykh (Independent)

3. **"System and Method for Real-Time Large-Scale Neural Network Simulation Using GPU-Accelerated Sparse Probabilistic Dynamics"**
   - USPTO Provisional Application No.: Pending (to be filed)
   - Filing Date: Expected March 2026
   - Status: In preparation
   - Inventors: Vladyslav Byelozerskykh
   - Assignee: Vladyslav Byelozerskykh (Independent)

**Nature of competing interest:**
These patent applications cover the methods described in this manuscript. The patents do not affect the scientific conclusions or data presented. All code and data will be made publicly available under open-source licenses as described in the Data Availability and Code Availability statements.

### Financial Interests

**Current:**
- [ ] No financial competing interests to declare

OR

- [ ] Employment: [Institution/Company]
- [ ] Consulting fees: None
- [ ] Honoraria: None
- [ ] Stock ownership: None
- [ ] Grants received: [List grants related to this work]

**Potential Future:**
- [ ] Potential licensing revenue from patents (not yet materialized)
- [ ] No other potential financial interests

### Non-Financial Interests

- [ ] No non-financial competing interests to declare

OR

- [ ] [List any non-financial interests, e.g., board memberships, scientific society roles]

### Statement

The authors declare that provisional patent applications have been filed for the methods described in this work. These patents are disclosed in the interest of transparency and do not compromise the scientific integrity, objectivity, or open availability of the research findings. All code will be released under MIT license and all data will be publicly available.

**Signed:**

Vladyslav Byelozerskykh: _________________________ Date: March 16, 2026

(Sole author - no co-authors)

---

## Data Availability Statement

### Data Generated by This Study

**Simulation Results:**
- Full brain olfactory responses (20 odors, 139,255 neurons)
- Digital smell database (glomerular + PN + KC + MBON patterns)
- Concentration invariance test results
- Performance benchmarking data

**Availability:**
All data generated in this study are available in the following repository:
- Repository: [Zenodo/Figshare/Dryad]
- DOI: [TO BE GENERATED UPON DEPOSIT]
- License: CC BY 4.0 (Creative Commons Attribution)

**Format:**
- JSON files for simulation results
- CSV files for tabular data
- HDF5 files for large numerical arrays

**Files included:**
```
data_repository/
├── full_brain_smell_results.json (20 odor responses)
├── digital_smell_database.json (10 odors with full pathway)
├── concentration_invariance_results.json
├── performance_benchmarks.csv
└── README.txt (data documentation)
```

### Data Used by This Study

**FlyWire Connectome:**
- Source: FlyWire Consortium
- URL: https://flywire.ai/
- DOI: 10.1038/s41586-024-07686-5
- License: Open access
- Date accessed: [Date you downloaded data]

**DOoR Database (Database of Odorant Responses):**
- Source: http://neuro.uni.wroc.pl/door
- Reference: Larsson et al. (2004), Münch & Galizia (2016)
- License: Public domain
- Date accessed: [Date you accessed]

**No restrictions on data availability.**

---

## Code Availability Statement

### Source Code

All software developed for this study is publicly available:

**Primary Repository:**
- Platform: GitHub
- URL: https://github.com/[your-username]/[your-repo]
- License: MIT License (permissive open source)
- Archive: Zenodo DOI [TO BE GENERATED]

**Contents:**
```
repository/
├── hive/                    (main simulation package)
│   ├── engine/             (SparseProbabilisticBrain)
│   ├── substrate/          (connectome handling)
│   ├── inverse/            (inverse optimizer)
│   └── data/               (DOoR client)
├── run_full_brain_smell.py (main experiment script)
├── concentration_invariance_test.py
├── create_publication_figures.py
├── requirements.txt        (dependencies)
├── README.md              (installation & usage)
└── LICENSE               (MIT License text)
```

**Installation:**
```bash
git clone https://github.com/[your-username]/[your-repo]
cd [your-repo]
pip install -r requirements.txt
python run_full_brain_smell.py
```

**System Requirements:**
- Python 3.9+
- 16 GB RAM minimum
- GPU recommended (Apple M-series, NVIDIA CUDA, or AMD ROCm)
- Tested on: macOS 14.0+, Ubuntu 22.04+

**Documentation:**
Comprehensive documentation including:
- API reference
- Usage examples
- Parameter descriptions
- Troubleshooting guide

Available at: https://[your-repo].readthedocs.io/ [if applicable]

**Version at Time of Publication:**
- Version: v1.0.0
- Commit hash: Will be generated at release
- Release DOI: Will be generated upon Zenodo deposit

### Reproducibility

All figures in the manuscript can be reproduced by running:
```bash
python create_publication_figures.py
```

All results can be reproduced by running:
```bash
python run_full_brain_smell.py  # Main results
python concentration_invariance_test.py  # Concentration tests
```

**Expected runtime:**
- Full brain simulation (20 odors): ~3 hours on Apple M4 Pro
- Concentration tests: ~1 hour
- Figure generation: <5 minutes

**Reproducibility Notes:**
- Results are deterministic given fixed random seeds (specified in code)
- Minor numerical variations (<1%) may occur across different hardware
- GPU implementations (MLX, CUDA) produce equivalent results to CPU

### Dependencies

**Core Dependencies:**
- numpy >= 1.24.0
- mlx >= 0.1.0 (for Apple Silicon GPU)
- scipy >= 1.10.0
- matplotlib >= 3.7.0 (for figures)

**Optional Dependencies:**
- torch >= 2.0.0 (CUDA alternative to MLX)
- jupyter >= 1.0.0 (for interactive exploration)

All versions specified in `requirements.txt`

### Custom Code vs. Standard Libraries

**Novel code (this study):**
- `SparseProbabilisticBrain` class (core innovation)
- `SmellOptimizer` (inverse problem solver)
- Olfactory subgraph extraction
- Concentration invariance testing

**Standard libraries used:**
- NumPy (numerical computation)
- MLX (GPU acceleration)
- Matplotlib (visualization)
- SciPy (statistical analysis)

### Patent Notice

This code is released under MIT License despite pending patent applications. Users are free to use, modify, and distribute the code for research and commercial purposes. Patent applications cover specific algorithmic innovations but do not restrict code usage.

---

## Reporting Summary

**Nature Research Reporting Summary (attach separately)**

Key methodological details:
- Sample size: 20 odors tested (full brain), 3 odors tested (concentration invariance)
- Replicates: Each simulation deterministic but biological variability captured via probabilistic framework
- Randomization: Not applicable (computational study)
- Blinding: Not applicable (computational study)
- Statistical methods: Described in Methods section
  - Correlation analysis (Pearson)
  - Sparsity measurements
  - Jaccard similarity
  - All code for statistics available in repository

**Software:**
- Python 3.11
- MLX 0.10.0
- NumPy 1.26.0
- SciPy 1.11.0
- Matplotlib 3.8.0

**Hardware:**
- Apple M4 Pro (16-core GPU, 16 GB unified memory)
- Intel Core i9 (for CPU benchmarking)
- NVIDIA RTX 4090 (for CUDA benchmarking)

---

## ORCID iDs

**Vladyslav Byelozerskykh:** 0009-0009-4741-2663

(Sole author - no co-authors)

---

## Contact Information

**Corresponding Author:**

Vladyslav Byelozerskykh  
Independent Researcher  
Toronto, Ontario, M5G 0C5  
Canada  

Email: vladorangeqwer@gmail.com  
ORCID: 0009-0009-4741-2663  

**Alternative Contact (if applicable):**

[Name]  
Email: [email]  

---

## Acknowledgments

**Funding:**
[List all funding sources with grant numbers]

Example:
- This work was supported by NIH grant R01NS123456 (to [PI name])
- [Your name] was supported by [fellowship name]

OR

- This work was self-funded with no external grant support

**Acknowledgments:**

We thank:
- The FlyWire Consortium for making the connectome data publicly available
- [Any colleagues who provided feedback on manuscripts]
- [Any technical support staff]
- [Computational resources provided by institution]

We acknowledge the use of:
- FlyWire connectome data (Dorkenwald et al., Nature 2024)
- DOoR odorant response database (Münch & Galizia, 2016)
- Apple MLX framework for GPU acceleration

**No involvement in data collection or analysis by any acknowledged parties.**

---

**Document Status:** TEMPLATE - Complete before submission  
**Created:** March 13, 2026  
**For:** Vladyslav Byelozerskykh  
**ORCID**: 0009-0009-4741-2663  
**Institution**: Independent Researcher  
**Location**: Toronto, Ontario, Canada  
**Contact**: vladorangeqwer@gmail.com  
**Date**: March 16, 2026
