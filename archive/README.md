# Archive

**Last Updated**: 2026-09-03

Superseded documents, kept for the record. **Nothing here is current and nothing here
should be cited.**

- `deprecated/` — status documents, checklists and index files replaced by the
  current [README](../README.md)
- `historical/` — earlier write-ups of the concentration invariance work and of the
  GPU/MLX porting effort

Every file carrying a claim that failed the 2026-09-03 audit has a correction banner
at the top and its withdrawn figures replaced with `[withdrawn]`. The three most
common problems in these documents:

1. **Validation scores that no run produced.** Files here quote 9/9, 13/13, 14/14 and
   27/27. The best score ever recorded was 3/5, and the most recent run, the first
   seeded one, gave 1/5.
2. **"1.65% KC sparsity matching Turner et al. 2008."** That figure appears in no
   result file, and KC sparsity is imposed by a rank threshold in the readout rather
   than measured.
3. **"Concentration invariance r = 0.724."** That run included isoamyl acetate, which
   is absent from the DoOR database and produces an all-zero stimulus that correlates
   with itself at 1.0. On real odors the value is 0.587, below the 0.70 target.

See [`results/README.md`](../results/README.md) for which artifact backs which claim,
and `hive/validation/invalid/README.md` for the two tests withdrawn as unfalsifiable.

This directory is a candidate for deletion. The git history preserves everything in
it, and its only current function is to document what was previously claimed.
