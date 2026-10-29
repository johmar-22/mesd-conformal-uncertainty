# Step 6 - accuracy gate (go / no-go) on the S0 random split, log10(Id) (CPU is enough)
exec(open(f'{BASE}/code/mesd_common.py').read())
require('3', '5')
check_gate('y_logId', '6', 'Step 7')
