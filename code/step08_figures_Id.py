# Step 8 - tables, figures and the pre-specified hypothesis decisions, log10(Id) (CPU)
exec(open(f'{BASE}/code/mesd_common.py').read())
require('7')
run_step('step8_figures_Id', 'mesd_05_figures_tables.py', env={'MESD_TARGET': 'y_logId'}, key='figs:y_logId',
         upstream=['eval:main:y_logId', 'build'], outputs=['paper/y_logId/table2_coverage_alpha0.10.csv', 'paper/y_logId/fig2_coverage_by_method.png'])
show_pngs(f'{WORKROOT}/main/paper/y_logId')
check_figs('y_logId', '8', 'Step 9.4 (Cgg) or Step 10.1')
