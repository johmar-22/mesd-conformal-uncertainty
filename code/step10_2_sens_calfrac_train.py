# Step 10.2 - sensitivity: calibration fraction 0.10, S0 and S4 (29 runs) in work/sens_cal10 (GPU; checkpointed per run)
exec(open(f'{BASE}/code/mesd_common.py').read())
require('3', '6'); require_gpu('Step 10.2')
run_step('step10_2_calfrac_splits', 'mesd_02_features_and_splits.py', work='sens_cal10', env={'MESD_CAL_FRAC': 0.10},
         key='splits:sens_cal10', upstream=['build'], outputs=['model_table.parquet', 'splits.parquet', 'anchors.csv'])
run_step('step10_2_calfrac_train', 'mesd_03_train_models.py', work='sens_cal10', env={'MESD_TARGET': 'y_logId', 'MESD_SCENARIOS': 'S0_random,S4_LOPO'},
         key='train:sens_cal10:y_logId', upstream=['splits:sens_cal10', 'tune'])
check_train('y_logId', '10.2', work='sens_cal10', scen=['S0_random', 'S4_LOPO'], next_step='Step 10.3',
            title='sensitivity training: calibration fraction 0.10 (S0, S4)', log_prefix='step10_2_calfrac_train')
