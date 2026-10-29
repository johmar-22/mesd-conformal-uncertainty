# Step 9.8 - tables and figures, log10(Cgg) (CPU)
exec(open(f'{BASE}/code/mesd_common.py').read())
require('9.7')
run_step('step9_8_figures_Cgg', 'mesd_05_figures_tables.py', env={'MESD_TARGET': 'y_logCgg'}, key='figs:y_logCgg',
         upstream=['eval:main:y_logCgg', 'build'], outputs=['paper/y_logCgg/table2_coverage_alpha0.10.csv', 'paper/y_logCgg/fig2_coverage_by_method.png'])
show_pngs(f'{WORKROOT}/main/paper/y_logCgg')
check_figs('y_logCgg', '9.8', 'Step 10.1')
