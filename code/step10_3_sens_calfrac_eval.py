# Step 10.3 - sensitivity: evaluation with calibration fraction 0.10 (CPU)
exec(open(f'{BASE}/code/mesd_common.py').read())
require('10.2')
run_step('step10_3_calfrac_eval', 'mesd_04_conformal_eval.py', work='sens_cal10', env={'MESD_TARGET': 'y_logId'},
         key='eval:sens_cal10:y_logId', upstream=['train:sens_cal10:y_logId'])
check_eval('y_logId', '10.3', work='sens_cal10', next_step='Step 10.4', full=False, title='sensitivity evaluation: calibration fraction 0.10')
