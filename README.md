# Conformal uncertainty intervals for neural MOSFET models under shift

Code, check logs, figure data and frozen results for the paper

> J. M. Omar and M. Tan, *Conformal uncertainty intervals for neural MOSFET models under geometry,
> temperature, process-corner, and technology shift* (manuscript; the full reference will be added on publication).

Archived release (Zenodo DOI): to be added after the first release.

The study trains deep ensembles for log10 I_D and log10 C_gg on the public MOSFET Electrical
Simulation Dataset (MESD; Zhang et al., 2024) and compares eight interval methods (split, normalized,
quantile-based, group-wise (Mondrian), curve-level and weighted conformal prediction, plus a Gaussian
ensemble interval) under five pre-specified, curve-level splits: random (S0), extreme channel length
(S1), 125 °C (S2), fast-fast corner (S3) and leave-one-PDK-out (S4).

This repository contains everything needed to (a) check every number in the paper against the
files that produced it and (b) rerun the whole study from the raw dataset. It does **not** contain
the MESD dataset itself; the pipeline downloads it at a pinned commit.

---

## 1. Contents

| Folder / file | What it holds |
|---|---|
| `code/` | The pipeline, code version **v10**, exactly as run. `step*.py` are the Colab cells (one per step of the execution plan), `engine/mesd_0*.py` do the work, `mesd_common.py` handles checkpoints, logs and prerequisite checks, `mesd_report.py` writes the PASS/FAIL check logs, `engine/figstyle.py` is the figure standard. `MANIFEST.sha256` lists the SHA-256 of every file in `code/` and `docs/`; the bootstrap checks it in every session. |
| `docs/` | `COLAB_CELLS.txt` (all pipeline cells, ready to paste), `CHANGELOG.md` (code versions v1 to v10), `DATASET_VERSION_NOTE.md` and `MESD_vs_MESD2.0_comparison.csv` (which MESD version is used and how it differs from the v1.0.0 release). |
| `results/Id/`, `results/Cgg/` | Paper tables (`table*.csv`), the data behind every figure (`fig*_data.csv`), the figure overlap audit, the long-format result file of every run and method (`results_long.csv`), per-curve checks (`curve_checks.csv.gz`, I_D only) and the hypothesis decisions (`hypotheses_results.txt`, I_D). |
| `results/sensitivity/` | The four pre-specified sensitivity analyses (ensemble size, calibration size, BSIM4-only model family, coverage level) and the long result files of the two re-trained variants. |
| `results/summary/FINAL_SUMMARY.md` | Key numbers of the frozen run (Step 11). |
| `figures/Id/`, `figures/Cgg/` | Every pipeline figure, 600 dpi PNG and vector PDF. |
| `figures/architecture/`, `figures/paper_combined/` | Figures as they appear in the paper (made by the cells in `colab/paper_figures/` from the frozen files; no numbers are recomputed). |
| `records/` | Run registry, environment log (Python and package versions, GPU, RAM of every session), PASS/FAIL status of every step, every single check (`step_checks.csv`), the full check log of every cell run (`reports/`), amendments log, code fingerprints, MESD commit. |
| `logs/` | One log per run of every step. |
| `work/` | Small working files needed to audit or redraw: tuned hyperparameters (`tuning.json`, `tuning_log.csv`), device anchors, per-file data audit, dataset flags, training logs (`train_log.jsonl`). Large intermediate files (parquet tables, predictions) are not included; the pipeline regenerates them. |
| `colab/` | `00_setup_from_github.py` (rerun the study from this repository), `paper_figures/` (Figures 2, 4, 5 and 6 of the paper), `build_and_push_repo.py` (the cell that assembled this repository from the project folder). |
| `verification/` | Independent scripts, not importing `code/`: `verify_checksums.py` (all checksums), `audit_raw_mesd.py` (dataset facts of Section 3 from the raw JSON), `compare_mesd2_vs_v1.py` (MESD2.0 against the v1.0.0 release). |
| `CHECKSUMS.sha256` | SHA-256 of every file in this repository; `GZIP_ORIGINALS.sha256` gives the hashes of the uncompressed `.gz` files. |
| `REPO_BUILD_REPORT.md` | How this repository was assembled and which files are byte-identical to the frozen export. |

At the end of the run, Step 11 froze all results in an export archive (`MESD_results_v10_20261024_064350.zip`,
331 files with their own SHA-256 list; SHA-256 of the archive `0445fd21c8d382cd9403db548916c8c972606d707421338fee2722c791f5edb7`).
`REPO_BUILD_REPORT.md` shows, file by file, that the tables, figure data and results published here are
byte-identical to that archive. The archive itself is kept by the authors and available on request.

## 2. Where each number and figure of the paper comes from

| Paper item | File(s) in this repository |
|---|---|
| Section 3, dataset counts and the C_gs artefact | `records/reports/step_1_*.txt`, `work/main/audit_per_file.csv`, `work/main/dataset_flags.json`; independent check: `verification/audit_raw_mesd.py` |
| Section 3, MESD2.0 vs v1.0.0 | `docs/DATASET_VERSION_NOTE.md`, `docs/MESD_vs_MESD2.0_comparison.csv`; independent check: `verification/compare_mesd2_vs_v1.py` |
| Figure 1 (stored C_gs vs g_m/2πf) | `figures/Id/fig1_audit_cgs_artifact.*`, data `results/Id/fig1_audit_cgs_artifact_data.csv` |
| Table 1 (splits, test curves) | `records/reports/step_2_*.txt` (split counts, seed 0) |
| Figure 2 (architecture) | `figures/architecture/fig_architecture.*`, facts read from the code in `fig_architecture_facts.json`; cell `colab/paper_figures/fig2_architecture_cell.py` |
| Section 4, tuned hyperparameters | `work/main/tuning.json`, `work/main/tuning_log.csv`, `records/reports/step_3_*.txt` |
| Section 4, run times and software versions | `records/run_registry.csv`, `records/environment_log.txt`, `logs/step05_*`, `logs/step09_5_*` |
| Table 2 (accuracy) | `results/Id/table1_accuracy.csv`, `results/Cgg/table1_accuracy.csv` |
| Table 3 (point coverage) | `results/Id/table2_coverage_alpha0.10.csv`, `results/Cgg/table2_coverage_alpha0.10.csv` |
| Figure 3 (coverage by method and split) | `figures/Id/fig2_coverage_by_method.*`, data `results/Id/fig2_coverage_by_method_data.csv` |
| Figure 4 (a) coverage per held-out PDK, (b) whole-curve coverage | `figures/paper_combined/fig3_lopo_and_curve_coverage.*`; data `results/Id/fig4_lopo_coverage_by_pdk_data.csv`, `results/Id/fig6_curve_coverage_data.csv`; per-PDK table `results/Id/table3_lopo_coverage_by_pdk.csv`; cell `colab/paper_figures/fig4_fig5_side_by_side_cell.py` |
| Table 4 (hypotheses H1 to H5) | `results/Id/hypotheses_results.txt` (also `records/hypotheses_results.txt`) |
| Table 5 (paired tests on the 8 held-out PDKs) | `results/Id/table4_lopo_paired_tests.csv`, `results/Cgg/table4_lopo_paired_tests.csv` |
| Figure 5 (recalibration with k target curves) | `figures/paper_combined/fig4_recalibration_budget_Id_Cgg.*`; data `results/Id/fig3_recalibration_budget_data.csv`, `results/Cgg/fig3_recalibration_budget_data.csv` |
| Figure 6 (width after recalibration) | `figures/paper_combined/fig6_recalibration_width.*` (cell `colab/paper_figures/fig6_recalibration_width_cell.py`; same plot as `figures/Id/fig5_recalibration_width.*` with US spelling); data `results/Id/fig5_recalibration_width_data.csv` |
| Table 6 (sensitivity analyses) | `results/sensitivity/sens_ensemble_and_calibration_size.csv`, `sens_model_family_bsim4.csv`, `sens_coverage_level.csv`; check logs `records/reports/step_10.*` |
| Whole-curve and V_th checks | `results/Id/table1b_curve_checks.csv`, `results/Id/curve_checks.csv.gz` |
| Every other number | `results/<target>/results_long.csv` (one row per run, method, split and nominal level) |

The figure files in `figures/Id/` and `figures/Cgg/` carry the pipeline's own numbering
(`fig1` to `fig6`), which differs from the paper's numbering; use the table above.

## 3. Checking the files (no GPU, a few minutes)

```bash
git clone https://github.com/johmar-22/mesd-conformal-uncertainty.git
cd mesd-conformal-uncertainty
python verification/verify_checksums.py            # every file, the code manifest and the .gz originals
```

Expected output ends with `ALL CHECKS PASSED`. The repository marks every file as binary in
`.gitattributes`, so line endings are never converted and the checksums hold on Windows as well.

To re-check the dataset facts directly from the raw MESD files (CPU, a few minutes; the clone needs about 1.5 GB of disk):

```bash
git clone https://github.com/SJTU-YONGFU-RESEARCH-GRP/MESD-MOSFET-Electrical-Simulation-Dataset mesd_data
git -C mesd_data checkout 5dcc2236ac5b5eeb6228503f544053c2a359b636
pip install numpy
python verification/audit_raw_mesd.py mesd_data
python verification/compare_mesd2_vs_v1.py mesd_data
```

## 4. Rerunning the study

### 4.1 Data

MESD (Zhang et al., 2024), folder `MESD2.0/` at commit
`5dcc2236ac5b5eeb6228503f544053c2a359b636` (26 December 2025) of
<https://github.com/SJTU-YONGFU-RESEARCH-GRP/MESD-MOSFET-Electrical-Simulation-Dataset>
(CC BY 4.0). Step 1 clones the repository and checks out this commit; nothing has to be downloaded by hand.

### 4.2 Environment

The study ran in Google Colab (Pro), NVIDIA Tesla T4 (15 GB) for training, High-RAM runtime (51 GB),
Python 3.13 (3.13.15 or 3.13.16, depending on the session). Package versions, recorded at the start of
every session in `records/environment_log.txt`, are pinned in `requirements.txt`:

| package | version |
|---|---|
| torch | 2.11.0 (+cu130 on GPU) |
| numpy | 2.1.3 |
| pandas | 2.2.3 |
| pyarrow | 23.0.1 |
| scipy | 1.16.3 |
| scikit-learn | 1.6.1 |
| matplotlib | 3.10.0 |

Colab's preinstalled versions change over time. Step 0.0 logs whatever it finds; if they differ from
the table, install the pinned versions first (`pip install -r requirements.txt`, then restart the
runtime). Neural-network training on a GPU is not bit-reproducible across GPU types, driver and
library versions even with fixed seeds, so expect small differences in the third decimal of the
results; the check logs compare every output with its expected value and show where yours differ.

### 4.3 Steps

The pipeline is a sequence of Colab cells, each with a PASS/FAIL check log against values written
into the execution plan before the run. Each cell refuses to start until its prerequisite steps have
passed, and every training cell resumes after a disconnect.

1. Open a new Colab notebook and paste `colab/00_setup_from_github.py` into the first cell. It mounts
   your Google Drive, clones this repository, packs `code/` and `docs/` into
   `MyDrive/execution_plan_mesd_v10_code.zip` (the package format the bootstrap expects), checks it
   against `code/MANIFEST.sha256`, and runs the first-time bootstrap. All outputs go to
   `MyDrive/mesd_v1/` (change `BASE` in the cell to use another folder).
2. Paste the cells of `docs/COLAB_CELLS.txt` one per Colab cell and run them in order, in three
   sessions (changing the runtime type restarts the session):

| Session | Runtime | Steps | Measured time in this study |
|---|---|---|---|
| A | CPU (High-RAM recommended) | 0.0, 1, 2 | 1.7 + 0.5 min |
| B | GPU + High-RAM | 0.0, 3, 4, 5, 6, 9.4, 9.5, 9.6, 10.2, 10.4 | Step 3: 6.5 min; Step 5: 6.8 h (44 runs); Step 9.5: 7.0 h (44 runs); Step 10.2: 4.9 h (29 runs); Step 10.4: 1.3 h (15 runs) |
| C | CPU + High-RAM | 0.0, 7, 8, 9.7, 9.8, 10.1, 10.3, 10.5, 10.6, 11 | Step 7: 26 min; Step 9.7: 18 min; Step 10.1: 21 min; Step 10.3: 11 min; Step 10.5: 6 min; others under 4 min |

   In total about 22 h of compute, about 20 h of it on the T4 GPU (from `records/run_registry.csv`).
3. Step 11 writes `records/FINAL_SUMMARY.md` and a new export archive. Compare your
   `results/` with the files in this repository, for example
   `results/Id/table2_coverage_alpha0.10.csv`.
4. Redraw the paper figures with the cells in `colab/paper_figures/` (CPU, seconds).

Each cell ends with a check log between two banner lines: `PASS` means continue with the step named in
the RESULT line, `FAIL` means stop (the next cell refuses to start until the failed step passes). The
same text is saved in `records/reports/`, every single check in `records/step_checks.csv`. After a
disconnect, run Step 0.0 and the same cell again; finished runs are skipped.

### 4.4 What is fixed in advance

MESD commit; hyperparameters chosen on inner-validation curves of the S0 training data only and
frozen (Step 3); accuracy gate on S0 before any shifted split is evaluated (Step 6); splits by whole
curve, device-anchor curves never used for calibration or testing; hypotheses H1 to H5 and their
decision rules; confirmatory tests only on the 8 leave-one-PDK-out folds (exact Wilcoxon signed-rank,
Holm correction over NCP, SCP-curve and CQR). The one amendment made during the study (model-family
control with five instead of four BSIM4 PDKs) is documented in `records/AMENDMENTS.md`,
`docs/CHANGELOG.md` (v9) and the paper.

## 5. Licence

* Code (`code/`, `colab/`, `verification/`): MIT licence, see `LICENSE`.
* Results, figures, logs and records: CC BY 4.0, see `DATA_LICENSE.md`. They are derived from MESD,
  which is itself CC BY 4.0 (Zhang et al., 2024); please cite both.

## 6. Citation

Please cite the paper (reference to be updated on publication) and this repository; GitHub's
"Cite this repository" button uses `CITATION.cff`. Please also cite the dataset:

Zhang, Y., Low, K. L., Li, L., Shao, L., Sun, Y., Zhao, J., Sun, Y., Shi, Y., & Li, Y. (2024).
Descriptor: MOSFET electrical simulation dataset (MESD). *IEEE Data Descriptions, 1*, 27–32.
<https://doi.org/10.1109/IEEEDATA.2024.3481356>

## 7. Contact

Muhammed Tan (corresponding author), Department of Electrical and Electronics Engineering,
Kastamonu University, Türkiye. Questions about the code: please open a GitHub issue.
