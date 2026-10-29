# Step 3 - hyperparameters chosen on inner-validation curves of S0 training data only; frozen once chosen (GPU)
exec(open(f'{BASE}/code/mesd_common.py').read())
require('2')
if ckpt_decide('tune', step_fp(['mesd_03a_tune_hyperparameters.py'], ['splits:main'], {'work': 'main'}), f'{WORKROOT}/main',
               ['tuning.json', 'tuning_log.csv']) == 'run':
    require_gpu('Step 3')
    run_step('step3_tune', 'mesd_03a_tune_hyperparameters.py', key='tune', upstream=['splits:main'], outputs=['tuning.json', 'tuning_log.csv'])
check_step3()
