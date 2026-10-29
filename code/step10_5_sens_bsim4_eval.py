# Step 10.5 - sensitivity: evaluation of the BSIM4-only leave-one-PDK-out runs (CPU)
exec(open(f'{BASE}/code/mesd_common.py').read())
require('10.4')
# v9 guard: the corrected control holds 5 BSIM4 PDKs (N45A added); stop if Step 10.4 has not been re-run
import pandas as _pd
_folds = set(_pd.read_parquet(f'{WORKROOT}/sens_bsim4/splits.parquet', columns=['fold']).fold.astype(str))
if 'N45A' not in _folds:
    raise RuntimeError('the BSIM4 control on Drive is the old 4-PDK version (no N45A). Re-run Step 10.4 '
                       '(GPU, 15 runs) with code v9 first, then this cell.')
print('BSIM4 control folds:', sorted(f for f in _folds if f != 'all'))
run_step('step10_5_bsim4_eval', 'mesd_04_conformal_eval.py', work='sens_bsim4', env={'MESD_TARGET': 'y_logId'},
         key='eval:sens_bsim4:y_logId', upstream=['train:sens_bsim4:y_logId'])
check_eval('y_logId', '10.5', work='sens_bsim4', next_step='Step 10.6', full=False, title='sensitivity evaluation: BSIM4 PDKs only')
