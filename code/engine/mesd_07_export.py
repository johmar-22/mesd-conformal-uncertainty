# =====================================================================
# MESD project - engine 07: export a frozen, citable record of the study (CPU)
# ENGINE script (executed by code/mesd_common.py run_step; never run it directly in Colab)
# Output: <root>/exports/MESD_results_<codeversion>_<timestamp>.zip
#         <root>/records/FINAL_SUMMARY.md (key numbers for the paper, regenerated each time)
# The zip holds results, paper tables/figures, records (registry, errors, amendments,
# environment), logs, tuning and audit files, training logs, plus SHA-256 checksums.
# Large intermediate files (parquet tables, prediction files) are NOT copied: they stay in
# work/ and can be regenerated from the pinned MESD commit with the same code version.
# The smoke-test folder is excluded on purpose (its numbers are meaningless).
# =====================================================================
import os, glob, hashlib, zipfile, datetime, json
import numpy as np
import pandas as pd

ROOT = os.environ['MESD_ROOT']
WORK = os.environ.get('MESD_WORK', os.path.join(ROOT, 'work', 'main'))
REC = os.path.join(ROOT, 'records')
ver = open(os.path.join(ROOT, 'code', 'VERSION.txt')).read().strip()
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
os.makedirs(os.path.join(ROOT, 'exports'), exist_ok=True)
zpath = os.path.join(ROOT, 'exports', f'MESD_results_{ver}_{ts}.zip')

def md(t):
    try:
        return t.to_markdown()
    except ImportError:            # 'tabulate' missing
        return '```\n' + t.to_string() + '\n```'

# ---------------- FINAL_SUMMARY.md ----------------
L = [f'# MESD study: final summary', '', f'- generated: {ts}', f'- code version: {ver}']
cm = os.path.join(REC, 'mesd_commit.txt')
L.append(f'- MESD commit: {open(cm).read().strip() if os.path.exists(cm) else "not recorded"}')
tj = os.path.join(WORK, 'tuning.json')
if os.path.exists(tj):
    L.append(f'- tuned hyperparameters: {json.load(open(tj))}')
if os.path.exists(tj) and json.load(open(tj)).get('debug'):
    L.append('- WARNING: tuning.json comes from a DEBUG run; these numbers are NOT valid for the paper')
for tgt in ['y_logId', 'y_logCgg']:
    pdir = os.path.join(WORK, 'preds', tgt)
    n = len(glob.glob(os.path.join(pdir, '*.parquet')))
    L.append(f'- prediction files {tgt}: {n} of 44 expected' + ('' if n >= 44 else '  <- WARNING: incomplete, results not final'))
for tgt in ['y_logId', 'y_logCgg']:
    rp = os.path.join(WORK, 'results', tgt, 'results_long.csv')
    if not os.path.exists(rp):
        continue
    r = pd.read_csv(rp)
    L += ['', f'## {tgt}: accuracy (mean over seeds / folds)', '']
    acc = r[r.method == 'accuracy'].groupby('scenario')[['mae_dec', 'medrel_above', 'auroc_sigma_err']].mean().round(3)
    L.append(md(acc))
    a = r[(r.alpha == 0.10) & ~r.method.str.contains('Recal') & (r.method != 'accuracy')]
    for met in ['coverage', 'curve_coverage', 'width_median']:
        t = a.groupby(['scenario', 'method'])[met].mean().unstack('method').round(3)
        L += ['', f'## {tgt}: {met} at alpha = 0.10 (nominal coverage 0.90)', '']
        L.append(md(t))
summ = '\n'.join(L) + '\n'
open(os.path.join(REC, 'FINAL_SUMMARY.md'), 'w').write(summ)
print(summ)

# ---------------- collect files ----------------
pats = ['work/main/results/**/*', 'work/main/paper/**/*', 'work/sens_cal10/results/**/*', 'work/sens_bsim4/results/**/*',
        'work/main/audit_per_file.csv', 'work/main/anchors.csv', 'work/main/tuning.json',
        'work/main/tuning_log.csv', 'work/main/preds/*/train_log.jsonl',
        'work/sens_cal10/preds/*/train_log.jsonl', 'work/sens_bsim4/preds/*/train_log.jsonl',
        'records/**/*', 'logs/**/*', 'code/VERSION.txt', 'code/MANIFEST.sha256', 'docs/**/*']
files = sorted({f for p in pats for f in glob.glob(os.path.join(ROOT, p), recursive=True) if os.path.isfile(f)})
sums = []
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in files:
        rel = os.path.relpath(f, ROOT)
        z.write(f, rel)
        sums.append(f'{hashlib.sha256(open(f, "rb").read()).hexdigest()}  {rel}')
    z.writestr('EXPORT_SHA256.txt', '\n'.join(sums) + '\n')
print(f'exported {len(files)} files -> {zpath} ({os.path.getsize(zpath) / 2**20:.1f} MB)')
