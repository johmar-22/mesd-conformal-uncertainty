# Step 10.4 - sensitivity: model-family control, S4 with only the 5 BSIM4 PDKs (N40A, N45A, N45B, N55A, N180B), 15 runs (GPU; checkpointed)
# v9: N45A added. It is BSIM4.0 according to the MESD v1.0.0 file header (MESD2.0 dropped that field, so v1-v8 had it as 'unknown').
exec(open(f'{BASE}/code/mesd_common.py').read())
require('3', '6'); require_gpu('Step 10.4')
run_step('step10_4_bsim4_splits', 'mesd_02_features_and_splits.py', work='sens_bsim4', env={'MESD_PDK_KEEP': 'N40A,N45A,N45B,N55A,N180B'},
         key='splits:sens_bsim4', upstream=['build'], outputs=['model_table.parquet', 'splits.parquet', 'anchors.csv'])
run_step('step10_4_bsim4_train', 'mesd_03_train_models.py', work='sens_bsim4', env={'MESD_TARGET': 'y_logId', 'MESD_SCENARIOS': 'S4_LOPO'},
         key='train:sens_bsim4:y_logId', upstream=['splits:sens_bsim4', 'tune'])
check_train('y_logId', '10.4', work='sens_bsim4', scen=['S4_LOPO'], next_step='Step 10.5',
            title='sensitivity training: BSIM4 PDKs only (S4)', log_prefix='step10_4_bsim4_train')
