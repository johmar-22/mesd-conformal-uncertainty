# Step 1 - clone MESD at the pinned commit, build the table, run the audit (CPU, High-RAM recommended)
exec(open(f'{BASE}/code/mesd_common.py').read())
run_step('step1_build_audit', 'mesd_01_build_and_audit.py', key='build',
         outputs=['mesd_long.parquet', 'audit_per_file.csv', 'dataset_flags.json'])
check_step1()
