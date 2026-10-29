# How this repository was built

- built: 2026-10-29 by `colab/build_and_push_repo.py` from the project folder `mesd_v1` on Google Drive
- code version: v10; the 33 files in `code/` are byte-identical to the files that produced the results (SHA-256 equal to the entries of the manifest verified by the pipeline in every session); `code/MANIFEST.sha256` lists them and the documentation files in `docs/`
- frozen export of Step 11: `MESD_results_v10_20261024_064350.zip` (331 files, verified against its `EXPORT_SHA256.txt`), SHA-256 `0445fd21c8d382cd9403db548916c8c972606d707421338fee2722c791f5edb7`
- 135 of 153 files in results/, figures/, records/, logs/ and work/ are byte-identical to a file in the frozen export.
- Files that differ are listed below. Records and logs keep growing after the export (every later Colab session adds
  a bootstrap line to `records/run_registry.csv` and `records/environment_log.txt`); the paper figures in
  `figures/architecture/` and `figures/paper_combined/` were drawn after the export from frozen data.
- files larger than 45 MB are stored gzip-compressed; `GZIP_ORIGINALS.sha256` holds the hash of their original content.

| file | status | counterpart in the export |
|---|---|---|
| `results/README.txt` | not in export |  |
| `figures/README.txt` | not in export |  |
| `figures/architecture/fig_architecture.pdf` | made after Step 11 by colab/paper_figures (from frozen data) |  |
| `figures/architecture/fig_architecture.png` | made after Step 11 by colab/paper_figures (from frozen data) |  |
| `figures/architecture/fig_architecture_facts.json` | made after Step 11 by colab/paper_figures (from frozen data) |  |
| `figures/paper_combined/fig3_lopo_and_curve_coverage.pdf` | made after Step 11 by colab/paper_figures (from frozen data) |  |
| `figures/paper_combined/fig3_lopo_and_curve_coverage.png` | made after Step 11 by colab/paper_figures (from frozen data) |  |
| `figures/paper_combined/fig4_recalibration_budget_Id_Cgg.pdf` | made after Step 11 by colab/paper_figures (from frozen data) |  |
| `figures/paper_combined/fig4_recalibration_budget_Id_Cgg.png` | made after Step 11 by colab/paper_figures (from frozen data) |  |
| `figures/paper_combined/fig6_recalibration_width.pdf` | made after Step 11 by colab/paper_figures (from frozen data) |  |
| `figures/paper_combined/fig6_recalibration_width.png` | made after Step 11 by colab/paper_figures (from frozen data) |  |
| `records/environment_log.txt` | CHANGED since the export (same path, different content) | `records/environment_log.txt` |
| `records/reports/step_11_20261024_064738.txt` | not in export |  |
| `records/run_registry.csv` | CHANGED since the export (same path, different content) | `records/run_registry.csv` |
| `records/step_checks.csv` | CHANGED since the export (same path, different content) | `records/step_checks.csv` |
| `records/step_status.json` | CHANGED since the export (same path, different content) | `records/step_status.json` |
| `logs/step11_export_20261024_064350.log` | CHANGED since the export (same path, different content) | `logs/step11_export_20261024_064350.log` |
| `work/main/dataset_flags.json` | not in export |  |

<details><summary>Byte-identical files and their path in the export</summary>

| file | path in the export |
|---|---|
| `results/Cgg/curve_checks.csv` | `work/main/results/y_logCgg/curve_checks.csv` |
| `results/Cgg/fig1_audit_cgs_artifact_data.csv` | `work/main/paper/y_logCgg/fig1_audit_cgs_artifact_data.csv` |
| `results/Cgg/fig2_coverage_by_method_data.csv` | `work/main/paper/y_logCgg/fig2_coverage_by_method_data.csv` |
| `results/Cgg/fig3_recalibration_budget_data.csv` | `work/main/paper/y_logCgg/fig3_recalibration_budget_data.csv` |
| `results/Cgg/fig4_lopo_coverage_by_pdk_data.csv` | `work/main/paper/y_logCgg/fig4_lopo_coverage_by_pdk_data.csv` |
| `results/Cgg/fig5_recalibration_width_data.csv` | `work/main/paper/y_logCgg/fig5_recalibration_width_data.csv` |
| `results/Cgg/fig6_curve_coverage_data.csv` | `work/main/paper/y_logCgg/fig6_curve_coverage_data.csv` |
| `results/Cgg/figure_audit.csv` | `work/main/paper/y_logCgg/figure_audit.csv` |
| `results/Cgg/results_long.csv` | `work/main/results/y_logCgg/results_long.csv` |
| `results/Cgg/table1_accuracy.csv` | `work/main/paper/y_logCgg/table1_accuracy.csv` |
| `results/Cgg/table1b_curve_checks.csv` | `work/main/paper/y_logCgg/table1b_curve_checks.csv` |
| `results/Cgg/table2_coverage_alpha0.10.csv` | `work/main/paper/y_logCgg/table2_coverage_alpha0.10.csv` |
| `results/Cgg/table3_lopo_coverage_by_pdk.csv` | `work/main/paper/y_logCgg/table3_lopo_coverage_by_pdk.csv` |
| `results/Cgg/table4_lopo_paired_tests.csv` | `work/main/paper/y_logCgg/table4_lopo_paired_tests.csv` |
| `results/Id/curve_checks.csv` | `work/main/results/y_logId/curve_checks.csv` |
| `results/Id/fig1_audit_cgs_artifact_data.csv` | `work/main/paper/y_logCgg/fig1_audit_cgs_artifact_data.csv` |
| `results/Id/fig2_coverage_by_method_data.csv` | `work/main/paper/y_logId/fig2_coverage_by_method_data.csv` |
| `results/Id/fig3_recalibration_budget_data.csv` | `work/main/paper/y_logId/fig3_recalibration_budget_data.csv` |
| `results/Id/fig4_lopo_coverage_by_pdk_data.csv` | `work/main/paper/y_logId/fig4_lopo_coverage_by_pdk_data.csv` |
| `results/Id/fig5_recalibration_width_data.csv` | `work/main/paper/y_logId/fig5_recalibration_width_data.csv` |
| `results/Id/fig6_curve_coverage_data.csv` | `work/main/paper/y_logId/fig6_curve_coverage_data.csv` |
| `results/Id/figure_audit.csv` | `work/main/paper/y_logCgg/figure_audit.csv` |
| `results/Id/hypotheses_results.txt` | `records/hypotheses_results.txt` |
| `results/Id/results_long.csv` | `work/main/results/y_logId/results_long.csv` |
| `results/Id/table1_accuracy.csv` | `work/main/paper/y_logId/table1_accuracy.csv` |
| `results/Id/table1b_curve_checks.csv` | `work/main/paper/y_logId/table1b_curve_checks.csv` |
| `results/Id/table2_coverage_alpha0.10.csv` | `work/main/paper/y_logId/table2_coverage_alpha0.10.csv` |
| `results/Id/table3_lopo_coverage_by_pdk.csv` | `work/main/paper/y_logId/table3_lopo_coverage_by_pdk.csv` |
| `results/Id/table4_lopo_paired_tests.csv` | `work/main/paper/y_logId/table4_lopo_paired_tests.csv` |
| `results/sensitivity/sens_bsim4_Id_results_long.csv` | `work/sens_bsim4/results/y_logId/results_long.csv` |
| `results/sensitivity/sens_cal10_Id_results_long.csv` | `work/sens_cal10/results/y_logId/results_long.csv` |
| `results/sensitivity/sens_coverage_level.csv` | `work/main/paper/sensitivity/sens_coverage_level.csv` |
| `results/sensitivity/sens_ensemble_and_calibration_size.csv` | `work/main/paper/sensitivity/sens_ensemble_and_calibration_size.csv` |
| `results/sensitivity/sens_model_family_bsim4.csv` | `work/main/paper/sensitivity/sens_model_family_bsim4.csv` |
| `results/summary/FINAL_SUMMARY.md` | `records/FINAL_SUMMARY.md` |
| `figures/Cgg/fig1_audit_cgs_artifact.pdf` | `work/main/paper/y_logCgg/fig1_audit_cgs_artifact.pdf` |
| `figures/Cgg/fig1_audit_cgs_artifact.png` | `work/main/paper/y_logCgg/fig1_audit_cgs_artifact.png` |
| `figures/Cgg/fig2_coverage_by_method.pdf` | `work/main/paper/y_logCgg/fig2_coverage_by_method.pdf` |
| `figures/Cgg/fig2_coverage_by_method.png` | `work/main/paper/y_logCgg/fig2_coverage_by_method.png` |
| `figures/Cgg/fig3_recalibration_budget.pdf` | `work/main/paper/y_logCgg/fig3_recalibration_budget.pdf` |
| `figures/Cgg/fig3_recalibration_budget.png` | `work/main/paper/y_logCgg/fig3_recalibration_budget.png` |
| `figures/Cgg/fig4_lopo_coverage_by_pdk.pdf` | `work/main/paper/y_logCgg/fig4_lopo_coverage_by_pdk.pdf` |
| `figures/Cgg/fig4_lopo_coverage_by_pdk.png` | `work/main/paper/y_logCgg/fig4_lopo_coverage_by_pdk.png` |
| `figures/Cgg/fig5_recalibration_width.pdf` | `work/main/paper/y_logCgg/fig5_recalibration_width.pdf` |
| `figures/Cgg/fig5_recalibration_width.png` | `work/main/paper/y_logCgg/fig5_recalibration_width.png` |
| `figures/Cgg/fig6_curve_coverage.pdf` | `work/main/paper/y_logCgg/fig6_curve_coverage.pdf` |
| `figures/Cgg/fig6_curve_coverage.png` | `work/main/paper/y_logCgg/fig6_curve_coverage.png` |
| `figures/Id/fig1_audit_cgs_artifact.pdf` | `work/main/paper/y_logId/fig1_audit_cgs_artifact.pdf` |
| `figures/Id/fig1_audit_cgs_artifact.png` | `work/main/paper/y_logCgg/fig1_audit_cgs_artifact.png` |
| `figures/Id/fig2_coverage_by_method.pdf` | `work/main/paper/y_logId/fig2_coverage_by_method.pdf` |
| `figures/Id/fig2_coverage_by_method.png` | `work/main/paper/y_logId/fig2_coverage_by_method.png` |
| `figures/Id/fig3_recalibration_budget.pdf` | `work/main/paper/y_logId/fig3_recalibration_budget.pdf` |
| `figures/Id/fig3_recalibration_budget.png` | `work/main/paper/y_logId/fig3_recalibration_budget.png` |
| `figures/Id/fig4_lopo_coverage_by_pdk.pdf` | `work/main/paper/y_logId/fig4_lopo_coverage_by_pdk.pdf` |
| `figures/Id/fig4_lopo_coverage_by_pdk.png` | `work/main/paper/y_logId/fig4_lopo_coverage_by_pdk.png` |
| `figures/Id/fig5_recalibration_width.pdf` | `work/main/paper/y_logId/fig5_recalibration_width.pdf` |
| `figures/Id/fig5_recalibration_width.png` | `work/main/paper/y_logId/fig5_recalibration_width.png` |
| `figures/Id/fig6_curve_coverage.pdf` | `work/main/paper/y_logId/fig6_curve_coverage.pdf` |
| `figures/Id/fig6_curve_coverage.png` | `work/main/paper/y_logId/fig6_curve_coverage.png` |
| `records/AMENDMENTS.md` | `records/AMENDMENTS.md` |
| `records/FINAL_SUMMARY.md` | `records/FINAL_SUMMARY.md` |
| `records/errors.log` | `records/errors.log` |
| `records/fingerprints.json` | `records/fingerprints.json` |
| `records/hypotheses_results.txt` | `records/hypotheses_results.txt` |
| `records/installed_versions.csv` | `records/installed_versions.csv` |
| `records/mesd_commit.txt` | `records/mesd_commit.txt` |
| `records/reports/step_10.1_20261023_133539.txt` | `records/reports/step_10.1_20261023_133539.txt` |
| `records/reports/step_10.2_20261023_183946.txt` | `records/reports/step_10.2_20261023_183946.txt` |
| `records/reports/step_10.3_20261023_185708.txt` | `records/reports/step_10.3_20261023_185708.txt` |
| `records/reports/step_10.4_20261023_195507.txt` | `records/reports/step_10.4_20261023_195507.txt` |
| `records/reports/step_10.4_20261023_212240.txt` | `records/reports/step_10.4_20261023_212240.txt` |
| `records/reports/step_10.5_20261024_063602.txt` | `records/reports/step_10.5_20261024_063602.txt` |
| `records/reports/step_10.6_20261024_063844.txt` | `records/reports/step_10.6_20261024_063844.txt` |
| `records/reports/step_10.6_20261024_064311.txt` | `records/reports/step_10.6_20261024_064311.txt` |
| `records/reports/step_1_20261022_185258.txt` | `records/reports/step_1_20261022_185258.txt` |
| `records/reports/step_1_20261022_202231.txt` | `records/reports/step_1_20261022_202231.txt` |
| `records/reports/step_2_20261022_185502.txt` | `records/reports/step_2_20261022_185502.txt` |
| `records/reports/step_2_20261022_202330.txt` | `records/reports/step_2_20261022_202330.txt` |
| `records/reports/step_3_20261022_190151.txt` | `records/reports/step_3_20261022_190151.txt` |
| `records/reports/step_3_20261022_202426.txt` | `records/reports/step_3_20261022_202426.txt` |
| `records/reports/step_4_20261022_202540.txt` | `records/reports/step_4_20261022_202540.txt` |
| `records/reports/step_5_20261023_031730.txt` | `records/reports/step_5_20261023_031730.txt` |
| `records/reports/step_6_20261023_035418.txt` | `records/reports/step_6_20261023_035418.txt` |
| `records/reports/step_7_20261023_042446.txt` | `records/reports/step_7_20261023_042446.txt` |
| `records/reports/step_7_20261023_123557.txt` | `records/reports/step_7_20261023_123557.txt` |
| `records/reports/step_8_20261023_045402.txt` | `records/reports/step_8_20261023_045402.txt` |
| `records/reports/step_8_20261023_052108.txt` | `records/reports/step_8_20261023_052108.txt` |
| `records/reports/step_8_20261023_131120.txt` | `records/reports/step_8_20261023_131120.txt` |
| `records/reports/step_9.4_20261023_050652.txt` | `records/reports/step_9.4_20261023_050652.txt` |
| `records/reports/step_9.5_20261023_122414.txt` | `records/reports/step_9.5_20261023_122414.txt` |
| `records/reports/step_9.6_20261023_123829.txt` | `records/reports/step_9.6_20261023_123829.txt` |
| `records/reports/step_9.7_20261023_125935.txt` | `records/reports/step_9.7_20261023_125935.txt` |
| `records/reports/step_9.8_20261023_130309.txt` | `records/reports/step_9.8_20261023_130309.txt` |
| `records/reports/step_9.8_20261023_131235.txt` | `records/reports/step_9.8_20261023_131235.txt` |
| `logs/01_build_audit_20261022_181322.log` | `logs/01_build_audit_20261022_181322.log` |
| `logs/step10_1_sens_ens3_20261023_131458.log` | `logs/step10_1_sens_ens3_20261023_131458.log` |
| `logs/step10_2_calfrac_splits_20261023_134444.log` | `logs/step10_2_calfrac_splits_20261023_134444.log` |
| `logs/step10_2_calfrac_train_20261023_134516.log` | `logs/step10_2_calfrac_train_20261023_134516.log` |
| `logs/step10_3_calfrac_eval_20261023_184544.log` | `logs/step10_3_calfrac_eval_20261023_184544.log` |
| `logs/step10_4_bsim4_splits_20261023_185907.log` | `logs/step10_4_bsim4_splits_20261023_185907.log` |
| `logs/step10_4_bsim4_splits_20261023_200328.log` | `logs/step10_4_bsim4_splits_20261023_200328.log` |
| `logs/step10_4_bsim4_train_20261023_185932.log` | `logs/step10_4_bsim4_train_20261023_185932.log` |
| `logs/step10_4_bsim4_train_20261023_200354.log` | `logs/step10_4_bsim4_train_20261023_200354.log` |
| `logs/step10_5_bsim4_eval_20261024_062941.log` | `logs/step10_5_bsim4_eval_20261024_062941.log` |
| `logs/step10_6_sens_summary_20261024_063841.log` | `logs/step10_6_sens_summary_20261024_063841.log` |
| `logs/step10_6_sens_summary_20261024_064311.log` | `logs/step10_6_sens_summary_20261024_064311.log` |
| `logs/step1_build_audit_20261022_185115.log` | `logs/step1_build_audit_20261022_185115.log` |
| `logs/step2_features_splits_20261022_185353.log` | `logs/step2_features_splits_20261022_185353.log` |
| `logs/step3_tune_20261022_185523.log` | `logs/step3_tune_20261022_185523.log` |
| `logs/step4_smoke_eval_20261022_202502.log` | `logs/step4_smoke_eval_20261022_202502.log` |
| `logs/step4_smoke_figures_20261022_202528.log` | `logs/step4_smoke_figures_20261022_202528.log` |
| `logs/step4_smoke_train_20261022_202443.log` | `logs/step4_smoke_train_20261022_202443.log` |
| `logs/step5_train_Id_20261022_202649.log` | `logs/step5_train_Id_20261022_202649.log` |
| `logs/step7_eval_Id_20261023_035730.log` | `logs/step7_eval_Id_20261023_035730.log` |
| `logs/step7_eval_Id_20261023_035847.log` | `logs/step7_eval_Id_20261023_035847.log` |
| `logs/step7_eval_Id_20261023_123526.log` | `logs/step7_eval_Id_20261023_123526.log` |
| `logs/step8_figures_Id_20261023_045340.log` | `logs/step8_figures_Id_20261023_045340.log` |
| `logs/step8_figures_Id_20261023_052045.log` | `logs/step8_figures_Id_20261023_052045.log` |
| `logs/step8_figures_Id_20261023_131101.log` | `logs/step8_figures_Id_20261023_131101.log` |
| `logs/step9_4_smoke_eval_20261023_050617.log` | `logs/step9_4_smoke_eval_20261023_050617.log` |
| `logs/step9_4_smoke_figures_20261023_050637.log` | `logs/step9_4_smoke_figures_20261023_050637.log` |
| `logs/step9_4_smoke_train_20261023_050508.log` | `logs/step9_4_smoke_train_20261023_050508.log` |
| `logs/step9_4_smoke_train_20261023_050555.log` | `logs/step9_4_smoke_train_20261023_050555.log` |
| `logs/step9_5_train_Cgg_20261023_052239.log` | `logs/step9_5_train_Cgg_20261023_052239.log` |
| `logs/step9_7_eval_Cgg_20261023_124145.log` | `logs/step9_7_eval_Cgg_20261023_124145.log` |
| `logs/step9_8_figures_Cgg_20261023_130253.log` | `logs/step9_8_figures_Cgg_20261023_130253.log` |
| `logs/step9_8_figures_Cgg_20261023_131217.log` | `logs/step9_8_figures_Cgg_20261023_131217.log` |
| `work/main/tuning.json` | `work/main/tuning.json` |
| `work/main/tuning_log.csv` | `work/main/tuning_log.csv` |
| `work/main/anchors.csv` | `work/main/anchors.csv` |
| `work/main/audit_per_file.csv` | `work/main/audit_per_file.csv` |
| `work/main/preds/y_logCgg/train_log.jsonl` | `work/main/preds/y_logCgg/train_log.jsonl` |
| `work/main/preds/y_logId/train_log.jsonl` | `work/main/preds/y_logId/train_log.jsonl` |
| `work/sens_cal10/preds/y_logId/train_log.jsonl` | `work/sens_cal10/preds/y_logId/train_log.jsonl` |
| `work/sens_bsim4/preds/y_logId/train_log.jsonl` | `work/sens_bsim4/preds/y_logId/train_log.jsonl` |

</details>

