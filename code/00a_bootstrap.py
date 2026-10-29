# =====================================================================
# MESD project - Step 0.0 bootstrap
# Run at the start of EVERY Colab session (it is quick). Requires BASE from the cell.
#  1. finds the newest execution_plan_mesd_v*_code.zip in MyDrive (or in BASE);
#  2. if it is newer than the installed code (or the installed code was altered),
#     archives the old code to BASE/code_archive/<version>_<time>/, installs the new
#     one, verifies every file against MANIFEST.sha256 and copies the version's
#     CHANGELOG entry into BASE/records/AMENDMENTS.md;
#  3. creates the folder tree, records the runtime (GPU, RAM, package versions) in
#     BASE/records/environment_log.txt and the registry, and prints the next step.
# =====================================================================
import os, re, glob, zipfile, hashlib, shutil, datetime, subprocess, sys, json, importlib

ROOT = BASE.rstrip('/')
MYDRIVE = '/content/drive/MyDrive' if os.path.isdir('/content/drive/MyDrive') else os.path.dirname(ROOT)
_ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
for _d in ['code', 'code_archive', 'docs', 'work/main', 'logs', 'records', 'exports']:
    os.makedirs(f'{ROOT}/{_d}', exist_ok=True)


def _vkey(p):
    return [int(n) for n in re.findall(r'\d+', os.path.basename(p))]


def _sha(p):
    return hashlib.sha256(open(p, 'rb').read()).hexdigest()


def _manifest_ok(folder):
    """Check BASE/code and BASE/docs against code/MANIFEST.sha256 (paths are relative to the zip root)."""
    man = f'{folder}/code/MANIFEST.sha256'
    if not os.path.exists(man):
        return False, ['MANIFEST.sha256 missing']
    bad = []
    for line in open(man):
        h, rel = line.strip().split('  ', 1)
        p = f'{folder}/{rel}'
        if not os.path.exists(p) or _sha(p) != h:
            bad.append(rel)
    return not bad, bad


ZIP_PATTERN = 'execution_plan_mesd_v*_code.zip'      # unique name: never confused with other projects' zips
SIGNATURE = 'code/mesd_common.py'            # a zip counts only if it really is this package


def _prefix(zpath):
    """Folder prefix inside the zip ('' normally; 'name/' if the zip was re-packed with a top folder)."""
    try:
        names = zipfile.ZipFile(zpath).namelist()
    except zipfile.BadZipFile:
        return None
    hit = [n for n in names if n.endswith(SIGNATURE)]
    return hit[0][:-len(SIGNATURE)] if hit else None


cands = sorted(set(glob.glob(f'{MYDRIVE}/{ZIP_PATTERN}') + glob.glob(f'{ROOT}/{ZIP_PATTERN}')), key=_vkey)
zips = [z for z in cands if _prefix(z) is not None]
for z in sorted(set(cands) - set(zips)):
    print(f'ignored (not a valid MESD package zip): {z}')
if not zips:
    raise FileNotFoundError(f'no valid {ZIP_PATTERN} in {MYDRIVE} or {ROOT}: upload the zip to MyDrive (top level, not unzipped)')
newest = zips[-1]
new_ver = 'v' + '.'.join(str(n) for n in _vkey(newest))
inst_ver = open(f'{ROOT}/code/VERSION.txt').read().strip() if os.path.exists(f'{ROOT}/code/VERSION.txt') else None
ok, bad = _manifest_ok(ROOT) if inst_ver else (False, ['not installed'])
print(f'newest zip: {os.path.basename(newest)} ({new_ver}) | installed: {inst_ver or "none"} | installed files intact: {ok}')

if inst_ver != new_ver or not ok:
    reason = 'first install' if inst_ver is None else ('upgrade' if inst_ver != new_ver else f'repair (changed: {bad[:5]})')
    if _vkey(new_ver) < _vkey(inst_ver or 'v0') and inst_ver != new_ver:
        raise RuntimeError(f'installed {inst_ver} is newer than the newest zip {new_ver}: keep the newest zip in MyDrive')
    tmp = f'/tmp/mesd_pkg_{_ts}'
    with zipfile.ZipFile(newest) as z:
        z.extractall(tmp)
    pkg = f'{tmp}/{_prefix(newest)}'.rstrip('/')
    ok_new, bad_new = _manifest_ok(pkg)
    if not ok_new:
        raise RuntimeError(f'the zip {newest} is corrupted or incomplete: {bad_new[:10]} - download/upload it again')
    if inst_ver is not None:                                   # archive the code being replaced
        arch = f'{ROOT}/code_archive/{inst_ver}{"_modified" if not ok else ""}_{_ts}'
        shutil.copytree(f'{ROOT}/code', f'{arch}/code', ignore=shutil.ignore_patterns('__pycache__'))
        if os.path.isdir(f'{ROOT}/docs'):
            shutil.copytree(f'{ROOT}/docs', f'{arch}/docs')
        print('archived previous code ->', arch)
    for sub in ['code', 'docs']:
        shutil.rmtree(f'{ROOT}/{sub}', ignore_errors=True)
        shutil.copytree(f'{pkg}/{sub}', f'{ROOT}/{sub}')
    shutil.rmtree(tmp, ignore_errors=True)
    ok, bad = _manifest_ok(ROOT)
    assert ok, f'installed files do not match the manifest: {bad[:10]}'
    # copy this version's CHANGELOG section into the amendments log
    amd = f'{ROOT}/records/AMENDMENTS.md'
    if not os.path.exists(amd):
        open(amd, 'w').write('# Corrections and amendments log\n\n'
                             'Automatic entries: code-version changes (from docs/CHANGELOG.md), failed steps (OPEN)\n'
                             'and their later successful re-runs (RESOLVED). You may add manual notes at the end.\n\n')
    cl = open(f'{ROOT}/docs/CHANGELOG.md').read()
    m = re.search(rf'(^## {re.escape(new_ver)}(?=[\s(]).*?)(?=^## v|\Z)', cl, flags=re.S | re.M)
    with open(amd, 'a') as fh:
        fh.write(f'## {datetime.datetime.now():%Y-%m-%d %H:%M:%S} | CODE {reason.upper()} | {inst_ver or "-"} -> {new_ver}\n'
                 f'- zip: {os.path.basename(newest)} sha256 {_sha(newest)[:16]}...\n'
                 + (m.group(1).split('\n', 1)[1].strip() + '\n' if m else '- (no CHANGELOG entry found)\n') + '\n')
    with open(f'{ROOT}/records/installed_versions.csv', 'a') as fh:
        if fh.tell() == 0:
            fh.write('time,version,reason,zip,zip_sha256\n')
        fh.write(f'{_ts},{new_ver},{reason.split(" (")[0]},{os.path.basename(newest)},{_sha(newest)}\n')
    print(f'INSTALLED {new_ver} ({reason}); manifest verified')
else:
    print(f'code {inst_ver} already installed and verified; nothing to install')

# ---------------- runtime + package record ----------------
exec(open(f'{ROOT}/code/mesd_common.py').read())
adopt_legacy()        # v3: record checkpoints for outputs that already exist (no recomputation)
publish()             # v7: copy final figures and results to BASE/figures and BASE/results
missing = [p for p in ['numpy', 'pandas', 'pyarrow', 'scipy', 'sklearn', 'matplotlib', 'torch']
           if importlib.util.find_spec(p) is None]
if missing:
    print('installing missing packages:', missing)
    subprocess.run([sys.executable, '-m', 'pip', 'install', '-q'] +
                   [{'sklearn': 'scikit-learn'}.get(p, p) for p in missing], check=True)
vers = {}
for p in ['numpy', 'pandas', 'pyarrow', 'scipy', 'sklearn', 'matplotlib', 'torch']:
    try:
        vers[p] = importlib.import_module(p).__version__
    except Exception as e:
        vers[p] = f'unavailable ({e})'
gpu, ram = runtime_info()
env_line = (f'{_now()} | code {code_version()} | python {sys.version.split()[0]} | GPU {gpu} | RAM {ram} GB | '
            + ' '.join(f'{k}={v}' for k, v in vers.items()))
with open(f'{REC}/environment_log.txt', 'a') as fh:
    fh.write(env_line + '\n')
_registry(dict(start=_now(), end=_now(), minutes=0, step='00_bootstrap', status='OK', code_version=code_version(),
               mesd_commit=mesd_commit(), work_dir='-', settings=json.dumps({'zip': os.path.basename(newest)}),
               gpu=gpu, ram_gb=ram, log_file='records/environment_log.txt', error=''))
print(env_line)
print(f'runtime: GPU = {gpu} | RAM = {ram} GB '
      f'({"High-RAM" if ram == ram and ram > 20 else "standard RAM"})')

# ---------------- progress + next step ----------------
STEPS = [('1', 'build + audit', 'CPU'), ('2', 'features + splits', 'CPU'), ('3', 'tune hyperparameters', 'GPU'),
         ('4', 'smoke test Id', 'CPU/GPU'), ('5', 'train Id (44 runs)', 'GPU'), ('6', 'accuracy gate Id', 'CPU'),
         ('7', 'evaluate Id', 'CPU'), ('8', 'figures + hypotheses Id', 'CPU'), ('9.4', 'smoke test Cgg', 'CPU/GPU'),
         ('9.5', 'train Cgg (44 runs)', 'GPU'), ('9.6', 'accuracy gate Cgg', 'CPU'), ('9.7', 'evaluate Cgg', 'CPU'),
         ('9.8', 'figures Cgg', 'CPU'), ('10.1', 'sensitivity: ensemble size', 'CPU'), ('10.2', 'sensitivity: calibration fraction, train', 'GPU'),
         ('10.3', 'sensitivity: calibration fraction, evaluate', 'CPU'), ('10.4', 'sensitivity: BSIM4 only, train', 'GPU'),
         ('10.5', 'sensitivity: BSIM4 only, evaluate', 'CPU'), ('10.6', 'sensitivity summary', 'CPU'), ('11', 'export', 'CPU')]
try:
    _st = json.load(open(f'{REC}/step_status.json'))
except Exception:
    _st = {}
print('\nprogress (from records/step_status.json):')
for k, name, rt in STEPS:
    res = _st.get(k, {}).get('result', 'not run')
    mark = {'PASS': 'PASS', 'PASS_WITH_WARNINGS': 'PASS*', 'FAIL': 'FAIL'}.get(res, '    ')
    print(f'  [{mark:5s}] Step {k:5s} {name:45s} ({rt})')
todo = [k for k, _, _ in STEPS if not _st.get(k, {}).get('result', '').startswith('PASS')]
print('\nNEXT:', ('Step ' + todo[0]) if todo else 'all steps passed', '| PASS* = passed with warnings | cell list: docs/COLAB_CELLS.txt')
import csv as _csv
if os.path.exists(f'{REC}/run_registry.csv'):
    _last = {}
    for _r in _csv.DictReader(open(f'{REC}/run_registry.csv')):
        _last[_r['step']] = _r['status']
    _open = sorted(k for k, v in _last.items() if v in ('FAILED', 'INTERRUPTED'))
    if _open:
        print('UNRESOLVED (last run failed or was interrupted):', _open, '-> see records/errors.log and records/AMENDMENTS.md')
