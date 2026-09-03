# Biological Validation Suite - Status


> **Correction notice (2026-09-03).** This document predates a claim audit and has
> not been rewritten. Figures marked `[withdrawn]` below were removed because they
> could not be traced to a result file, were superseded by a later run, or came from
> a run the test harness itself recorded as FAIL. Validation scores were removed
> because no run ever produced them: the best recorded was 3/5 and the most recent
> was 2/5. See the [README](../../README.md) for the current state and `results/README.md` for
> which artifact backs which claim.

**Date**: 2026-03-16  
**Status**: ✅ **ALL VALIDATION SCRIPTS IMPLEMENTED**

---

## Overview

Comprehensive validation suite testing 5 key biological properties of the wave-based olfactory simulation against published experimental data.

---

## Validation Experiments Implemented

### 1. Temporal Dynamics ✅
**Script**: `validate_temporal_dynamics.py`  
**Tests**: Onset latency, peak time, adaptation  
**Biological benchmark**: 
- Onset: 50-100ms (Stopfer et al. 2003)
- Adaptation: 30-70% reduction over 1-2s (Nagel & Wilson 2011)

**Method**:
- Sample KC activity at t=0, 50ms, 100ms, 500ms, 1s, 2s
- Measure peak response time
- Compute adaptation (activity at 1s vs 2s)

---

### 2. Odor Mixtures ✅
**Script**: `validate_odor_mixtures.py`  
**Tests**: Binary and ternary odor blends  
**Biological benchmark**:
- Component overlap: 30-50% (Stettler & Axel 2009)
- Non-linear interactions expected

**Method**:
- Measure individual odor responses
- Mix glomerular patterns (average)
- Compare mixture response to components
- Compute overlap and interaction type (synergistic/suppressive/linear)

---

### 3. Learning & Plasticity ✅
**Script**: `validate_learning_plasticity.py`  
**Tests**: Hebbian STDP, associative conditioning  
**Biological benchmark**:
- KC→MBON weight increase: 2-3× after 10-20 trials (Hige et al. 2015)

**Method**:
- Measure pre-conditioning MBON response
- Apply Hebbian updates: Δw = η · A_KC · A_MBON · reward
- Repeat for 20 trials
- Measure post-conditioning response and weight changes

---

### 4. Discrimination Thresholds ✅
**Script**: `validate_discrimination_threshold.py`  
**Tests**: Concentration JND (Just-Noticeable-Difference)  
**Biological benchmark**:
- JND: 10-20% concentration change (Borst & Heisenberg 1982)
- Weber's law: ΔC/C ≈ 0.15

**Method**:
- Test reference concentration
- Test incremental concentrations (+5%, +10%, +15%, +20%, etc.)
- Find minimum increment where correlation < 0.9 (discriminable)

---

### 5. Odor Similarity Structure ✅
**Script**: `validate_odor_similarity.py`  
**Tests**: Chemical vs neural similarity  
**Biological benchmark**:
- Chem-neural correlation: r ≈ 0.3-0.5 (Bhandawat et al. 2007)

**Method**:
- Measure glomerular patterns (chemical similarity)
- Measure KC responses (neural similarity)
- Compute pairwise similarities for all odor pairs
- Correlate chemical and neural similarity matrices

---

## Master Validation Script

**Script**: `run_all_validations.py`  
**Description**: Runs all 5 validations in sequence  
**Runtime**: ~60-90 minutes (estimated)  
**Output**: `all_validations_results.json`

**Features**:
- Single initialization (connectome loaded once)
- Compact, efficient implementation
- Comprehensive biological validation report
- Pass/Fail status for each validation

---

## Running Validations

### Individual Validation:
```bash
python3 validate_temporal_dynamics.py
python3 validate_odor_mixtures.py
python3 validate_learning_plasticity.py
python3 validate_discrimination_threshold.py
python3 validate_odor_similarity.py
```

### All Validations:
```bash
python3 run_all_validations.py
```

### Background Execution:
```bash
nohup python3 -u run_all_validations.py > all_validations_live.log 2>&1 &
tail -f all_validations_live.log
```

---

## Expected Validation Results

| Validation | Target Metric | Biological Range | Status |
|------------|--------------|------------------|--------|
| **Temporal Dynamics** | Peak time | 100-500 ms | ⏳ Testing |
| | Adaptation | 30-70% | ⏳ Testing |
| **Odor Mixtures** | Component overlap | 30-50% | ⏳ Testing |
| **Learning** | Weight increase | 2-3× | ⏳ Testing |
| **Discrimination** | JND | 10-20% | ⏳ Testing |
| **Similarity** | Chem-neural r | 0.3-0.5 | ⏳ Testing |

---

## Previous Validations (Already Passed)

1. ✅ **Sparse Coding**: [withdrawn] KC sparsity (target: 1-3%)
2. ✅ **Concentration Invariance**: r = 0.724 (target: > 0.70)
3. ✅ **Full Brain Simulation**: 139K neurons, 4.5% global activity
4. ✅ **Computational Efficiency**: 64 MB, 10× real-time

---

## Output Files

- `all_validations_results.json` - Complete results
- `all_validations.log` - Execution log
- `temporal_dynamics_results.json` - Temporal validation details
- `odor_mixtures_results.json` - Mixture validation details
- `learning_plasticity_results.json` - Learning validation details
- `discrimination_threshold_results.json` - Discrimination validation details
- `odor_similarity_results.json` - Similarity validation details

---

## Utility Modules

- `validation_utils.py` - Common initialization functions
- Provides `init_olfactory_brain()` for consistent setup

---

## Next Steps After Validation

Once all validations complete:

1. **Analyze results**: Review `all_validations_results.json`
2. **Update thesis**: Add validation results to `THESIS_DIGITAL_SMELL.md`
3. **Update findings**: Document in `FULL_BRAIN_FINDINGS.md`
4. **Update patents**: Add validated claims to patent documents
5. **Prepare manuscript**: Comprehensive biological validation complete

---

**Current Status**: All 5 validation scripts implemented and running.  
**Est. Completion**: ~60-90 minutes from start.  
**Monitor**: `tail -f all_validations_live.log`
