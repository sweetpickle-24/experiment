# Archive

**Last Updated**: 2026-09-05

Superseded documents, kept for the record. **Nothing here is current and nothing here
should be cited.**

- `deprecated/` — status documents, checklists and index files replaced by the
  current [README](../README.md)
- `historical/` — earlier write-ups of the concentration invariance work and of the
  GPU/MLX porting effort

Every file carrying a claim that failed the 2026-09-03 audit has a correction banner
at the top and its withdrawn figures replaced with `[withdrawn]`. The four most
common problems in these documents:

1. **Validation scores that no run produced.** Files here quote 9/9, 13/13, 14/14 and
   27/27. None of those was ever produced. The recorded history is 3/5 (2026-03-15),
   1/5 (2026-09-03, the first seeded run), 2/5 (2026-09-04, after the benchmark
   targets were checked against their sources), and **5/5** (2026-09-05, after the
   input projection was corrected — `results/final/all_validations_G2.json`).
2. **"1.65% KC sparsity matching Turner et al. 2008."** That figure appears in no
   result file, and KC sparsity is imposed by a rank threshold in the readout rather
   than measured. It is still imposed today, at 310 of 5,177 cells.
3. **"Concentration invariance r = 0.724."** That run included isoamyl acetate, which
   was absent from the DoOR database and produced an all-zero stimulus correlating
   with itself at 1.0. On real odorants that run gives 0.587. The current value is
   0.6603, and it is deliberately **not scored**, because the 0.70 threshold it used
   to be compared against is not in the paper it was cited to.
4. **"86× GPU speedup"** and **"1,283 active KCs"**. Both come from a single result
   file now in `results/superseded/`, which also recorded a null pattern correlation
   and `validation_passed: true` against a criterion it never evaluated. The verified
   speedup is **10.00×**.

For what is current, see [docs/00_START_HERE.md](../docs/00_START_HERE.md).

See [`results/README.md`](../results/README.md) for which artifact backs which claim,
and `hive/validation/invalid/README.md` for the two tests withdrawn as unfalsifiable.

This directory is a candidate for deletion. The git history preserves everything in
it, and its only current function is to document what was previously claimed.
