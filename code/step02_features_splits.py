# Step 2 - features, device anchors and the shift splits (CPU, High-RAM recommended)
exec(open(f'{BASE}/code/mesd_common.py').read())
require('1')
run_step('step2_features_splits', 'mesd_02_features_and_splits.py', key='splits:main', upstream=['build'],
         outputs=['model_table.parquet', 'splits.parquet', 'anchors.csv'])
check_step2()
