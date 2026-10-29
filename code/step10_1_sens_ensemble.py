# Step 10.1 - sensitivity: ensemble of 3 instead of 5 (members 0-2 are exactly the networks a 3-member run would train) (CPU)
exec(open(f'{BASE}/code/mesd_common.py').read())
require('7')
run_step('step10_1_sens_ens3', 'mesd_04_conformal_eval.py', env={'MESD_TARGET': 'y_logId', 'MESD_N_ENS_USE': 3, 'MESD_RES_TAG': '_ens3'},
         key='eval:main:y_logId_ens3', upstream=['train:main:y_logId'])
check_eval('y_logId', '10.1', tag='_ens3', next_step='Step 10.2', title='sensitivity: ensemble size 3 (y_logId)')
