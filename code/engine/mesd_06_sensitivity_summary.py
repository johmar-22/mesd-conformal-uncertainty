# =====================================================================
# MESD project - engine 06: sensitivity summary (plan Step 10)  (CPU)
# ENGINE script (executed by code/mesd_common.py run_step; never run it directly in Colab)
# The four sensitivity analyses of the execution plan, Step 10:
#   1. Ensemble size     : 3 instead of 5 members, S0 and S4        (results/y_logId_ens3,  Step 10.1)
#   2. Calibration size  : CAL_FRAC 0.10 instead of 0.20, S0 and S4  (work/sens_cal10,      Steps 10.2-10.3)
#   3. Coverage level    : alpha = 0.20 and 0.05 (already in results_long.csv of Step 7)
#   4. Model family      : S4 with only the BSIM4 PDKs N40A, N45A, N45B, N55A, N180B (work/sens_bsim4, Steps 10.4-10.5)
# Output: <work>/paper/sensitivity/*.csv. Descriptive only: no hypothesis tests (plan: "do not let
# them change the main conclusions retroactively").
# =====================================================================
import os
import numpy as np
import pandas as pd

WORK = os.environ.get('MESD_WORK', os.path.abspath('./MESD_project'))
ROOT = os.environ.get('MESD_ROOT', os.path.dirname(os.path.dirname(WORK)))
BASE = WORK
OUT = os.path.join(BASE, 'paper', 'sensitivity'); os.makedirs(OUT, exist_ok=True)
pd.set_option('display.width', 250); pd.set_option('display.max_columns', None); pd.set_option('display.max_rows', 500)
KEY = ['SCP-ens', 'NCP', 'CQR', 'SCP-curve', 'Mondrian-region']
MET = ['coverage', 'curve_coverage', 'width_median']
BSIM4 = ['N40A', 'N45A', 'N45B', 'N55A', 'N180B']   # v9: N45A is BSIM4.0 (MESD v1.0.0 header)


def load(path, scen=None, folds=None):
    if not os.path.exists(path):
        return None
    r = pd.read_csv(path)
    r = r[r.method.isin(KEY)]
    if scen:
        r = r[r.scenario.isin(scen)]
    if folds is not None:
        r = r[r.fold.astype(str).isin(folds)]
    return r


def summ(r, label, alpha=0.10):
    g = r[r.alpha == alpha].groupby(['scenario', 'method'])[MET].mean()
    g.columns = [f'{label}:{c}' for c in g.columns]
    return g


main_path = os.path.join(BASE, 'results', 'y_logId', 'results_long.csv')
assert os.path.exists(main_path), 'run Step 7 (evaluation of y_logId) first'
main = load(main_path)

# ---- 1 + 2: ensemble size and calibration size (S0 and S4, as in the plan) ----
S04 = ['S0_random', 'S4_LOPO']
parts = [summ(main[main.scenario.isin(S04)], 'main')]
e3 = load(os.path.join(BASE, 'results', 'y_logId_ens3', 'results_long.csv'), S04)
c10 = load(os.path.join(ROOT, 'work', 'sens_cal10', 'results', 'y_logId', 'results_long.csv'), S04)
for r, lab in [(e3, 'ens3'), (c10, 'cal10')]:
    if r is None:
        print(f'[{lab}] results not found -> skipped')
    else:
        parts.append(summ(r, lab))
t12 = pd.concat(parts, axis=1).round(3)
for lab in ['ens3', 'cal10']:
    if f'{lab}:coverage' in t12:
        t12[f'delta_cov_{lab}'] = (t12[f'{lab}:coverage'] - t12['main:coverage']).round(3)
        t12[f'delta_curvecov_{lab}'] = (t12[f'{lab}:curve_coverage'] - t12['main:curve_coverage']).round(3)
t12.to_csv(os.path.join(OUT, 'sens_ensemble_and_calibration_size.csv'))
print('\n1-2. ENSEMBLE SIZE (3 vs 5) AND CALIBRATION FRACTION (0.10 vs 0.20), alpha = 0.10, S0 and S4:')
print(t12)

# ---- 3: coverage level (alpha 0.20 / 0.10 / 0.05): coverage and method ranking by |coverage - nominal| ----
lv = main.groupby(['scenario', 'method', 'alpha'])['coverage'].mean().reset_index()
lv['nominal'] = 1 - lv.alpha
lv['gap'] = (lv.coverage - lv.nominal).abs()
lv['rank'] = lv.groupby(['scenario', 'alpha'])['gap'].rank(method='min')
t3 = lv.pivot_table(index=['scenario', 'method'], columns='alpha', values=['coverage', 'rank']).round(3)
t3.to_csv(os.path.join(OUT, 'sens_coverage_level.csv'))
print('\n3. COVERAGE LEVEL: coverage and rank (1 = closest to nominal) at alpha = 0.20, 0.10, 0.05:')
print(t3)

# ---- 4: model-family control: S4 trained/evaluated on BSIM4 PDKs only vs main S4 on the same folds ----
b4 = load(os.path.join(ROOT, 'work', 'sens_bsim4', 'results', 'y_logId', 'results_long.csv'), ['S4_LOPO'])
m4 = main[(main.scenario == 'S4_LOPO') & main.fold.astype(str).isin(BSIM4)]
if b4 is None:
    print('\n4. MODEL FAMILY: results not found -> skipped')
else:
    a = m4[m4.alpha == 0.10].groupby(['fold', 'method'])['coverage'].mean().unstack('method')
    b = b4[b4.alpha == 0.10].groupby(['fold', 'method'])['coverage'].mean().unstack('method')
    a.loc['mean'] = a.mean(); b.loc['mean'] = b.mean()
    # v10: labels state the number of TRAINING PDKs per fold (one PDK is always held out)
    t4 = pd.concat({'main (7 training PDKs per fold)': a, f'BSIM4 only ({len(BSIM4) - 1} training PDKs per fold)': b}, axis=1).round(3)
    t4.to_csv(os.path.join(OUT, 'sens_model_family_bsim4.csv'))
    print('\n4. MODEL FAMILY CONTROL: S4 coverage on the BSIM4 folds (alpha = 0.10):')
    print(t4)
print('\nsaved to', OUT, sorted(os.listdir(OUT)))
