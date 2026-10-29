# =====================================================================
# MESD project - common runner (executed inside every Step cell)
# Requires the notebook variable BASE (set in the cell, e.g. '/content/drive/MyDrive/mesd_v1').
# What it guarantees for EVERY step:
#   * the engine script runs in its own namespace (no clutter in the notebook);
#   * everything printed goes to the screen AND to  BASE/logs/<step>_<timestamp>.log;
#   * one row per run is appended to  BASE/records/run_registry.csv
#     (start, end, minutes, status, code version, MESD commit, GPU, RAM, settings, log file);
#   * on failure the full traceback is appended to  BASE/records/errors.log  and an
#     OPEN entry is added to  BASE/records/AMENDMENTS.md ; the next successful run of
#     the same step appends a RESOLVED line, so the correction history is complete.
# =====================================================================
import os, sys, time, json, csv, traceback, datetime, subprocess, gc

ROOT = BASE.rstrip('/')
import pandas as _pd
_pd.set_option('display.max_columns', None); _pd.set_option('display.width', 250); _pd.set_option('display.max_rows', 500)
CODE, ENGINE = f'{ROOT}/code', f'{ROOT}/code/engine'
WORKROOT, LOGS, REC = f'{ROOT}/work', f'{ROOT}/logs', f'{ROOT}/records'
for _d in (WORKROOT, LOGS, REC, f'{ROOT}/exports'):
    os.makedirs(_d, exist_ok=True)


def _now():
    return datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')


def code_version():
    p = f'{CODE}/VERSION.txt'
    return open(p).read().strip() if os.path.exists(p) else 'unknown'


def mesd_commit():
    p = f'{REC}/mesd_commit.txt'
    return open(p).read().strip() if os.path.exists(p) else 'not-yet-recorded'


def runtime_info():
    """GPU name and total RAM of the current Colab runtime."""
    gpu = 'none'
    try:
        out = subprocess.run(['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                             capture_output=True, text=True, timeout=20)
        if out.returncode == 0 and out.stdout.strip():
            gpu = out.stdout.strip().splitlines()[0]
    except Exception:
        pass
    ram = float('nan')
    try:
        with open('/proc/meminfo') as fh:
            ram = int(fh.readline().split()[1]) / 2**20
    except Exception:
        pass
    return gpu, round(ram, 1)


class _Tee:
    def __init__(self, *streams):
        self.streams = streams
    def write(self, s):
        for st in self.streams:
            try:
                st.write(s)
            except Exception:
                pass
        return len(s)
    def flush(self):
        for st in self.streams:
            try:
                st.flush()
            except Exception:
                pass
    def isatty(self):
        return False


REG_COLS = ['start', 'end', 'minutes', 'step', 'status', 'code_version', 'mesd_commit', 'work_dir',
            'settings', 'gpu', 'ram_gb', 'log_file', 'error']


def _registry(row):
    p = f'{REC}/run_registry.csv'
    new = not os.path.exists(p)
    with open(p, 'a', newline='') as fh:
        w = csv.DictWriter(fh, fieldnames=REG_COLS)
        if new:
            w.writeheader()
        w.writerow({k: row.get(k, '') for k in REG_COLS})


def _amend(text):
    p = f'{REC}/AMENDMENTS.md'
    if not os.path.exists(p):
        open(p, 'w').write('# Corrections and amendments log\n\n'
                           'Automatic entries: code-version changes (from docs/CHANGELOG.md), failed steps (OPEN)\n'
                           'and their later successful re-runs (RESOLVED). You may add manual notes at the end.\n\n')
    with open(p, 'a') as fh:
        fh.write(text.rstrip() + '\n\n')


def _open_failures(step):
    p = f'{REC}/run_registry.csv'
    if not os.path.exists(p):
        return False
    rows = list(csv.DictReader(open(p)))
    st = [r['status'] for r in rows if r['step'] == step]
    return bool(st) and st[-1] in ('FAILED', 'INTERRUPTED')


def need(paths, hint):
    """Stop early with a clear message when an input of this step is missing."""
    miss = [p for p in paths if not os.path.exists(p)]
    if miss:
        raise FileNotFoundError(f'missing input(s): {miss}\n  -> {hint}')


EXPECTED_RUNS = 12 if os.environ.get('MESD_DEBUG') == '1' else 44   # 12 only in the developer's CPU test


def require_gpu(step):
    gpu, _ = runtime_info()
    if gpu == 'none' and os.environ.get('MESD_ALLOW_CPU') == '1':      # developer test hook only
        print(f'WARNING: {step} running on CPU (MESD_ALLOW_CPU=1)'); return
    if gpu == 'none':
        raise RuntimeError(f'{step} needs a GPU runtime: Runtime > Change runtime type > GPU (T4/L4/A100), '
                           'then re-run Step 0.0 and this cell. Nothing was written.')


def _run_engine(step, engine, work='main', data='main', env=None):
    """Run code/engine/<engine> with logging, registry and error records."""
    env = {k: str(v) for k, v in (env or {}).items()}
    wdir, ddir = f'{WORKROOT}/{work}', f'{WORKROOT}/{data}'
    os.makedirs(wdir, exist_ok=True)
    full = {'MESD_ROOT': ROOT, 'MESD_WORK': wdir, 'MESD_DATA': ddir, **env}
    old = {k: os.environ.get(k) for k in full}
    os.environ.update(full)
    ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    log_file = f'{LOGS}/{step}_{ts}.log'
    gpu, ram = runtime_info()
    row = dict(start=_now(), step=step, code_version=code_version(), mesd_commit=mesd_commit(),
               work_dir=os.path.relpath(wdir, ROOT), settings=json.dumps(env), gpu=gpu, ram_gb=ram,
               log_file=os.path.relpath(log_file, ROOT))
    path = f'{ENGINE}/{engine}'
    src = open(path).read()
    t0, status, err = time.time(), 'OK', ''
    so, se = sys.stdout, sys.stderr
    fh = open(log_file, 'w', buffering=1)
    sys.stdout, sys.stderr = _Tee(so, fh), _Tee(se, fh)
    try:
        print(f'=== {step} | engine {engine} | code {row["code_version"]} | MESD {row["mesd_commit"][:12]} ===')
        print(f'start {row["start"]} | work {wdir} | settings {env or "default"} | GPU {gpu} | RAM {ram} GB')
        ns = {'__name__': '__mesd_step__', '__file__': path}
        exec(compile(src, path, 'exec'), ns)
        del ns
    except BaseException as e:
        status = 'INTERRUPTED' if isinstance(e, KeyboardInterrupt) else 'FAILED'
        err = f'{type(e).__name__}: {e}'.replace('\n', ' | ')[:500]
        tb = traceback.format_exc()
        print(tb)
        with open(f'{REC}/errors.log', 'a') as ef:
            ef.write(f'\n===== {_now()} | {step} | {status} | code {row["code_version"]} | log {row["log_file"]}\n{tb}')
        print(f'\n{"=" * 30} PASTE-BACK FAILURE REPORT: {step} {"=" * 30}\n'
              f'code {row["code_version"]} | MESD {row["mesd_commit"][:12]} | GPU {gpu} | RAM {ram} GB | settings {env or "default"}\n'
              f'error: {err}\nfull log: {row["log_file"]} (also in records/errors.log)\n'
              f'Copy the WHOLE cell output above (including the traceback) and paste it back.\n{"=" * 80}')
        _amend(f'## {_now()} | OPEN | {step} {status}\n- code version: {row["code_version"]}\n'
               f'- error: {err}\n- log: {row["log_file"]} (traceback also in records/errors.log)\n'
               f'- action: send the log to the analyst; fix arrives as a new execution_plan_mesd_v*_code.zip')
        raise
    finally:
        sys.stdout, sys.stderr = so, se
        fh.close()
        for k, v in old.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        row.update(end=_now(), minutes=round((time.time() - t0) / 60, 2), status=status, error=err)
        if step.startswith('step1_build_audit') and status == 'OK':
            c = subprocess.run(['git', '-C', os.environ.get('MESD_CLONE', '/content/mesd_repo'), 'rev-parse', 'HEAD'],
                               capture_output=True, text=True).stdout.strip()
            if c:
                open(f'{REC}/mesd_commit.txt', 'w').write(c + '\n')
                row['mesd_commit'] = c
        if status == 'OK' and _open_failures(step):
            _amend(f'## {_now()} | RESOLVED | {step}\n- re-run succeeded with code version {row["code_version"]} '
                   f'(log: {row["log_file"]})')
        _registry(row)
        gc.collect()
        try:                                       # hand freed memory back to the OS (long Colab sessions)
            import ctypes
            ctypes.CDLL('libc.so.6').malloc_trim(0)
        except Exception:
            pass
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass
    print(f'\n{step}: {status} in {row["minutes"]} min | log -> {row["log_file"]} | registry -> records/run_registry.csv')


def show_pngs(folder, names=None):
    """Display saved figures inline (Agg backend saves files only)."""
    try:
        from IPython.display import Image, display
    except ImportError:
        return
    for n in sorted(os.listdir(folder)):
        if n.endswith('.png') and (names is None or any(k in n for k in names)):
            print(n)
            display(Image(filename=os.path.join(folder, n), width=700))


# paste-back report functions (report_01, report_02, ...)
exec(open(f'{CODE}/mesd_report.py').read())


# =====================================================================
# CHECKPOINTS (v3): a step is re-computed ONLY when something it depends on changed.
# fingerprint = hash of (engine code without comments/formatting, settings, fingerprints of the
# upstream steps). Stored in records/fingerprints.json. If the outputs exist and the fingerprint is
# unchanged, the step is skipped and its outputs are reused. If an amendment changes the engine code
# or an upstream result, the old outputs are moved to <work>/_superseded/ and the step re-runs.
# Training and evaluation are checkpointed per run / per prediction file inside the engines.
# Outputs that existed before v3 (no fingerprint yet) are adopted once, never silently recomputed.
# =====================================================================
import ast, hashlib, shutil
FP_FILE = f'{REC}/fingerprints.json'


def _fps():
    try:
        return json.load(open(FP_FILE))
    except Exception:
        return {}


def _save_fp(key, fp, note=''):
    d = _fps()
    d[key] = dict(fp=fp, time=_now(), code_version=code_version(), note=note)
    json.dump(d, open(FP_FILE, 'w'), indent=2)


def code_fp(*engines):
    h = hashlib.sha256()
    for e in engines:
        h.update(ast.dump(ast.parse(open(f'{ENGINE}/{e}').read())).encode())   # comments/formatting ignored
    return h.hexdigest()[:16]


def step_fp(engines, upstream=(), settings=None):
    d = _fps()
    miss = [u for u in upstream if u not in d]
    if miss:
        raise RuntimeError(f'checkpoint(s) {miss} not recorded yet: run the cell of the step that produces them '
                           '(Step 1 -> build, Step 2 -> splits:main, Step 3 -> tune, Step 5 -> train:main:y_logId, ...). '
                           'If the outputs already exist it only records them; nothing is recomputed.')
    parts = [code_fp(*engines)] + [d[u]['fp'] for u in upstream] + \
            [json.dumps({k: str(v) for k, v in (settings or {}).items()}, sort_keys=True)]
    return hashlib.sha256('|'.join(parts).encode()).hexdigest()[:16]


def ckpt_decide(key, fp, wdir, outputs):
    """'reuse' (same fingerprint), 'adopt' (pre-v3 outputs), or 'run' (missing or amended; old outputs archived)."""
    have = all(os.path.exists(f'{wdir}/{o}') for o in outputs)
    stored = _fps().get(key)
    if have and stored is None:
        _save_fp(key, fp, note='adopted existing outputs (created before checkpoint tracking)')
        print(f'CHECKPOINT [{key}]: existing outputs ADOPTED (made before v3; fingerprint {fp} recorded, nothing recomputed)')
        return 'adopt'
    if have and stored['fp'] == fp:
        print(f'CHECKPOINT [{key}]: outputs REUSED - nothing changed since {stored["time"]} (code {stored["code_version"]}, fingerprint {fp})')
        return 'reuse'
    if have:
        dst = f'{wdir}/_superseded/{key.replace(":", "_")}_{datetime.datetime.now():%Y%m%d_%H%M%S}'
        os.makedirs(dst, exist_ok=True)
        for o in outputs:
            if os.path.exists(f'{wdir}/{o}'):
                shutil.move(f'{wdir}/{o}', f'{dst}/{os.path.basename(o)}')
        print(f'CHECKPOINT [{key}]: an amendment changed this step (fingerprint {stored["fp"]} -> {fp}); '
              f'old outputs moved to {os.path.relpath(dst, ROOT)} and the step is re-computed')
        _amend(f'## {_now()} | RECOMPUTE | {key}\n- fingerprint {stored["fp"]} -> {fp} (code {code_version()})\n'
               f'- previous outputs archived in {os.path.relpath(dst, ROOT)}')
    return 'run'


HELPERS = {'mesd_05_figures_tables.py': ['figstyle.py']}     # helper modules that are part of an engine's code


def run_step(step, engine, work='main', data='main', env=None, key=None, upstream=(), outputs=None):
    """Run an engine with checkpointing. key=None -> always run (no checkpoint)."""
    env = dict(env or {})
    if key is None:
        return _run_engine(step, engine, work, data, env)
    fp = step_fp([engine] + HELPERS.get(engine, []), upstream, dict(env, work=work))
    env['MESD_FP'] = fp
    old = _fps().get(key)
    if not outputs and old and old['fp'] != fp:
        print(f'CHECKPOINT [{key}]: an amendment changed this step (fingerprint {old["fp"]} -> {fp}); '
              'affected runs/files are recomputed, old ones are kept in _superseded/')
        _amend(f'## {_now()} | RECOMPUTE | {key}\n- fingerprint {old["fp"]} -> {fp} (code {code_version()})\n'
               '- outdated per-run outputs moved to _superseded/ by the engine')
    if outputs:
        act = ckpt_decide(key, fp, f'{WORKROOT}/{work}', outputs)
        if act in ('reuse', 'adopt'):
            _registry(dict(start=_now(), end=_now(), minutes=0, step=step, status='SKIPPED_CHECKPOINT',
                           code_version=code_version(), mesd_commit=mesd_commit(), work_dir=work,
                           settings=json.dumps({k: str(v) for k, v in env.items()}), gpu=runtime_info()[0],
                           ram_gb=runtime_info()[1], log_file='-', error=act))
            return act
    _run_engine(step, engine, work, data, env)
    _save_fp(key, fp)
    return 'run'


def run_smoke(target, work, step_prefix):
    """Smoke test (train 2 epochs on 3% -> evaluate -> figures) with a checkpoint: re-run only if the
    training, evaluation or figure code, or the splits, changed since the last smoke test."""
    eng = ['mesd_03_train_models.py', 'mesd_04_conformal_eval.py', 'mesd_05_figures_tables.py']
    key = f'smoke:{target}'
    fp = step_fp(eng + ['figstyle.py'], ['splits:main'], {'target': target, 'debug': 1})
    outs = [f'results/{target}/results_long.csv', f'paper/{target}/table2_coverage_alpha0.10.csv']
    if ckpt_decide(key, fp, f'{WORKROOT}/{work}', outs) in ('reuse', 'adopt'):
        return
    shutil.rmtree(f'{WORKROOT}/{work}', ignore_errors=True)          # a smoke test always starts clean
    env = {'MESD_TARGET': target}
    _run_engine(f'{step_prefix}_smoke_train', eng[0], work=work, env=dict(env, MESD_DEBUG=1))
    _run_engine(f'{step_prefix}_smoke_eval', eng[1], work=work, env=env)
    _run_engine(f'{step_prefix}_smoke_figures', eng[2], work=work, env=env)
    _save_fp(key, fp)


# ------------------------------------------------------------------ v7: Drive folders figures/ and results/
FIGDIR, RESDIR = f'{ROOT}/figures', f'{ROOT}/results'
TARGET_NAME = {'y_logId': 'Id', 'y_logCgg': 'Cgg'}


def _mirror(pairs, dest):
    """Copy (src, name) pairs into dest; files in dest that are not in the set are removed, so dest
    always equals the CURRENT outputs (old versions stay in work/<...>/_superseded/). Unchanged files
    (same size and time) are not copied again. Returns the number of files in dest."""
    import shutil
    os.makedirs(dest, exist_ok=True)
    want = {}
    for src, name in pairs:
        if os.path.isfile(src):
            want[name] = src
    for f in os.listdir(dest):
        if f not in want and f != 'README.txt' and os.path.isfile(f'{dest}/{f}'):
            os.remove(f'{dest}/{f}')
    for name, src in want.items():
        d = f'{dest}/{name}'
        st = os.stat(src)
        if not (os.path.exists(d) and os.path.getsize(d) == st.st_size and int(os.path.getmtime(d)) == int(st.st_mtime)):
            shutil.copy2(src, d)
    return len(want)


def publish(verbose=True):
    """Copy every FINAL figure (PNG + PDF) to  BASE/figures/<Id|Cgg>/  and every final result
    (paper tables, figure data, figure audit, per-run results, curve checks, hypotheses, sensitivity
    tables, final summary) to  BASE/results/...  Smoke tests are never copied (their numbers mean
    nothing). The originals stay in work/ (that is where the checkpoints live); these two folders are
    plain copies, refreshed by every check log, so you can open or download them directly."""
    import glob
    W = f'{WORKROOT}/main'
    out = []
    for t, nm in TARGET_NAME.items():
        P, R = f'{W}/paper/{t}', f'{W}/results/{t}'
        figs = [(f, os.path.basename(f)) for e in ('png', 'pdf') for f in glob.glob(f'{P}/*.{e}')]
        if figs:
            out.append((f'figures/{nm}', _mirror(figs, f'{FIGDIR}/{nm}')))
        res = [(f, os.path.basename(f)) for f in glob.glob(f'{P}/*.csv')]
        res += [(f'{R}/{f}', f) for f in ('results_long.csv', 'curve_checks.csv')]
        if t == 'y_logId':
            res.append((f'{REC}/hypotheses_results.txt', 'hypotheses_results.txt'))
        if any(os.path.isfile(a) for a, _ in res):
            out.append((f'results/{nm}', _mirror(res, f'{RESDIR}/{nm}')))
    sens = [(f, os.path.basename(f)) for f in glob.glob(f'{W}/paper/sensitivity/*')]
    for w in ('sens_cal10', 'sens_bsim4'):
        for t, nm in TARGET_NAME.items():
            sens.append((f'{WORKROOT}/{w}/results/{t}/results_long.csv', f'{w}_{nm}_results_long.csv'))
    if any(os.path.isfile(a) for a, _ in sens):
        out.append(('results/sensitivity', _mirror(sens, f'{RESDIR}/sensitivity')))
    if os.path.isfile(f'{REC}/FINAL_SUMMARY.md'):
        out.append(('results/summary', _mirror([(f'{REC}/FINAL_SUMMARY.md', 'FINAL_SUMMARY.md')], f'{RESDIR}/summary')))
    for d, txt in [(FIGDIR, 'Final paper figures (600 dpi PNG + vector PDF), one folder per target (Id, Cgg).'),
                   (RESDIR, 'Final results: paper tables, figure data, figure audit, per-run results (results_long.csv),\n'
                            'curve checks, hypothesis decisions, sensitivity tables and the final summary.')]:
        if os.path.isdir(d):
            open(f'{d}/README.txt', 'w').write(txt + '\nThese are COPIES refreshed automatically by every step cell. The originals '
                                               '(and the checkpoints) are in work/main/; superseded versions in work/main/_superseded/.\n'
                                               'Do not edit files here; they are overwritten.\n')
    if verbose and out:
        print('copied to Drive: ' + ' | '.join(f'{ROOT}/{d} ({n} files)' for d, n in out))
    return out


def adopt_legacy():
    """Record fingerprints for outputs made before checkpoint tracking (v1/v2), without recomputing."""
    W = f'{WORKROOT}/main'
    chain = [('build', 'mesd_01_build_and_audit.py', (), ['mesd_long.parquet', 'audit_per_file.csv', 'dataset_flags.json']),
             ('splits:main', 'mesd_02_features_and_splits.py', ('build',), ['model_table.parquet', 'splits.parquet', 'anchors.csv']),
             ('tune', 'mesd_03a_tune_hyperparameters.py', ('splits:main',), ['tuning.json', 'tuning_log.csv'])]
    for key, eng, up, outs in chain:
        d = _fps()
        if key in d or not all(os.path.exists(f'{W}/{o}') for o in outs) or any(u not in d for u in up):
            continue
        _save_fp(key, step_fp([eng], up, {'work': 'main'}), note='adopted existing outputs (created before checkpoint tracking)')
        print(f'CHECKPOINT [{key}]: existing outputs adopted (made before v3; nothing recomputed)')
