# Changelog of the pipeline code

Step 0.0 (the bootstrap) copies the section of the installed version into `records/AMENDMENTS.md`, so
every code change is recorded with its date. Newest version first. Version v10 produced all results in
this repository.

## v10 (24 Oct 2026) - sensitivity table labels
- Step 10.6, model-family table: column labels now state the number of training PDKs per fold
  ("main (7 training PDKs per fold)", "BSIM4 only (4 training PDKs per fold)"). Numbers unchanged.
- Only Step 10.6 is recomputed (seconds), then Step 11.

## v9 (23 Oct 2026) - model-family control uses all five BSIM4 PDKs
- The MESD2.0 header of the N45A files has no Model field, so N45A had been treated as "model unknown"
  and the BSIM4-only control (Steps 10.4-10.5) used four PDKs. The MESD v1.0.0 header gives BSIM4.0 for
  N45A. The control now uses N40A, N45A, N45B, N55A and N180B (15 runs: 5 held-out PDKs x 3 seeds).
  The four-PDK outputs are kept in `work/sens_bsim4/_superseded/`. This is the one amendment of the
  study; it is reported in the paper.
- Step 10.6 compares main vs BSIM4-only S4 coverage on the five BSIM4 folds.

## v8 (23 Oct 2026) - figure layout
- Figure 2: infinity marks placed above their markers so they never touch the 0.90 line; y axis
  headroom to 1.17.
- Steps 6 and 9.6 (accuracy gates) also require the training step they check.
- Only the figure steps are recomputed.

## v7 (23 Oct 2026) - output folders; dataset version documented
- New folders `figures/` and `results/` next to `work/` hold copies of every final figure and table.
- `docs/DATASET_VERSION_NOTE.md` and `MESD_vs_MESD2.0_comparison.csv` document the dataset version.
- No engine code changed; nothing recomputed.

## v6 (23 Oct 2026) - legends and overlap audit
- Legends drawn where they cover no data; every figure is audited for overlapping elements before it is
  written (`figure_audit.csv`). Only the figure steps are recomputed.

## v5 (23 Oct 2026) - direction of every paired test
- The paired-test table states whether each method is closer to or farther from 0.90 than SCP-ens
  (the exact Wilcoxon test is two-sided). p values and Holm correction unchanged.
- Figure 1 scatter rasterized inside the PDF. Only Step 8 is recomputed.

## v4 (23 Oct 2026) - figure standard
- Figures use `figstyle.py` (serif text at final size, 8.5 or 15 cm wide, 600 dpi PNG and vector PDF,
  colour + line style + marker per series) with colours from the batlow map (Kaspar & Crameri 2022);
  the data of every figure is written to `<figure>_data.csv`. Only Step 8 is recomputed.

## v3 (22 Oct 2026) - checkpoints
- Every computing step has a fingerprint (code, settings, upstream fingerprints) in
  `records/fingerprints.json`; unchanged steps reuse their outputs, changed steps move old outputs to
  `_superseded/` and recompute. Training and evaluation are checkpointed per run.
- Step 3 tuning frozen: 60 epochs, peak learning rate 5e-3, W/L normalisation.

## v2 (22 Oct 2026) - PASS/FAIL check logs
- Steps numbered as in the execution plan; every step ends with a check log comparing its outputs with
  the values fixed in the plan; a step refuses to start until its prerequisites have passed.
- Accuracy gate (Steps 6, 9.6) before any shifted split is evaluated; hypotheses H1-H5 decided by the
  pre-specified rules in Step 8.
- Sensitivity analyses as planned: calibration fraction 0.10 (S0, S4, all seeds), model-family control,
  ensemble size 3, coverage level 0.80 / 0.90 / 0.95.

## v1 (22 Oct 2026) - first Colab package
- Engine scripts, run registry, logs, amendments log, environment log, manifest verification, smoke
  tests, final summary and frozen export with SHA-256 checksums.
- Known limitation, by design: the Cgg models reuse the epochs and learning rate tuned for Id.
