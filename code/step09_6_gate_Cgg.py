# Step 9.6 - accuracy gate on S0 for log10(Cgg) (CPU is enough)
exec(open(f'{BASE}/code/mesd_common.py').read())
require('3', '9.5')
check_gate('y_logCgg', '9.6', 'Step 9.7')
