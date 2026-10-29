# Corrections and amendments log

Automatic entries: code-version changes (from docs/CHANGELOG.md), failed steps (OPEN)
and their later successful re-runs (RESOLVED). You may add manual notes at the end.

## 2026-10-22 17:19:31 | CODE FIRST INSTALL | - -> v1
- zip: execution_plan_mesd_v1_code.zip sha256 6708e28f0a566b34...
- Package file is named execution_plan_mesd_v<N>_code.zip so it is never confused with other
  projects' execution_plan_v*_code.zip files in MyDrive; the bootstrap accepts only zips that
  contain this package (code/mesd_common.py) and tolerates a zip re-packed with a top folder.
- Engine scripts are the tested cells of the execution plan (Cells 01, 02, 03a, 03, 04, 05),
  unchanged in method. Changes are limited to plumbing:
  - paths come from the runner (work/main, work/smoke, work/sens_cal10) instead of a Drive mount in every cell;
  - settings that differ between steps (target, debug, calibration fraction, ensemble size used,
    seeds) are passed as environment variables and written to the run registry.
- Figures re-sized for the two-column conference layout: 3.5 in (one column) or 7.16 in (two
  columns), 600 dpi PNG plus vector PDF with embedded TrueType fonts; Figure 2 is now a 2 x 4 grid.
- New Step 3.0 smoke test (3% of curves, 2 epochs) in its own folder, so a broken pipeline is
  found in minutes instead of after hours of GPU training.
- New sensitivity steps: 6.1 (3 vs 5 ensemble members, no retraining), 6.2 (calibration
  fraction 10% vs 20%, seed 0, 12 runs), 6.3 (summary and LOPO coverage by compact-model family).
- New Step 7.0: FINAL_SUMMARY.md and a frozen export zip with SHA-256 checksums.
- Records: per-step logs, run_registry.csv, errors.log, AMENDMENTS.md (OPEN / RESOLVED),
  environment_log.txt, installed_versions.csv, manifest verification of the installed code.
- Literature: added the ESDED dataset descriptor (same research group as MESD, different devices)
  as related work; reference list rebuilt from Crossref metadata (docs/REFERENCES_IEEE.md).
  Correct DOI of Ortiz-Conde et al. (2002): 10.1016/S0026-2714(02)00027-6 (the execution-plan
  docx cited this paper without a DOI; use this one).
- Known limitation, by design: the Cgg models reuse epochs and learning rate tuned for Id.

## 2026-10-22 18:50:19 | CODE UPGRADE | v1 -> v2
- zip: execution_plan_mesd_v2_code.zip sha256 54d8c21a41ea8196...
- Cells renumbered to the plan's step numbers: 1 build/audit, 2 features/splits, 3 tuning,
  4 smoke test, 5 training, 6 accuracy gate, 7 evaluation, 8 tables/figures/hypotheses,
  9.4-9.8 the same for Cgg (plan Step 9 = repeat Steps 4-8), 10.1-10.6 sensitivity, 11 export.
- Every cell ends with a STEP CHECK LOG: one [PASS]/[FAIL]/[WARN] line per check with the
  expected value from the plan and the value obtained, and a final RESULT line saying whether to
  proceed. Logged to records/step_checks.csv, records/step_status.json and records/reports/.
- Cells refuse to start unless their prerequisite steps PASSED (plan: "do not continue until the
  checkpoint passes"). In particular Step 7 needs the Step 6 accuracy gate.
- NEW Step 6 / 9.6 accuracy gate exactly as in the plan (S0, mean of 5 seeds: median relative
  error above threshold <= 5%, MAE <= 0.05 decades, subthreshold MAE <= 0.10 decades).
- Step 7 checks the plan's sanity values (S0 domain AUC 0.45-0.55; S1-S4 domain AUC >= 0.99;
  S0 SCP-ens coverage 0.89-0.91 with CI containing 0.90; S0 SCP-curve whole-curve coverage
  0.88-0.92; no above-threshold non-monotonic true curves).
- Step 8 applies the decision rules of plan section 6 (H1-H5, RQ3, confirmatory Wilcoxon/Holm)
  and writes records/hypotheses_results.txt.
- Sensitivity analyses now follow plan Step 10 exactly:
  calibration fraction 0.10 retrained for S0 and S4 with all seeds (v1: seed 0, all scenarios);
  model-family control retrained on BSIM4 PDKs only (N40A, N45B, N55A, N180B) for S4 (v1 had
  only a descriptive table); ensemble size 3 uses members 0-2 of the 5-member runs, which are
  exactly the networks a 3-member run would train (same seeds 1000*seed + k, k = 0, 1, 2);
  coverage level from alpha = 0.20 / 0.10 / 0.05 with method ranks.
- Step 1 writes dataset_flags.json (commit, Monte Carlo flag, counts) so the check is file-based.
- Memory: Step 2 and training use categorical split tables (identical outputs, verified on all
  60 split definitions; peak RAM with pandas 2.2 down from >7.8 GB to about 5 GB in Step 2 and
  from 5.5 to 2.8 GB in training).

## 2026-10-22 20:20:46 | CODE UPGRADE | v2 -> v3
- zip: execution_plan_mesd_v3_code.zip sha256 a5d5b2c474b9ee80...
- Every computing step now has a fingerprint (hash of its engine code with comments and formatting
  ignored, its settings, and the fingerprints of the steps it depends on), stored in
  records/fingerprints.json. Re-running a cell REUSES its outputs when the fingerprint is unchanged.
  When an amendment changes the code of a step, or an upstream result, the old outputs are moved to
  <work>/_superseded/ (never deleted), the step is recomputed, and a RECOMPUTE entry is written to
  records/AMENDMENTS.md. Downstream steps follow automatically (new training -> new evaluation).
- Training (Steps 5, 9.5, 10.2, 10.4) is checkpointed per run: each prediction file has a .fp
  fingerprint file and is written atomically (a disconnect never leaves a half-written file).
- Evaluation (Steps 7, 9.7, 10.1, 10.3, 10.5) is checkpointed per prediction file (results/<target>/parts/),
  so an interrupted evaluation resumes and an unchanged one takes seconds.
- Steps 1-3 outputs made under v2 are ADOPTED (fingerprints recorded at Step 0.0, nothing recomputed).
  Step 3 is frozen: tuning.json is never re-tuned unless the tuning code or the splits are amended
  (plan: "never re-run Cell 03a after seeing results").
- Step 3 check log: the "winning configuration" line is now INFO (plan: whatever tuning.json says is
  final), plus INFO lines on the 100-epoch result and the effect of the W/L normalisation.
- Step 3 result of 22 Oct 2026 (T4, full data): 60 epochs, lr 5e-3, W/L normalisation;
  inner-validation MAE 0.0074 decades, median relative error above Vth 0.86%. The 100-epoch run at
  the same lr ended with a higher training loss (5.0e-4 vs 3.0e-5) and a worse validation MAE (0.034):
  a sign of late-schedule instability at lr 5e-3 on a single seed. This is reported, not acted on;
  the per-run loss check in Step 5 and the accuracy gate in Step 6 guard against it.
- docs/MESD_Research_Proposal.docx: the detailed research proposal with references.

## 2026-10-23 03:57:39 | OPEN | step7_eval_Id INTERRUPTED
- code version: v3
- error: KeyboardInterrupt: 
- log: logs/step7_eval_Id_20261023_035730.log (traceback also in records/errors.log)
- action: send the log to the analyst; fix arrives as a new execution_plan_mesd_v*_code.zip

## 2026-10-23 04:24:42 | RESOLVED | step7_eval_Id
- re-run succeeded with code version v3 (log: logs/step7_eval_Id_20261023_035847.log)

## 2026-10-23 04:53:22 | CODE UPGRADE | v3 -> v4
- zip: execution_plan_mesd_v4_code.zip sha256 b7d73fdcf6e90d7b...
- The paper figures (Steps 8 and 9.8) now use the author's figstyle.py (Times-like serif text at final
  size, 8.5 cm single-column / 15 cm double-column figures, 600 dpi PNG + vector PDF with embedded fonts,
  every series distinguished by colour AND line style AND marker, panel labels (a), (b) outside the axes,
  legends placed where they hide the least data).
- Colours follow Kaspar & Crameri, Angew. Chem. Int. Ed. 61 (2022) e202114910: colour is optional
  (figures read fully in greyscale), series colours are sampled from the perceptually uniform,
  colour-vision-deficiency-safe scientific colour map batlow (Crameri) with monotonic lightness, no
  rainbow, no red-green pairs, and every figure's plotted numbers are written to <figure>_data.csv.
- Figure 4 now shows coverage per held-out PDK as categories ordered by node (two PDKs share 45 nm and
  two share 180 nm, so the numeric node axis drew misleading vertical joins); file renamed to
  fig4_lopo_coverage_by_pdk. Figure 6 legend moved above the bars; Figure 5 axis labels in plain numbers.
- Nothing upstream changes: Steps 1-7 keep their checkpoints (no retraining, no re-evaluation). Only
  Step 8 (and later 9.8) draws the figures with the new style; figstyle.py is part of its fingerprint.

## 2026-10-23 05:02:46 | CODE UPGRADE | v4 -> v5
- zip: execution_plan_mesd_v5_code.zip sha256 e64727df515d2a88...
- Step 8 v4 reported "CQR vs SCP-ens: significant" without saying which way. The exact Wilcoxon test is
  two-sided; CQR is significantly FARTHER from 0.90 than SCP-ens (median gap 0.871 vs 0.798, closer in
  only 1 of 8 folds), not better. Table 4 now has the columns folds_closer_to_090 and direction, plus a
  note that WCP's coverage under shift comes from infinite intervals, and the CONFIRMATORY lines of the
  check log say BETTER or WORSE. The p values and Holm correction are unchanged.
- Figure 1: the 40,000 scatter markers are rasterized inside the PDF (text and axes stay vector), so
  the PDF is small and opens quickly.
- H2 rule text now says what "worst group" is: the worst PDK x region group with >= 1000 points.
- Only Step 8 is recomputed (about 0.5 min, CPU). Steps 1-7 keep their checkpoints.

## 2026-10-23 05:05:11 | OPEN | step9_4_smoke_train INTERRUPTED
- code version: v5
- error: KeyboardInterrupt: 
- log: logs/step9_4_smoke_train_20261023_050508.log (traceback also in records/errors.log)
- action: send the log to the analyst; fix arrives as a new execution_plan_mesd_v*_code.zip

## 2026-10-23 05:06:16 | RESOLVED | step9_4_smoke_train
- re-run succeeded with code version v5 (log: logs/step9_4_smoke_train_20261023_050555.log)

## 2026-10-23 05:20:31 | CODE UPGRADE | v5 -> v6
- zip: execution_plan_mesd_v6_code.zip sha256 1a4c919f2c303d0c...
- Legends inside the plot area are drawn in a box with a thin (0.5 pt) border and an opaque white
  fill, set 0.9 x font size in from the axes so the box never touches the inward ticks. The position is
  chosen so the box covers NO marker, NO line (line segments are now tested along their length, not
  only at their vertices; the 0.90 reference line counts), no bar and no text. If no such position
  exists inside, the legend goes outside the axes (frameless). Legend symbols in Fig. 1 are opaque.
- Every figure is audited before it is written: legend vs data, every pair of texts (tick labels,
  axis labels, titles, panel labels, annotations, legends), annotations vs data. The result is printed
  for each figure, saved in paper/<target>/figure_audit.csv and checked in the Step 8 / 9.8 check log
  ("no overlaps"). The size printed is now the REAL size of the written PNG.
- The audit found a real overlap in the v5 Figure 5 on the Step 7 data (minor y tick labels 0.6, 0.7,
  0.8, 0.9 collided); minor ticks are now labelled only at 2 and 5 of each decade.
- Step 9.4 / 9.8 print "(no curve-level Vth checks for this target)" instead of an empty table for Cgg.
- Only the figure steps are recomputed (Step 8, about 0.5 min, CPU). No training or evaluation.

## 2026-10-23 05:20:45 | RECOMPUTE | figs:y_logId
- fingerprint cca005dfe38f9439 -> 6232a5b28b840fe0 (code v6)
- previous outputs archived in work/main/_superseded/figs_y_logId_20261023_052045

## 2026-10-23 12:35:02 | CODE UPGRADE | v6 -> v7
- zip: execution_plan_mesd_v7_code.zip sha256 45d031f593803fa2...
- New Drive folders next to work/: `mesd_v1/figures/Id/` and `figures/Cgg/` hold every final figure as
  PNG (600 dpi) and PDF; `mesd_v1/results/Id/`, `results/Cgg/`, `results/sensitivity/` and
  `results/summary/` hold the paper tables, figure data, figure audit, per-run results
  (results_long.csv), curve checks, hypothesis decisions, sensitivity tables and the final summary.
  They are refreshed by Step 0.0 and by every step's check log (block "COPIED TO DRIVE"). The
  originals and checkpoints stay in work/main/. Smoke-test outputs are not copied.
- docs/DATASET_VERSION_NOTE.md + MESD_vs_MESD2.0_comparison.csv: the study uses MESD2.0 (commit
  5dcc223); all 45 files were compared with the v1.0.0 folder MESD/. Ids and Cgg are identical to 5
  significant digits except the N45A Cgg curves, which were re-simulated in MESD2.0.
- No engine code changed: nothing is recomputed.

## 2026-10-23 13:08:36 | CODE UPGRADE | v7 -> v8
- zip: execution_plan_mesd_v8_code.zip sha256 0e13a928759bccc3...
- Step 9.8 (Cgg, run on Colab) reported 4 overlaps in Figure 2: the infinity marks of the WCP panel
  touched the dashed 0.90 line (the same layout was clean on this machine; text metrics differ
  between matplotlib versions). The marks now sit ABOVE their marker, where no data can be
  (coverage <= 1), the y axis of Figure 2 has headroom to 1.17 (ticks still 0 to 1.0), and every mark
  is checked against the data as it is drawn and moved further up if it touches anything.
- Steps 6 and 9.6 (accuracy gates) now also require the training step they check (5 and 9.5).
- Only the figure steps are recomputed (Steps 8 and 9.8, about 0.5 min each, CPU).

## 2026-10-23 13:11:01 | RECOMPUTE | figs:y_logId
- fingerprint 6232a5b28b840fe0 -> 94b374adf0c09d9d (code v8)
- previous outputs archived in work/main/_superseded/figs_y_logId_20261023_131101

## 2026-10-23 13:12:17 | RECOMPUTE | figs:y_logCgg
- fingerprint 61b98f0d48b11468 -> 53a7086d23fb1f24 (code v8)
- previous outputs archived in work/main/_superseded/figs_y_logCgg_20261023_131217

## 2026-10-23 20:02:08 | CODE UPGRADE | v8 -> v9
- zip: execution_plan_mesd_v9_code.zip sha256 d0d44789abe821d8...
- Correction of a design error. The MESD2.0 header of the N45A files has no Model field, so the
  proposal, the plan and code v1-v8 listed N45A as "unknown" and the BSIM4-only control (Steps
  10.4-10.5) used 4 PDKs. The MESD v1.0.0 header says N45A is BSIM4.0. The control now uses all 5
  BSIM4 PDKs (N40A, N45A, N45B, N55A, N180B): Step 10.4 trains 15 runs (5 held-out PDKs x 3 seeds).
- Because the Step 10.4 settings changed, its checkpoint no longer matches: re-running Step 10.4
  moves the 4-PDK outputs to work/sens_bsim4/_superseded/ (kept, not deleted) and trains the 15 runs.
  Nothing else is recomputed (Steps 1-10.3 keep their checkpoints).
- Step 10.6 compares main vs BSIM4-only S4 coverage on the 5 BSIM4 folds and adds a mean row.
- Research proposal (docs/MESD_Research_Proposal.docx, version 4) and DATASET_VERSION_NOTE.md
  corrected: BSIM4.x = N40A, N45A, N45B, N55A, N180B; BSIM3v3 = N90A, N180A, N350A.

## 2026-10-23 20:03:28 | RECOMPUTE | splits:sens_bsim4
- fingerprint a4bd81916b3f8a1e -> 2f0a4b537e925da5 (code v9)
- previous outputs archived in work/sens_bsim4/_superseded/splits_sens_bsim4_20261023_200328

## 2026-10-23 20:03:54 | RECOMPUTE | train:sens_bsim4:y_logId
- fingerprint 7d919375703638b1 -> db2488d89e3ecb53 (code v9)
- outdated per-run outputs moved to _superseded/ by the engine

## 2026-10-24 06:42:57 | CODE UPGRADE | v9 -> v10
- zip: execution_plan_mesd_v10_code.zip sha256 b4931b9e85441a75...
- Step 10.6, model-family table: the column labels said "main (8 PDKs in training pool)" and
  "BSIM4 only (5 PDKs)", but in leave-one-PDK-out each fold trains on one PDK fewer. They now read
  "main (7 training PDKs per fold)" and "BSIM4 only (4 training PDKs per fold)". Numbers unchanged.
- Only Step 10.6 is recomputed (seconds). Then run Step 11.

