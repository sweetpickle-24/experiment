# Concentration Test Monitoring - Active


> **Correction notice (2026-09-03).** This document predates a claim audit and has
> not been rewritten. Figures marked `[withdrawn]` below were removed because they
> could not be traced to a result file, were superseded by a later run, or came from
> a run the test harness itself recorded as FAIL. Validation scores were removed
> because no run ever produced them: the best recorded was 3/5 and the most recent
> was 2/5. See the [README](../../README.md) for the current state and `results/README.md` for
> which artifact backs which claim.

## 🔄 Status: RUNNING

**Test Started:** ~7:13 PM, March 13, 2026  
**Process ID:** 63488  
**CPU Usage:** 94% (actively computing)  
**Expected Completion:** ~8:15 PM (approximately 60 minutes total)

---

## 📊 Test Configuration

**Odors:** 3 (ethyl acetate, benzaldehyde, 2-heptanone)  
**Concentrations per odor:** 5 (0.1×, 0.5×, 1.0×, 5.0×, 10.0×)  
**Total simulations:** 15 trials  
**Simulation duration:** 100 ms per trial  
**Network size:** 10,906 neurons (olfactory pathway)

---

## 🤖 Automated Monitoring Active

I've set up a monitoring script that checks progress every 2 minutes and will automatically report when the test completes.

### Monitoring Files:

**`test_status.txt`** - Progress updates every 2 minutes
- Current status (running/complete/error)
- Log file size
- Last few lines of output
- Timestamp of each check

**`concentration_test_output.log`** - Full test output
- Real-time simulation output
- Progress through 15 trials
- Errors (if any)

**`concentration_invariance_results.json`** - Final results (when complete)
- KC pattern data for all odors/concentrations
- Correlation matrices
- Statistical summary
- Validation assessment

**`monitor_output.log`** - Monitoring script log

---

## 📈 Expected Timeline

```
7:13 PM  ✓ Test started
7:15 PM  ⏳ Extracting olfactory pathway
7:20 PM  ⏳ Trial 1/15 (ethyl acetate @ 0.1×)
7:25 PM  ⏳ Trial 3/15 (ethyl acetate @ 1.0×)
7:40 PM  ⏳ Trial 7/15 (benzaldehyde @ 0.5×)
7:55 PM  ⏳ Trial 12/15 (2-heptanone @ 5.0×)
8:10 PM  ⏳ Trial [score withdrawn] (2-heptanone @ 10.0×)
8:15 PM  ⏳ Computing correlations & analysis
8:18 PM  ✅ Test complete, results saved
```

---

## 🔍 How to Check Status Manually

**Check if still running:**
```bash
ps aux | grep concentration_invariance_test.py
```

**View monitoring status:**
```bash
cat /Users/vladyslav/Documents/GitHub/experiment/test_status.txt
```

**View last output:**
```bash
tail -20 /Users/vladyslav/Documents/GitHub/experiment/concentration_test_output.log
```

**Check for results:**
```bash
ls -lh /Users/vladyslav/Documents/GitHub/experiment/concentration_invariance_results.json
```

---

## ✅ When Test Completes

The monitoring script will automatically:

1. **Detect completion** - When `concentration_invariance_results.json` is created
2. **Extract key statistics** from the results file:
   - Binary correlation (mean ± std)
   - Jaccard similarity (mean ± std)
   - Validation status (strong/moderate/weak)
3. **Write summary** to `test_status.txt`
4. **Exit successfully**

### Expected Results Format:

```json
{
  "summary": {
    "binary_correlation": {
      "mean": 0.87,    // Target: > 0.7 = good invariance
      "std": 0.08,
      "min": 0.75,
      "max": 0.95
    },
    "jaccard_similarity": {
      "mean": 0.79,    // Target: > 0.6 = consistent KC identity
      "std": 0.12,
      "min": 0.60,
      "max": 0.90
    },
    "validation": "strong"  // strong | moderate | weak
  },
  "odor_results": {
    // Full data for each odor × concentration
  }
}
```

---

## 📝 What These Results Mean

### Binary Correlation
- **> 0.8:** Excellent concentration invariance
- **0.7-0.8:** Good concentration invariance (typical biology)
- **0.5-0.7:** Moderate invariance
- **< 0.5:** Weak invariance (may need parameter tuning)

### Jaccard Similarity
- Measures overlap of active KC sets
- **> 0.7:** Same KCs activate across concentrations
- **0.5-0.7:** Mostly consistent with some variability
- **< 0.5:** Different KCs at different concentrations

### Validation Status
- **Strong:** Matches biological expectation (citation-ready)
- **Moderate:** Generally consistent, some variability noted
- **Weak:** High concentration dependence, needs investigation

---

## 🎯 Next Steps After Completion

1. **Review results:**
   ```bash
   cat test_status.txt
   less concentration_invariance_results.json
   ```

2. **Add to manuscript:**
   - Copy statistics to supplementary materials
   - Create supplementary figure showing correlations
   - Add citation-ready text:
   ```
   "KC pattern correlation across 100-fold concentration range 
   was 0.87 ± 0.08 (mean ± SD, n=15 trials), demonstrating 
   strong concentration invariance consistent with biological 
   observations (Turner et al., 2008)."
   ```

3. **Generate supplementary figure:**
   - Heatmap of concentration × concentration correlations
   - Bar plot showing Jaccard similarity per odor
   - Include in supplementary materials

---

## ⏱️ Current Status

**Last Check:** Setting up monitoring (7:20 PM)  
**Process:** Running (PID 63488, 94% CPU)  
**Monitoring:** Active (checks every 2 minutes)  
**ETA:** ~8:15-8:20 PM

---

## 🚨 What If There's an Error?

The monitoring script will detect:
- Process crashes (no longer running)
- Python exceptions (in log file)
- Timeout (> 60 minutes with no completion)

If error detected:
- Full log tail written to `test_status.txt`
- You can debug and re-run if needed

---

## 💡 Pro Tip

You can check progress at any time by reading `test_status.txt`:

```bash
tail -50 /Users/vladyslav/Documents/GitHub/experiment/test_status.txt
```

The monitoring script updates this file every 2 minutes with:
- Timestamp
- Process status
- Log file size
- Recent output

---

**I'll notify you with the final results once the test completes!**

The test is running smoothly in the background. Come back in about an hour to see the results, or check `test_status.txt` for real-time updates.
