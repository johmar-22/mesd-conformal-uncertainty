# =====================================================================
# MESD project - step CHECK LOGS (PASS / FAIL against the execution plan)
# Executed by the step cells after their work is done. Each check log:
#   * re-reads the step's OUTPUT FILES from Drive (not the screen);
#   * prints the key results;
#   * prints one line per check:  [PASS]/[FAIL]/[WARN]  what | expected | got | fix if it fails
#     The expected values are the ones written in the execution plan (Steps 1-11, sections 6-8);
#   * ends with "STEP n RESULT: PASS -> you can proceed to Step m" or "FAIL -> do not proceed";
#   * appends every check to records/step_checks.csv, the result to records/step_status.json,
#     and the whole log to records/reports/<step>_<time>.txt.
# Cells refuse to start when a prerequisite step has not PASSED (plan: "each step ends with a
# checkpoint; do not continue until it passes").
# =====================================================================
import os, json, glob, io, csv, contextlib, datetime
import numpy as np
import pandas as pd

pd.set_option('display.max_columns', None); pd.set_option('display.width', 250)
pd.set_option('display.max_rows', 500); pd.set_option('display.max_colwidth', 60)

PINNED = '5dcc2236ac5b5eeb6228503f544053c2a359b636'
SC = ['S0_random', 'S1_Lextreme', 'S2_T125', 'S3_ff', 'S4_LOPO']
PDKS = ['N180A', 'N180B', 'N350A', 'N40A', 'N45A', 'N45B', 'N55A', 'N90A']
BSIM4 = ['N40A', 'N45A', 'N45B', 'N55A', 'N180B']   # v9: N45A is BSIM4.0 (MESD v1.0.0 header)
MAIN_METHODS = ['SCP-single', 'SCP-ens', 'Ens-Gauss', 'NCP', 'CQR', 'Mondrian-region', 'SCP-curve', 'WCP']
DEBUG_RUN = os.environ.get('MESD_DEBUG') == '1'          # developer test only
STATUS = f'{REC}/step_status.json'

# Expected seed-0 role counts (execution plan, Step 2 table; CAL_FRAC = 0.20, full data)
ROLE_COUNTS = {('S0_random', 'all'): (46010, 57741, 184212, 37), ('S1_Lextreme', 'all'): (46038, 57600, 184362, 0),
               ('S2_T125', 'all'): (46038, 57600, 184362, 0), ('S3_ff', 'all'): (39158, 92000, 156842, 0),
               ('S4_LOPO', 'N180A'): (55160, 11992, 220840, 8), ('S4_LOPO', 'N180B'): (49463, 40473, 198037, 27),
               ('S4_LOPO', 'N350A'): (55163, 11976, 220837, 24), ('S4_LOPO', 'N40A'): (48564, 44970, 194436, 30),
               ('S4_LOPO', 'N45A'): (53960, 17988, 216040, 12), ('S4_LOPO', 'N45B'): (46765, 53964, 187235, 36),
               ('S4_LOPO', 'N55A'): (48564, 44970, 194436, 30), ('S4_LOPO', 'N90A'): (45266, 61459, 181234, 41)}


# ------------------------------------------------------------------ framework
def _status():
    try:
        return json.load(open(STATUS))
    except Exception:
        return {}


def require(*steps):
    """Stop the cell unless every listed step has PASSED (plan checkpoints)."""
    st = _status()
    bad = {s: st.get(s, {}).get('result', 'NOT RUN') for s in steps if not st.get(s, {}).get('result', '').startswith('PASS')}
    if bad and DEBUG_RUN:
        print(f'(developer test: prerequisite check bypassed {bad})'); return
    if bad:
        raise RuntimeError('this step cannot start yet. Prerequisite step(s) not PASSED: '
                           + ', '.join(f'Step {k} = {v}' for k, v in bad.items())
                           + '. Run them first (or re-run them until they PASS).')
    print('prerequisites PASSED:', ', '.join(f'Step {s}' for s in steps) or 'none')


class _Log:
    def __init__(self):
        self.rows = []
    def check(self, ok, what, expected, got, level='FAIL', fix=''):
        """ok -> PASS; otherwise `level` (FAIL blocks the next step, WARN does not)."""
        self.rows.append(dict(status='PASS' if ok else level, check=what, expected=str(expected), got=str(got),
                              fix='' if ok else fix))


def _fmt(x, d=3):
    try:
        return f'{float(x):.{d}f}'
    except Exception:
        return str(x)


def run_checks(step, title, body, next_step):
    """Run body(log) and print the PASS/FAIL check log with banners; save everything."""
    lg = _Log()
    buf = io.StringIO()
    stamp = f'{datetime.datetime.now():%Y-%m-%d %H:%M:%S}'
    with contextlib.redirect_stdout(buf):
        print(f'STEP {step}: {title}')
        print(f'code {code_version()} | MESD commit {mesd_commit()} | {stamp} | GPU {runtime_info()[0]}')
        print('\n--- KEY RESULTS ---')
        try:
            body(lg)
        except Exception as e:                       # a check log must never hide a problem
            lg.check(False, 'check log completed', 'no error', f'{type(e).__name__}: {e}',
                     fix='paste this log back; the step outputs are missing or malformed')
        try:                                         # v7: refresh the Drive folders figures/ and results/
            pub = publish(verbose=False)
            if pub:
                print('\n--- COPIED TO DRIVE (figures/ and results/ in ' + ROOT + ') ---')
                for d, n in pub:
                    print(f'  {d:24s} {n} files')
        except Exception as e:
            lg.check(False, 'copy to Drive folders figures/ and results/', 'done', f'{type(e).__name__}: {e}', 'WARN',
                     fix='paste this log back; the originals in work/ are unaffected')
        print('\n--- CHECKS (expected values from the execution plan) ---')
        for r in lg.rows:
            line = f"[{r['status']}] {r['check']} | expected: {r['expected']} | got: {r['got']}"
            if r['fix']:
                line += f" | if not: {r['fix']}"
            print(line)
        nf = sum(r['status'] == 'FAIL' for r in lg.rows); nw = sum(r['status'] == 'WARN' for r in lg.rows)
        # INFO lines are reported facts for the paper; they never block or warn
        npass = sum(r['status'] == 'PASS' for r in lg.rows)
        if nf:
            result = 'FAIL'
            verdict = f'STEP {step} RESULT: FAIL ({nf} failed, {nw} warnings, {npass} passed) -> DO NOT PROCEED. Paste this log back.'
        elif nw:
            result = 'PASS_WITH_WARNINGS'
            verdict = (f'STEP {step} RESULT: PASS WITH WARNINGS ({npass} passed, {nw} warnings) -> you can proceed to '
                       f'{next_step}, but paste this log back so the warnings are reviewed.')
        else:
            result = 'PASS'
            verdict = f'STEP {step} RESULT: PASS (all {npass} checks passed) -> you can proceed to {next_step}.'
        print('\n' + verdict)
    txt = buf.getvalue()
    bar = '=' * 26
    print(f'\n{bar} STEP {step} CHECK LOG (copy from here) {bar}\n{txt}{bar} END OF STEP {step} CHECK LOG {bar}')
    os.makedirs(f'{REC}/reports', exist_ok=True)
    fn = f'{REC}/reports/step_{step}_{datetime.datetime.now():%Y%m%d_%H%M%S}.txt'
    open(fn, 'w').write(txt)
    new = not os.path.exists(f'{REC}/step_checks.csv')
    with open(f'{REC}/step_checks.csv', 'a', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=['time', 'step', 'code_version', 'status', 'check', 'expected', 'got', 'fix'])
        if new:
            w.writeheader()
        for r in lg.rows:
            w.writerow(dict(time=stamp, step=step, code_version=code_version(), **r))
    st = _status(); st[step] = dict(result=result, time=stamp, code_version=code_version(), debug=DEBUG_RUN)
    json.dump(st, open(STATUS, 'w'), indent=2)
    print(f'(check log saved to {os.path.relpath(fn, ROOT)}; all checks appended to records/step_checks.csv)')


def _w(work):
    return f'{WORKROOT}/{work}'


# ------------------------------------------------------------------ Step 1
def check_step1():
    def body(lg):
        W = _w('main')
        aud = pd.read_csv(f'{W}/audit_per_file.csv')
        fl = json.load(open(f'{W}/dataset_flags.json'))
        lg_ = pd.read_parquet(f'{W}/mesd_long.parquet', columns=['pdk', 'family', 'curve_id', 'corner', 'T_C'])
        print(f'rows (bias points): {len(lg_):,} | curves: {lg_.curve_id.nunique():,} | JSON files: {len(aud)} | PDKs: {lg_.pdk.nunique()}')
        print(lg_.groupby('pdk', observed=True).agg(family=('family', 'first'), curves=('curve_id', 'nunique'),
              points=('curve_id', 'size'), corners=('corner', 'nunique'), temps=('T_C', 'nunique')).sort_values('curves'))
        print('\naudit per file:'); print(aud.to_string(index=False))
        viol = aud[aud.frac_cap_conservation_violated > 0.10]
        ok_files = sorted(set(aud.file) - set(viol.file))
        r = viol.median_Cgs_over_gm_div_omega
        lg.check(fl['commit'] == PINNED, 'MESD commit in use', PINNED, fl['commit'], fix='plan error E3: delete /content/mesd_repo, re-run Step 1')
        lg.check(fl['n_json'] == 44, 'JSON files parsed', 44, fl['n_json'], fix='plan error E3')
        lg.check(fl['n_rows'] == 4_451_750 and fl['n_curves'] == 305_750, 'rows | curves', '4,451,750 | 305,750',
                 f"{fl['n_rows']:,} | {fl['n_curves']:,}", fix='plan error E3: data changed or clone interrupted')
        lg.check(len(viol) == 42 and ok_files == ['N45A-nmos1.json', 'N45A-pmos1.json'],
                 'files violating Cgs/Cgd charge conservation in >10% of curves',
                 '42 of 44 (only N45A-nmos1 and N45A-pmos1 pass)', f'{len(viol)} of {len(aud)} (passing: {ok_files})',
                 fix='audit finding 1 changed; paste this log back')
        lg.check(r.notna().all() and r.min() >= 0.80 and r.max() <= 1.03, 'median Cgs/(gm/2*pi*f) of the violating files',
                 'between about 0.83 and 1.01', f'{_fmt(r.min())} to {_fmt(r.max())}', 'WARN',
                 fix='the gm/(2*pi*f) artefact explanation needs re-checking')
        lg.check(fl['mc_present'] is False, 'Monte Carlo files present', False, fl['mc_present'], 'WARN',
                 fix='audit finding 2 changed; report it')
    run_checks('1', 'build the dataset and run the audit', body, 'Step 2')


# ------------------------------------------------------------------ Step 2
def check_step2(work='main', label='features, device anchors and splits', next_step='Step 3 (GPU session)', exact=True):
    def body(lg):
        W = _w(work)
        anc = pd.read_csv(f'{W}/anchors.csv')
        mt = pd.read_parquet(f'{W}/model_table.parquet', columns=['curve_id', 'pdk', 'valid_Id', 'is_anchor', 'region'])
        sp = pd.read_parquet(f'{W}/splits.parquet')
        for c in ['scenario', 'fold', 'role']:
            sp[c] = sp[c].astype(str)
        n_cur = mt.curve_id.nunique(); n_anchor = mt.loc[mt.is_anchor, 'curve_id'].nunique()
        print(f'planar rows: {len(mt):,} | curves: {n_cur:,} | Id rows (Vds>0): {int(mt.valid_Id.sum()):,} | '
              f'anchor curves: {n_anchor} | devices: {len(anc)} | PDKs: {sorted(mt.pdk.astype(str).unique())}')
        print('\ndevice anchors (Vth_ref in V, log10 currents in A):'); print(anc.round(3).to_string(index=False))
        rc = sp[sp.seed == 0].groupby(['scenario', 'fold', 'role']).size().unstack(fill_value=0)
        rc = rc.reindex(columns=['cal', 'test', 'train', 'unused'], fill_value=0)
        print('\nrole counts, seed 0 (curves):'); print(rc)
        anchors = set(mt.loc[mt.is_anchor, 'curve_id'].astype(str))
        leak = int((sp.curve_id.astype(str).isin(anchors) & sp.role.isin(['cal', 'test'])).sum())
        dup = int(sp.duplicated(['curve_id', 'scenario', 'fold', 'seed']).sum())
        lg.check(anc.Vth_ref.notna().all(), 'every device has a finite Vth_ref', 'no NaN', f'{int(anc.Vth_ref.isna().sum())} NaN',
                 fix='plan error E4')
        lg.check(leak == 0, 'anchor curves used as calibration or test', 0, leak, fix='leakage: paste this log back')
        lg.check(dup == 0, 'curves with more than one role in a run', 0, dup, fix='paste this log back')
        if exact:
            lo, hi = anc.loc[anc.Vth_ref.idxmin()], anc.loc[anc.Vth_ref.idxmax()]
            lg.check(len(anc) == 33, 'devices in the anchor table', '33 (34 planar device files minus N180A-pmos1; '
                     'the plan text said 35: a counting error)', len(anc))
            lg.check(n_cur == 288_000, 'planar curves', '288,000', f'{n_cur:,}')
            lg.check(n_anchor == 208, 'anchor curves', 208, n_anchor)
            lg.check(abs(lo.Vth_ref - 0.150) < 0.0015 and lo.dev_key == 'N90A-nmos1' and abs(hi.Vth_ref - 0.955) < 0.0015
                     and hi.dev_key == 'N180B-pmos2', 'Vth_ref range', '0.150 V (N90A-nmos1) to 0.955 V (N180B-pmos2)',
                     f'{lo.Vth_ref:.3f} V ({lo.dev_key}) to {hi.Vth_ref:.3f} V ({hi.dev_key})')
            mism = []
            for (s, f), exp in ROLE_COUNTS.items():
                got = tuple(int(v) for v in rc.loc[(s, f)]) if (s, f) in rc.index else None
                if got != exp:
                    mism.append(f'{s}/{f}: expected {exp}, got {got}')
            lg.check(not mism, 'seed-0 role counts (cal, test, train, unused) for all 12 scenario/fold rows',
                     'exactly the plan table', 'all 12 match' if not mism else '; '.join(mism), fix='paste this log back')
            lg.check(len(sp.groupby(['scenario', 'fold', 'seed'])) == 60, 'split definitions', '60 (4 scenarios x 5 seeds + 8 folds x 5 seeds)',
                     len(sp.groupby(['scenario', 'fold', 'seed'])))
    run_checks('2' if work == 'main' else f'2 ({work})', label, body, next_step)


# ------------------------------------------------------------------ Step 3
def check_step3():
    def body(lg):
        W = _w('main')
        tl = pd.read_csv(f'{W}/tuning_log.csv'); tj = json.load(open(f'{W}/tuning.json'))
        print('tuning grid (inner validation = 15% of S0 seed-0 TRAINING curves; no calibration or test curve used):')
        print(tl.round(4).to_string(index=False)); print('\nselected and frozen in tuning.json:', tj)
        sel = tl[(tl.epochs == tj['epochs']) & np.isclose(tl.lr, tj['lr']) & (tl.norm_wl == tj['norm_wl'])]
        lg.check(not tj.get('debug', False), 'tuning.json comes from a full (non-debug) run', 'debug = False', tj.get('debug'))
        lg.check(len(sel) == 1 and not bool(sel.diverged.iloc[0]), 'selected configuration diverged', False,
                 bool(sel.diverged.iloc[0]) if len(sel) else 'not found', fix='lower the learning rates in the grid')
        lg.check(False, 'winning configuration (plan rule: whatever tuning.json says is final)',
                 'decided by the grid; the CPU pilot at 15% of data had favoured 100 epochs at lr 5e-3',
                 f"{tj['epochs']} epochs, lr {tj['lr']}, norm_wl {tj['norm_wl']} -> report these values in Methods", 'INFO')
        same = tl[np.isclose(tl.lr, tj['lr']) & (tl.norm_wl == tj['norm_wl'])].sort_values('epochs')
        longer = same[same.epochs > tj['epochs']]
        if len(longer):
            lg.check(False, 'longer schedule at the same learning rate',
                     'usually at least as good as a shorter one (one seed per configuration)',
                     '; '.join(f"{int(r.epochs)} epochs: val MAE {r.val_mae_dec:.4f}, train MSE {r.train_mse_std:.1e}" for r in longer.itertuples())
                     + f" vs selected val MAE {tj['val_mae_dec']:.4f} -> a higher final training loss with more epochs suggests a late-schedule "
                     "instability at lr 5e-3; Step 5 checks the training loss of every run, Step 6 checks accuracy", 'INFO')
        nw_ = tl[(tl.epochs == tj['epochs']) & np.isclose(tl.lr, tj['lr']) & (tl.norm_wl != tj['norm_wl'])]
        if len(nw_):
            lg.check(False, 'effect of the W/L normalisation (same epochs and lr)', 'normalised target better (plan design choice)',
                     f"val MAE {nw_.val_mae_dec.iloc[0]:.4f} without vs {tj['val_mae_dec']:.4f} with normalisation", 'INFO')
        lg.check(tj['val_mae_dec'] <= 0.05, 'validation MAE (decades)', 'near 0.03 (gate on S0 later: <= 0.05)',
                 _fmt(tj['val_mae_dec'], 4), 'WARN', fix='the Step 6 accuracy gate may fail; plan: extend the grid')
        lg.check(tj['val_medrel_above'] <= 0.05, 'validation median relative error above Vth', 'near 3-4% (gate: <= 5%)',
                 f"{100 * tj['val_medrel_above']:.2f}%", 'WARN', fix='the Step 6 accuracy gate may fail')
        short = tl[(tl.epochs == 40) & np.isclose(tl.lr, 2e-3)]
        if len(short):
            lg.check(short.val_mae_dec.iloc[0] > 1.5 * tj['val_mae_dec'], '40 epochs at 2e-3 is clearly worse',
                     'several times worse than the winner', f"{_fmt(short.val_mae_dec.iloc[0], 4)} vs {_fmt(tj['val_mae_dec'], 4)}", 'WARN')
    run_checks('3', 'select hyperparameters on inner validation curves', body, 'Step 4')


# ------------------------------------------------------------------ Steps 4 / 9.4 (smoke)
def check_smoke(target='y_logId', step='4', work='smoke', next_step='Step 5'):
    def body(lg):
        W = _w(work)
        n = len(glob.glob(f'{W}/preds/{target}/*.parquet'))
        logl = sum(1 for _ in open(f'{W}/preds/{target}/train_log.jsonl'))
        r = pd.read_csv(f'{W}/results/{target}/results_long.csv')
        figs = sorted(os.path.basename(f) for f in glob.glob(f'{W}/paper/{target}/*.png'))
        print(f'smoke runs: {n} | log lines: {logl} | evaluated methods: {sorted(r.method.unique())}')
        print('figures:', figs)
        print('(2 epochs on 3% of the curves: the numbers are meaningless; only the pipeline is checked)')
        lg.check(n == 12 and logl == 12, 'smoke runs and train_log lines', '12 runs, 12 lines', f'{n} runs, {logl} lines')
        lg.check(set(MAIN_METHODS) <= set(r.method), 'all interval methods evaluated', ', '.join(MAIN_METHODS), 'all present'
                 if set(MAIN_METHODS) <= set(r.method) else sorted(set(MAIN_METHODS) - set(r.method)))
        lg.check(len(figs) == 6, 'figures written', 6, len(figs))
    run_checks(step, f'smoke test ({target}, separate folder work/{work})', body, next_step)


# ------------------------------------------------------------------ Steps 5 / 9.5 / 10.2 / 10.4 (training)
def check_train(target, step, work='main', scen=SC, seeds_main=(0, 1, 2, 3, 4), seeds_lopo=(0, 1, 2),
                next_step='next step', title=None, log_prefix=None):
    def body(lg):
        W = _w(work)
        files = sorted(glob.glob(f'{W}/preds/{target}/*.parquet'))
        lp = f'{W}/preds/{target}/train_log.jsonl'
        log = pd.DataFrame([json.loads(l) for l in open(lp)]) if os.path.exists(lp) else pd.DataFrame()
        sp = pd.read_parquet(f'{W}/splits.parquet', columns=['scenario', 'fold', 'seed']).drop_duplicates()
        sm, sl = ([0], [0]) if DEBUG_RUN else (list(seeds_main), list(seeds_lopo))
        want = [f'{s}__{f}__seed{d}' for s, f, d in sp.astype({'scenario': str, 'fold': str}).itertuples(index=False)
                if s in scen and d in (sl if s == 'S4_LOPO' else sm)]
        names = {os.path.basename(f)[:-8] for f in files}
        missing = sorted(set(want) - names)
        if len(log):
            log = log.drop_duplicates(['scenario', 'fold', 'seed'], keep='last')     # latest training of each run
            log['ens_loss_mean'] = log.train_loss_ens.apply(np.mean); log['ens_loss_max'] = log.train_loss_ens.apply(max)
            print('per run (standardized train MSE of the 5 networks; pinball loss of the quantile net):')
            print(log[['scenario', 'fold', 'seed', 'n_train', 'n_eval', 'ens_loss_mean', 'ens_loss_max',
                       'train_loss_q', 'minutes']].round(5).to_string(index=False))
            print(f'\ntraining time logged: {log.minutes.sum() / 60:.2f} h | mean per run {log.minutes.mean():.1f} min')
            if missing:
                print(f'estimated time for the missing runs: {len(missing) * log.minutes.mean() / 60:.1f} h')
        if missing:
            print('\nruns still missing:', missing)
        engine_log = sorted(glob.glob(f'{LOGS}/{log_prefix}_*.log')) if log_prefix else []
        used = bool(engine_log) and 'using tuning.json' in open(engine_log[-1]).read()
        lg.check(len(missing) == 0, 'prediction files', f'{len(want)} runs', f'{len(want) - len(missing)} done',
                 fix='not finished: run 0.0, then re-run this cell; finished runs are skipped')
        lg.check(len(log) >= len(want) - len(missing), 'runs with a training record', f'one per finished run ({len(want) - len(missing)})', len(log))
        if not DEBUG_RUN:
            lg.check(used, 'training used the frozen tuning.json', "log line 'using tuning.json: ...'",
                     'found' if used else 'not found in the latest training logs', fix='run Step 3 first')
            if len(log):
                hi = log[log.ens_loss_max > 0.05]
                lg.check(len(hi) == 0, 'runs with standardized train MSE > 0.05 (divergence guard limit)', 0, len(hi),
                         fix='plan error E8: see the retraining messages in the log')
                lg.check(log.ens_loss_max.max() < 4e-3, 'ensemble train loss', 'near 4e-4 (pilot at 15% of data)',
                         f'max {log.ens_loss_max.max():.2e}, median {log.ens_loss_mean.median():.2e}', 'WARN')
        if files:
            P = pd.read_parquet(files[-1])
            mu = [c for c in P.columns if c.startswith('mu') and c[2:].isdigit()]
            lg.check(np.isfinite(P[mu + ['q_lo', 'q_hi']].to_numpy()).all(), 'finite predictions in the last file', 'all finite', 'yes')
            lg.check(len(mu) == (2 if DEBUG_RUN else 5), 'ensemble members per file', 2 if DEBUG_RUN else 5, len(mu))
            lg.check(set(P.role.astype(str).unique()) == {'cal', 'test'}, 'rows written', 'calibration and test only',
                     sorted(P.role.astype(str).unique()), fix='leakage risk: paste this log back')
    run_checks(step, title or f'train the surrogates for {target}', body, next_step)


# ------------------------------------------------------------------ Steps 6 / 9.6 (accuracy gate)
def check_gate(target='y_logId', step='6', next_step='Step 7'):
    def body(lg):
        W = _w('main')
        files = sorted(glob.glob(f'{W}/preds/{target}/S0_random__all__seed*.parquet'))
        meta = pd.read_parquet(f'{W}/model_table.parquet', columns=['valid_Id', 'region'])
        if target == 'y_logId':
            meta = meta[meta.valid_Id].reset_index(drop=True)
        reg = meta.region.astype(str).to_numpy()
        rows = []
        for f in files:
            P = pd.read_parquet(f); P = P[P.role.astype(str) == 'test']
            mu = P[[c for c in P.columns if c.startswith('mu') and c[2:].isdigit()]].to_numpy().mean(1)
            e = np.abs(mu - P.y.to_numpy()); ab = reg[P.row.to_numpy()] == 'above'
            rows.append(dict(file=os.path.basename(f), mae_dec=e.mean(), mae_dec_sub=e[~ab].mean(),
                             medrel_above=np.median(np.abs(10 ** (mu - P.y.to_numpy())[ab] - 1))))
        g = pd.DataFrame(rows)
        print(f'accuracy of the 5-network ensemble mean on the S0 (random split) TEST curves, {target}:')
        print(g.round(4).to_string(index=False))
        m = g[['mae_dec', 'mae_dec_sub', 'medrel_above']].mean()
        print(f'\nmean over seeds: MAE {m.mae_dec:.4f} dec | MAE sub {m.mae_dec_sub:.4f} dec | median rel. error above Vth {100 * m.medrel_above:.2f}%')
        print('pilot values (plan): MAE 0.028 | MAE sub 0.052 | median rel. error 2.9%')
        fix = 'plan Step 6: do NOT look at S1-S4; extend the grid in Step 3 (e.g. 150 epochs or HIDDEN 512), re-tune, retrain, document both rounds'
        lg.check(len(g) == (1 if DEBUG_RUN else 5), 'S0 seeds available', 1 if DEBUG_RUN else 5, len(g), fix='finish the S0 runs of the training step')
        lg.check(m.medrel_above <= 0.05, 'median relative error above threshold', '<= 5% (pilot 2.9%)', f'{100 * m.medrel_above:.2f}%', fix=fix)
        lg.check(m.mae_dec <= 0.05, 'MAE, all points (decades)', '<= 0.05 (pilot 0.028)', _fmt(m.mae_dec, 4), fix=fix)
        lg.check(m.mae_dec_sub <= 0.10, 'MAE, subthreshold (decades)', '<= 0.10 (pilot 0.052)', _fmt(m.mae_dec_sub, 4), fix=fix)
    run_checks(step, f'accuracy gate (go / no-go) for {target}', body, next_step)


# ------------------------------------------------------------------ Steps 7 / 9.7 / 10.x (evaluation)
def _print_eval(r, target, work, tag):
    acc = r[r.method == 'accuracy']
    a = r[(r.alpha == 0.10) & r.method.isin(MAIN_METHODS)]
    print(f'runs evaluated: {len(acc)} | test curves per run {int(acc.n_test_curves.min())}-{int(acc.n_test_curves.max())} | '
          f'calibration curves per run {int(acc.n_cal_curves.min())}-{int(acc.n_cal_curves.max())}')
    print('\nACCURACY (RQ1; mean and SD over seeds/folds):')
    print(acc.groupby('scenario')[['mae_dec', 'mae_dec_sub', 'mae_dec_above', 'medrel_above', 'auroc_sigma_err',
                                   'frac_err_gt_flag']].agg(['mean', 'std']).round(3))
    for met, lab in [('coverage', 'POINT COVERAGE, alpha = 0.10 (nominal 0.90)'), ('curve_coverage', 'WHOLE-CURVE COVERAGE'),
                     ('width_median', 'MEDIAN WIDTH (decades)'), ('worst_group_cov', 'WORST-GROUP COVERAGE (PDK x region)'),
                     ('frac_infinite', 'FRACTION OF INFINITE INTERVALS')]:
        print(f'\n{lab}:')
        print(a.groupby(['scenario', 'method'])[met].mean().unstack('method').reindex(columns=MAIN_METHODS).round(3))
    ci = a.groupby(['scenario', 'method'])[['cov_ci_lo', 'cov_ci_hi']].mean().round(3).unstack('method')
    print('\nPOINT COVERAGE 95% CLUSTER-BOOTSTRAP CI (mean of run CIs):')
    print(ci['cov_ci_lo'].reindex(columns=MAIN_METHODS).astype(str) + '-' + ci['cov_ci_hi'].reindex(columns=MAIN_METHODS).astype(str))
    print('\nCOVERAGE AT alpha = 0.20 / 0.10 / 0.05:')
    print(r[r.method.isin(['SCP-ens', 'NCP', 'CQR', 'SCP-curve', 'Mondrian-region'])].groupby(['scenario', 'method', 'alpha'])
          ['coverage'].mean().unstack('alpha').round(3))
    rc = r[(r.alpha == 0.10) & r.method.str.match(r'^(Recal|RecalNCP)-\d+$')]
    if len(rc):
        print('\nRECALIBRATION WITH k TARGET-DOMAIN CURVES (RQ3): coverage | median width')
        print(rc.groupby(['scenario', 'method'])[['coverage', 'width_median']].mean().unstack('method').round(3))
    if (a.scenario == 'S4_LOPO').any():
        print('\nLOPO COVERAGE BY HELD-OUT PDK (alpha = 0.10):')
        print(a[a.scenario == 'S4_LOPO'].groupby(['fold', 'method'])['coverage'].mean().unstack('method').reindex(columns=MAIN_METHODS).round(3))
        print('\nLOPO ACCURACY BY HELD-OUT PDK:')
        print(acc[acc.scenario == 'S4_LOPO'].groupby('fold')[['mae_dec', 'medrel_above', 'auroc_sigma_err']].mean().round(3))
    print('\nDOMAIN-CLASSIFIER AUC (WCP):')
    print(r[(r.method == 'WCP') & (r.alpha == 0.10)].groupby('scenario')['domain_auc'].agg(['mean', 'min']).round(3))
    cp = f'{_w(work)}/results/{target}{tag}/curve_checks.csv'
    if target == 'y_logId' and os.path.exists(cp) and os.path.getsize(cp) > 5:
        cc = pd.read_csv(cp)
        cols = ['nonmono_pred_above', 'nonmono_true_above', 'nonmono_true_all', 'vth_err_mV', 'vth_covered', 'vth_width_mV',
                'vth_covered_pointwise']
        print('\nCURVE CHECKS at Vds = VDD (RQ4: Vth error, Vth interval from the curve band):')
        print(cc[['scenario'] + cols].astype({c: float for c in cols}).groupby('scenario')[cols].agg(['mean', 'count']).round(3))
    return acc, a


def check_eval(target='y_logId', step='7', work='main', tag='', next_step='Step 8', title=None, full=True):
    def body(lg):
        r = pd.read_csv(f'{_w(work)}/results/{target}{tag}/results_long.csv')
        acc, a = _print_eval(r, target, work, tag)
        s0 = a[a.scenario == 'S0_random']; wcp = a[a.method == 'WCP']
        lg.check(a.coverage.notna().all(), 'missing coverage values', 0, int(a.coverage.isna().sum()))
        if full:
            lg.check(len(acc) == (12 if DEBUG_RUN else 44), 'runs evaluated', 12 if DEBUG_RUN else 44, len(acc))
        if (wcp.scenario == 'S0_random').any():
            d0 = wcp[wcp.scenario == 'S0_random'].domain_auc.mean()
            lg.check(0.45 <= d0 <= 0.55, 'S0 domain-classifier AUC', '0.45 to 0.55 (pilot 0.50)', _fmt(d0), fix='plan error E12')
            c = s0[s0.method == 'SCP-ens']
            lg.check(0.89 <= c.coverage.mean() <= 0.91 and c.cov_ci_lo.mean() <= 0.90 <= c.cov_ci_hi.mean(),
                     'S0 coverage of SCP-ens at 90%', '0.89 to 0.91, CI containing 0.90 (pilot 0.899, CI 0.896-0.902)',
                     f'{_fmt(c.coverage.mean())} (CI {_fmt(c.cov_ci_lo.mean())}-{_fmt(c.cov_ci_hi.mean())})', fix='plan error E11')
            cv = s0[s0.method == 'SCP-curve'].curve_coverage.mean()
            lg.check(0.88 <= cv <= 0.92, 'S0 whole-curve coverage of SCP-curve', '0.88 to 0.92 (pilot 0.903)', _fmt(cv), fix='plan error E11')
        sh = wcp[wcp.scenario != 'S0_random']
        if len(sh):
            lg.check(sh.domain_auc.min() >= 0.99, 'S1 to S4 domain-classifier AUC (every run)', '>= 0.99 (pilot 1.00)',
                     f'min {_fmt(sh.domain_auc.min())}', 'WARN', fix='support overlap exists; WCP becomes informative; report it')
        cp = f'{_w(work)}/results/{target}{tag}/curve_checks.csv'
        if target == 'y_logId' and os.path.exists(cp) and os.path.getsize(cp) > 5:
            cc = pd.read_csv(cp)
            v = cc.nonmono_true_above.astype(float).mean()
            lg.check(v == 0, 'above-threshold non-monotonic TRUE curves', '0.000', _fmt(v), fix='data or harmonisation error; inspect the device')
    run_checks(step, title or f'uncertainty evaluation for {target}{tag}', body, next_step)


# ------------------------------------------------------------------ Steps 8 / 9.8 (figures + hypotheses)
def _hypotheses(r, tab4):
    """Decision rules of plan section 6 (fixed in advance). Returns printable lines."""
    a = r[r.alpha == 0.10]; acc = r[r.method == 'accuracy']
    m = lambda sc, meth, col='coverage': a[(a.scenario == sc) & (a.method == meth)][col].mean()
    out = []
    v = {k: m('S0_random', k) for k in ['SCP-single', 'SCP-ens', 'NCP', 'CQR', 'Mondrian-region']}
    ok = all(0.89 <= x <= 0.91 for x in v.values())
    out.append(('H1 in-distribution', ok, 'each of SCP-single, SCP-ens, NCP, CQR, Mondrian: S0 coverage 0.89-0.91 (pilot 0.897-0.902)',
                ', '.join(f'{k} {x:.3f}' for k, x in v.items())))
    lo = a[(a.scenario == 'S4_LOPO') & (a.method == 'SCP-ens')].groupby('fold')['coverage'].mean()
    out.append(('H1 technology shift', int((lo < 0.85).sum()) >= 4, 'SCP-ens coverage < 0.85 for at least 4 of 8 PDKs (pilot 2 of 2)',
                f'{int((lo < 0.85).sum())} of {len(lo)}: ' + ', '.join(f'{k} {x:.3f}' for k, x in lo.items())))
    w = {k: m('S0_random', k, 'worst_group_cov') for k in ['SCP-ens', 'NCP', 'Mondrian-region']}
    out.append(('H2', w['SCP-ens'] < 0.85 and max(w['NCP'], w['Mondrian-region']) - w['SCP-ens'] >= 0.05,
                'S0 SCP-ens worst-group coverage (worst PDK x region group, >= 1000 points) < 0.85 and NCP or Mondrian raises it by >= 0.05',
                ', '.join(f'{k} {x:.3f}' for k, x in w.items())))
    wc = a[(a.method == 'WCP') & (a.scenario != 'S0_random')]
    out.append(('H3', bool(len(wc)) and (wc.domain_auc >= 0.99).all() and (wc.frac_infinite >= 0.5).all(),
                'every S1-S4 run: domain AUC >= 0.99 and >= 50% infinite WCP intervals',
                f'min AUC {wc.domain_auc.min():.3f}, min infinite share {wc.frac_infinite.min():.3f}'))
    au0 = acc[acc.scenario == 'S0_random'].auroc_sigma_err.mean(); au4 = acc[acc.scenario == 'S4_LOPO'].auroc_sigma_err.mean()
    out.append(('H4', au0 >= 0.80 and au4 < au0, 'S0 AUROC >= 0.80 and mean S4 AUROC lower (pilot 0.91 vs 0.72-0.78)',
                f'S0 {au0:.3f}, S4 {au4:.3f}'))
    c_curve, c_ens = m('S0_random', 'SCP-curve', 'curve_coverage'), m('S0_random', 'SCP-ens', 'curve_coverage')
    out.append(('H5', 0.88 <= c_curve <= 0.92 and c_ens < 0.70, 'S0 whole-curve coverage: SCP-curve 0.88-0.92 and SCP-ens < 0.70 (pilot 0.903 vs 0.402)',
                f'SCP-curve {c_curve:.3f}, SCP-ens {c_ens:.3f}'))
    lines = [f"{'SUPPORTED' if ok else 'NOT SUPPORTED'} | {name} | rule: {rule} | observed: {obs}" for name, ok, rule, obs in out]
    rc = a[a.method.str.match(r'^Recal-\d+$')].copy()
    if len(rc):
        rc['k'] = rc.method.str.split('-').str[1].astype(int)
        g = rc.groupby(['scenario', 'k'])[['coverage', 'width_median']].mean().reset_index()
        for sc in SC:
            q = g[(g.scenario == sc) & (g.coverage >= 0.88)].sort_values('k')
            lines.append(f'RQ3 (descriptive) | {sc}: smallest k with mean coverage >= 0.88 = '
                         + (f'{int(q.k.iloc[0])}, median width {q.width_median.iloc[0]:.3f} dec' if len(q) else 'none of 5/20/100'))
    if tab4 is not None and len(tab4):
        for _, t in tab4[tab4.family == 'primary'].iterrows():
            better = t.median_gap_method < t.median_gap_SCPens
            way = 'BETTER than SCP-ens (closer to 0.90)' if better else 'WORSE than SCP-ens (farther from 0.90)'
            nc = (f", closer in {int(t.folds_closer_to_090)} of {int(t.n_folds)} folds"
                  if 'folds_closer_to_090' in t and pd.notna(t.folds_closer_to_090) else '')
            verdict = f'significantly {way}' if t.p_holm < 0.05 else f'no significant difference (direction: {way})'
            lines.append(f"CONFIRMATORY | {t.method} vs SCP-ens on |coverage - 0.90| over {int(t.n_folds)} folds: Holm p = {t.p_holm:.4f} "
                         f"-> {verdict} (median gap {t.median_gap_method:.3f} vs {t.median_gap_SCPens:.3f}{nc})")
    else:
        lines.append('CONFIRMATORY | Table 4 not available (needs all 8 LOPO folds)')
    return lines


def check_figs(target='y_logId', step='8', next_step='Step 9 (Cgg) or Step 10', work='main'):
    def body(lg):
        P = f'{_w(work)}/paper/{target}'
        files = sorted(os.listdir(P))
        for f in files:
            print(f'  {f:45s} {os.path.getsize(f"{P}/{f}") / 1024:8.1f} kB')
        for t in ['table1_accuracy.csv', 'table1b_curve_checks.csv', 'table2_coverage_alpha0.10.csv',
                  'table3_lopo_coverage_by_pdk.csv', 'table4_lopo_paired_tests.csv']:
            p = f'{P}/{t}'
            if os.path.exists(p) and os.path.getsize(p) > 5:
                print(f'\n--- {t} ---'); print(open(p).read())
        need = ['table1_accuracy.csv', 'table2_coverage_alpha0.10.csv', 'table3_lopo_coverage_by_pdk.csv'] + \
               [f'fig{i}_{n}.{e}' for i, n in [(1, 'audit_cgs_artifact'), (2, 'coverage_by_method'), (3, 'recalibration_budget'),
                                               (4, 'lopo_coverage_by_pdk'), (5, 'recalibration_width'), (6, 'curve_coverage')]
                for e in ('png', 'pdf')]
        miss = [n for n in need if n not in files]
        lg.check(not miss, 'plan Step 8 outputs (tables 1-3, figures 1-6 as PNG and PDF)', 'all present', 'all present' if not miss else miss)
        ap = f'{P}/figure_audit.csv'                      # v6: overlap audit written by the figure engine
        if os.path.exists(ap):
            au = pd.read_csv(ap).fillna('')
            print('\n--- FIGURE AUDIT (size as written, overlaps of legends, texts and data) ---')
            for _, a in au.iterrows():
                print(f"  {a.figure:30s} {a.width_cm:5.2f} x {a.height_cm:5.2f} cm | overlaps: {int(a.n_overlaps) or 'none'}"
                      + (f' -> {a.overlaps}' if a.n_overlaps else ''))
            bad = au[au.n_overlaps > 0]
            lg.check(len(bad) == 0, 'no overlaps (legend vs data, text vs text, text vs data) in any figure', '0 overlaps',
                     '0 overlaps' if len(bad) == 0 else f'{int(bad.n_overlaps.sum())} in {", ".join(bad.figure)}', 'WARN',
                     fix='paste the log back; the figure layout is corrected in a code update (no recomputation of results)')
            wide = au[au.width_cm > au.canvas_width_cm + 0.05]
            lg.check(len(wide) == 0, 'figure width as written within 8.5 cm (single) / 15 cm (double)', 'yes',
                     'yes' if len(wide) == 0 else f'too wide: {", ".join(wide.figure)}', 'WARN',
                     fix='paste the log back (layout fix in a code update)')
        t4p = f'{P}/table4_lopo_paired_tests.csv'
        lg.check(os.path.exists(t4p), 'Table 4 (exact Wilcoxon over 8 PDK folds, Holm within NCP, SCP-curve, CQR)', 'present',
                 'present' if os.path.exists(t4p) else 'missing', fix='needs all 8 LOPO folds')
        if target == 'y_logId':
            r = pd.read_csv(f'{_w(work)}/results/{target}/results_long.csv')
            tab4 = pd.read_csv(t4p) if os.path.exists(t4p) else None
            print('\n--- HYPOTHESES (plan section 6 decision rules; results, not pass/fail of the pipeline) ---')
            lines = _hypotheses(r, tab4)
            for l in lines:
                print(l)
            open(f'{REC}/hypotheses_results.txt', 'w').write('\n'.join(lines) + '\n')
            lg.check(len(lines) >= 6, 'all pre-specified hypotheses evaluated', 'H1 (2 parts), H2, H3, H4, H5, RQ3, confirmatory',
                     f'{len(lines)} lines written to records/hypotheses_results.txt')
    run_checks(step, f'tables, figures and hypothesis decisions for {target}', body, next_step)


# ------------------------------------------------------------------ Step 10.6 / 11
def check_sens():
    def body(lg):
        P = f'{_w("main")}/paper/sensitivity'
        for t in sorted(os.listdir(P)):
            print(f'\n--- {t} ---'); print(open(f'{P}/{t}').read())
        for f, lab in [('sens_ensemble_and_calibration_size.csv', 'ensemble size + calibration size'),
                       ('sens_coverage_level.csv', 'coverage level'), ('sens_model_family_bsim4.csv', 'model family (BSIM4 only)')]:
            lg.check(os.path.exists(f'{P}/{f}'), f'sensitivity analysis: {lab}', 'table written', 'yes' if os.path.exists(f'{P}/{f}') else 'missing',
                     'WARN', fix='run the matching Step 10 cells')
        p = f'{P}/sens_ensemble_and_calibration_size.csv'
        if os.path.exists(p):
            s = pd.read_csv(p)
            for col in ['delta_cov_ens3', 'delta_cov_cal10']:
                if col in s:
                    mx = s[col].abs().max()
                    lg.check(mx <= 0.05, f'largest coverage change ({col})', '<= 0.05 (conclusions robust)', _fmt(mx), 'WARN',
                             fix='not an error: report the sensitivity in the supplement')
    run_checks('10.6', 'sensitivity analyses summary', body, 'Step 11')


def check_export():
    def body(lg):
        z = sorted(glob.glob(f'{ROOT}/exports/MESD_results_*.zip'))
        txt = open(f'{REC}/FINAL_SUMMARY.md').read()
        print(txt); print('export zip:', os.path.relpath(z[-1], ROOT), f'{os.path.getsize(z[-1]) / 2**20:.1f} MB')
        if os.path.exists(f'{REC}/hypotheses_results.txt'):
            print('\n--- hypotheses ---\n' + open(f'{REC}/hypotheses_results.txt').read())
        lg.check('WARNING' not in txt, 'FINAL_SUMMARY warnings', 'none (44 runs per target, non-debug tuning)',
                 'none' if 'WARNING' not in txt else 'see the WARNING lines above')
        st = _status()
        need = ['1', '2', '3', '4', '5', '6', '7', '8']
        bad = {k: st.get(k, {}).get('result', 'NOT RUN') for k in need if not st.get(k, {}).get('result', '').startswith('PASS')}
        lg.check(not bad, 'core steps 1-8 PASSED', 'all PASS', bad or 'all PASS')
        opt = {k: st.get(k, {}).get('result', 'NOT RUN') for k in ['9.8', '10.6']}
        lg.check(all(v.startswith('PASS') for v in opt.values()), 'Cgg (Step 9) and sensitivity (Step 10) finished', 'PASS', opt, 'WARN')
    run_checks('11', 'freeze the results (FINAL_SUMMARY + export zip)', body, 'writing the paper from FINAL_SUMMARY.md')
