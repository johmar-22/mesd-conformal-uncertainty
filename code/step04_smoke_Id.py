# Step 4 - smoke test of the whole pipeline (3% of curves, 2 epochs) in work/smoke; never used in the paper
exec(open(f'{BASE}/code/mesd_common.py').read())
require('2')
run_smoke('y_logId', 'smoke', 'step4')
check_smoke('y_logId', '4', 'smoke', 'Step 5')
