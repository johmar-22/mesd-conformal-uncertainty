# MESD study: final summary

- generated: 20261024_064350
- code version: v10
- MESD commit: 5dcc2236ac5b5eeb6228503f544053c2a359b636
- tuned hyperparameters: {'epochs': 60, 'lr': 0.005, 'norm_wl': True, 'val_mae_dec': 0.007417269982397556, 'val_medrel_above': 0.008622229099273682, 'selected_on': 'S0_random seed 0, inner validation (15% of train curves)', 'debug': False}
- prediction files y_logId: 44 of 44 expected
- prediction files y_logCgg: 44 of 44 expected

## y_logId: accuracy (mean over seeds / folds)

| scenario    |   mae_dec |   medrel_above |   auroc_sigma_err |
|:------------|----------:|---------------:|------------------:|
| S0_random   |     0.028 |          0.035 |             0.962 |
| S1_Lextreme |     0.125 |          0.098 |             0.883 |
| S2_T125     |     0.058 |          0.051 |             0.909 |
| S3_ff       |     0.471 |          0.584 |             0.699 |
| S4_LOPO     |     0.467 |          0.488 |             0.764 |

## y_logId: coverage at alpha = 0.10 (nominal coverage 0.90)

| scenario    |   CQR |   Ens-Gauss |   Mondrian-region |   NCP |   SCP-curve |   SCP-ens |   SCP-single |   WCP |
|:------------|------:|------------:|------------------:|------:|------------:|----------:|-------------:|------:|
| S0_random   | 0.9   |       0.916 |             0.899 | 0.9   |       0.99  |     0.9   |        0.899 |   0.9 |
| S1_Lextreme | 0.409 |       0.725 |             0.58  | 0.724 |       0.904 |     0.611 |        0.63  |   1   |
| S2_T125     | 0.61  |       0.899 |             0.769 | 0.879 |       0.972 |     0.795 |        0.77  |   1   |
| S3_ff       | 0.035 |       0.597 |             0.099 | 0.493 |       0.701 |     0.132 |        0.202 |   1   |
| S4_LOPO     | 0.037 |       0.671 |             0.089 | 0.628 |       0.825 |     0.108 |        0.116 |   1   |

## y_logId: curve_coverage at alpha = 0.10 (nominal coverage 0.90)

| scenario    |   CQR |   Ens-Gauss |   Mondrian-region |   NCP |   SCP-curve |   SCP-ens |   SCP-single |   WCP |
|:------------|------:|------------:|------------------:|------:|------------:|----------:|-------------:|------:|
| S0_random   | 0.358 |       0.531 |             0.507 | 0.409 |       0.899 |     0.427 |        0.399 | 0.428 |
| S1_Lextreme | 0.022 |       0.275 |             0.143 | 0.268 |       0.651 |     0.118 |        0.092 | 1     |
| S2_T125     | 0.056 |       0.493 |             0.249 | 0.425 |       0.816 |     0.241 |        0.175 | 1     |
| S3_ff       | 0     |       0.159 |             0     | 0.081 |       0.308 |     0     |        0.002 | 1     |
| S4_LOPO     | 0     |       0.297 |             0     | 0.265 |       0.541 |     0     |        0     | 1     |

## y_logId: width_median at alpha = 0.10 (nominal coverage 0.90)

| scenario    |   CQR |   Ens-Gauss |   Mondrian-region |   NCP |   SCP-curve |   SCP-ens |   SCP-single |     WCP |
|:------------|------:|------------:|------------------:|------:|------------:|----------:|-------------:|--------:|
| S0_random   | 0.012 |       0.101 |             0.09  | 0.098 |       0.202 |     0.123 |        0.157 |   0.123 |
| S1_Lextreme | 0.018 |       0.196 |             0.111 | 0.197 |       0.407 |     0.151 |        0.191 | inf     |
| S2_T125     | 0.015 |       0.154 |             0.089 | 0.142 |       0.291 |     0.124 |        0.146 | inf     |
| S3_ff       | 0.015 |       0.726 |             0.088 | 0.523 |       0.986 |     0.125 |        0.135 | inf     |
| S4_LOPO     | 0.033 |       0.867 |             0.074 | 0.799 |       1.56  |     0.103 |        0.137 | inf     |

## y_logCgg: accuracy (mean over seeds / folds)

| scenario    |   mae_dec |   medrel_above |   auroc_sigma_err |
|:------------|----------:|---------------:|------------------:|
| S0_random   |     0.013 |          0.02  |           nan     |
| S1_Lextreme |     0.023 |          0.032 |             0.733 |
| S2_T125     |     0.014 |          0.022 |           nan     |
| S3_ff       |     0.082 |          0.188 |             0.625 |
| S4_LOPO     |     0.193 |          0.399 |             0.625 |

## y_logCgg: coverage at alpha = 0.10 (nominal coverage 0.90)

| scenario    |   CQR |   Ens-Gauss |   Mondrian-region |   NCP |   SCP-curve |   SCP-ens |   SCP-single |   WCP |
|:------------|------:|------------:|------------------:|------:|------------:|----------:|-------------:|------:|
| S0_random   | 0.9   |       0.821 |             0.899 | 0.9   |       0.991 |     0.899 |        0.899 |   0.9 |
| S1_Lextreme | 0.568 |       0.746 |             0.697 | 0.854 |       0.983 |     0.697 |        0.724 |   1   |
| S2_T125     | 0.81  |       0.846 |             0.87  | 0.921 |       0.994 |     0.869 |        0.848 |   1   |
| S3_ff       | 0.091 |       0.952 |             0.321 | 0.98  |       0.999 |     0.327 |        0.406 |   1   |
| S4_LOPO     | 0.041 |       0.524 |             0.08  | 0.622 |       0.834 |     0.081 |        0.103 |   1   |

## y_logCgg: curve_coverage at alpha = 0.10 (nominal coverage 0.90)

| scenario    |   CQR |   Ens-Gauss |   Mondrian-region |   NCP |   SCP-curve |   SCP-ens |   SCP-single |   WCP |
|:------------|------:|------------:|------------------:|------:|------------:|----------:|-------------:|------:|
| S0_random   | 0.359 |       0.236 |             0.428 | 0.396 |       0.9   |     0.394 |        0.39  | 0.397 |
| S1_Lextreme | 0.053 |       0.168 |             0.135 | 0.355 |       0.85  |     0.114 |        0.117 | 1     |
| S2_T125     | 0.178 |       0.301 |             0.38  | 0.513 |       0.93  |     0.35  |        0.279 | 1     |
| S3_ff       | 0     |       0.791 |             0.019 | 0.892 |       0.988 |     0.016 |        0.028 | 1     |
| S4_LOPO     | 0     |       0.233 |             0     | 0.336 |       0.668 |     0     |        0.001 | 1     |

## y_logCgg: width_median at alpha = 0.10 (nominal coverage 0.90)

| scenario    |   CQR |   Ens-Gauss |   Mondrian-region |   NCP |   SCP-curve |   SCP-ens |   SCP-single |     WCP |
|:------------|------:|------------:|------------------:|------:|------------:|----------:|-------------:|--------:|
| S0_random   | 0.006 |       0.041 |             0.051 | 0.054 |       0.124 |     0.057 |        0.06  |   0.058 |
| S1_Lextreme | 0.009 |       0.058 |             0.047 | 0.081 |       0.187 |     0.053 |        0.076 | inf     |
| S2_T125     | 0.007 |       0.05  |             0.049 | 0.066 |       0.153 |     0.053 |        0.065 | inf     |
| S3_ff       | 0.01  |       0.493 |             0.069 | 0.644 |       1.449 |     0.08  |        0.133 | inf     |
| S4_LOPO     | 0.016 |       0.433 |             0.04  | 0.55  |       1.191 |     0.044 |        0.063 | inf     |
