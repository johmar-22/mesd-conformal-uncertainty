# ===================================================================================================
# MESD study: assemble the public GitHub repository from the project folder on Drive, check it, push it,
# and publish the release.
# Normally started by the short launcher cell in the instructions (it reads this file from
# MyDrive/mesd_repo_kit.zip and passes MODE and GITHUB_OWNER in OVERRIDES). It can also be pasted whole
# into a cell; then edit the settings below.
#   MODE = 'dry_run'  builds /content/repo_build/tree, runs every check, pushes nothing;
#   MODE = 'push'     builds again and commits + pushes to GitHub (creates the repository if missing);
#   MODE = 'release'  creates release RELEASE_TAG on GitHub (switch the repository on in Zenodo BEFORE
#                     this step if you want a DOI).
# Nothing on Drive is modified; the cell only reads BASE and the kit zip.
# ===================================================================================================
from google.colab import drive; drive.mount('/content/drive')
BASE = '/content/drive/MyDrive/mesd_v1'
KIT_ZIP = '/content/drive/MyDrive/mesd_repo_kit.zip'

# ---------------- settings ----------------
MODE = 'dry_run'                    # 'dry_run' | 'push' | 'release'
GITHUB_OWNER = 'YOUR_GITHUB_USERNAME'
REPO_NAME = 'mesd-conformal-uncertainty'
VISIBILITY = 'private'              # used only if the cell creates the repository; make it public on GitHub later
BRANCH = 'main'
RELEASE_TAG = 'v1.0.0'
ZENODO_DOI = ''                     # e.g. '10.5281/zenodo.1234567' after the first release; '' = not yet
COMMIT_MESSAGE = 'Code v10, check logs, figure data and frozen results of the MESD conformal study'
GIT_NAME, GIT_EMAIL = 'Johaimen M. Omar', ''   # GIT_EMAIL '' = GitHub's private no-reply address of GITHUB_OWNER
EXPORT_ZIP = ''                     # '' = newest BASE/exports/MESD_results_<code version>_*.zip
ATTACH_EXPORT_ZIP = False           # True = also attach the frozen export zip to the release. It contains the
                                    # internal working documents of the project (docs/ as on Drive), so the
                                    # default is False; its SHA-256 is recorded in the repository either way.
GZIP_ABOVE_MB = 45                  # files larger than this are committed gzip-compressed (GitHub warns at 50 MB)
EXCLUDE_FILES = []                  # paths to leave out, e.g. ['records/AMENDMENTS.md'] (never edited, only omitted)
ALLOW_RESULTS_NOT_IN_EXPORT = False # True only if you deliberately changed a result file after Step 11

if 'OVERRIDES' in globals():        # settings passed by the launcher cell
    globals().update(OVERRIDES)

import os, re, io, glob, gzip, json, shutil, hashlib, zipfile, subprocess, datetime, base64, urllib.request, urllib.error

assert MODE in ('dry_run', 'push', 'release'), MODE
assert GITHUB_OWNER.strip() and GITHUB_OWNER.lower() not in ('your_github_username', 'your-github-username'), \
    'set GITHUB_OWNER to your GitHub user name (the name in https://github.com/<name>)'
assert os.path.isdir(BASE), f'{BASE} not found'
WORKDIR = '/content/repo_build'
TREE = f'{WORKDIR}/tree'           # the assembled repository content
GITDIR = f'{WORKDIR}/{REPO_NAME}'  # the git working copy that is committed and pushed
LOG = []


def say(msg=''):
    print(msg); LOG.append(msg)


def sha_bytes(b):
    return hashlib.sha256(b).hexdigest()


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def rel(p, root):
    return os.path.relpath(p, root).replace(os.sep, '/')


# ---------------- GitHub API helpers (token never printed, never written to disk) ----------------
TOKEN = None
if MODE != 'dry_run':
    from google.colab import userdata
    TOKEN = userdata.get('GITHUB_TOKEN')
    assert TOKEN, 'Colab secret GITHUB_TOKEN is empty'


def api(method, url, data=None, ctype='application/json', ok=(200, 201)):
    body = json.dumps(data).encode() if (data is not None and ctype == 'application/json') else data
    req = urllib.request.Request(url, data=body, method=method, headers={
        'Authorization': f'Bearer {TOKEN}', 'Accept': 'application/vnd.github+json',
        'X-GitHub-Api-Version': '2022-11-28', 'Content-Type': ctype, 'User-Agent': 'mesd-repo-builder'})
    try:
        with urllib.request.urlopen(req, timeout=600) as r:
            txt = r.read().decode() or '{}'
            return r.status, json.loads(txt)
    except urllib.error.HTTPError as e:
        txt = e.read().decode()
        if e.code in ok:
            return e.code, json.loads(txt or '{}')
        return e.code, (json.loads(txt) if txt.startswith('{') else {'message': txt})


def git(*args, cwd=None, auth=False, check=True):
    cmd = ['git']
    if auth:   # token passed as a one-off header, so it is not stored in .git/config
        b64 = base64.b64encode(f'x-access-token:{TOKEN}'.encode()).decode()
        cmd += ['-c', f'http.extraheader=AUTHORIZATION: basic {b64}']
    r = subprocess.run(cmd + list(args), cwd=cwd, capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(f'git {args[0]} failed: {(r.stderr or r.stdout).replace(TOKEN or "@@", "***")[-1500:]}')
    return r.stdout.strip()


REMOTE = f'https://github.com/{GITHUB_OWNER}/{REPO_NAME}.git'
API_REPO = f'https://api.github.com/repos/{GITHUB_OWNER}/{REPO_NAME}'

# =================================================================================================
# 1. Code and docs: verify against the pipeline's own manifest
# =================================================================================================
say(f'# MESD repository build | {datetime.datetime.now():%Y-%m-%d %H:%M:%S} | mode {MODE}')
manifest = {}
for line in open(f'{BASE}/code/MANIFEST.sha256'):
    h, r_ = line.strip().split('  ', 1)
    manifest[r_] = h
bad = [r_ for r_, h in manifest.items() if not os.path.isfile(f'{BASE}/{r_}') or sha_file(f'{BASE}/{r_}') != h]
assert not bad, f'code/docs on Drive do not match code/MANIFEST.sha256: {bad}'
CODE_VER = open(f'{BASE}/code/VERSION.txt').read().strip()
say(f'[PASS] code {CODE_VER}: all {len(manifest)} files of code/ and docs/ on Drive match code/MANIFEST.sha256')
CODE_FILES = sorted(r_ for r_ in manifest if r_.startswith('code/'))
extra_code = sorted(rel(p, BASE) for p in glob.glob(f'{BASE}/code/**/*', recursive=True)
                    if os.path.isfile(p) and '__pycache__' not in p and rel(p, BASE) not in manifest
                    and rel(p, BASE) != 'code/MANIFEST.sha256')
assert not extra_code, f'files in code/ not covered by the manifest (remove them or reinstall v10): {extra_code}'

# =================================================================================================
# 2. Frozen export: verify the zip against its own EXPORT_SHA256.txt; collect its hashes
# =================================================================================================
if not EXPORT_ZIP:
    cands = sorted(glob.glob(f'{BASE}/exports/MESD_results_{CODE_VER}_*.zip'))
    assert cands, f'no export zip for {CODE_VER} in {BASE}/exports (run Step 11 first)'
    EXPORT_ZIP = cands[-1]
EXPORT_SHA = sha_file(EXPORT_ZIP)
with zipfile.ZipFile(EXPORT_ZIP) as z:
    ref = {}
    for line in z.read('EXPORT_SHA256.txt').decode().splitlines():
        if line.strip():
            h, r_ = line.split('  ', 1)
            ref[r_] = h
    bad = [r_ for r_, h in ref.items() if sha_bytes(z.read(r_)) != h]
assert not bad, f'the export zip is damaged: {bad[:10]}'
EXPORT_HASHES = {}
for r_, h in ref.items():
    EXPORT_HASHES.setdefault(h, []).append(r_)
say(f'[PASS] export {os.path.basename(EXPORT_ZIP)}: {len(ref)} files match its EXPORT_SHA256.txt | '
    f'{os.path.getsize(EXPORT_ZIP) / 2**20:.1f} MB | sha256 {EXPORT_SHA}')

# =================================================================================================
# 3. Assemble the tree
# =================================================================================================
shutil.rmtree(TREE, ignore_errors=True); os.makedirs(TREE)
copied = []   # (repo path, source path)


def put(src, dst_rel):
    dst = f'{TREE}/{dst_rel}'
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.copy2(src, dst)
    copied.append((dst_rel, src))


def put_dir(sub, exclude=()):
    for p in sorted(glob.glob(f'{BASE}/{sub}/**/*', recursive=True)):
        r_ = rel(p, BASE)
        if os.path.isfile(p) and '__pycache__' not in r_ and not any(re.search(x, r_) for x in exclude):
            if r_ in EXCLUDE_FILES:
                say(f'[INFO] left out on request: {r_}')
                continue
            put(p, r_)


for r_ in CODE_FILES:                       # the code exactly as run (docs/ comes from the kit, see below)
    put(f'{BASE}/{r_}', r_)
for sub in ('results', 'figures', 'records', 'logs'):
    put_dir(sub, exclude=(r'\.pyc$',))
WORK_FILES = ['work/main/tuning.json', 'work/main/tuning_log.csv', 'work/main/anchors.csv',
              'work/main/audit_per_file.csv', 'work/main/dataset_flags.json']
for r_ in WORK_FILES:
    if os.path.isfile(f'{BASE}/{r_}'):
        put(f'{BASE}/{r_}', r_)
    else:
        say(f'[WARN] {r_} not found on Drive (skipped)')
for sub in ('main', 'sens_cal10', 'sens_bsim4'):
    for p in sorted(glob.glob(f'{BASE}/work/{sub}/preds/*/train_log.jsonl')):
        put(p, rel(p, BASE))

# static kit (README, licences, colab/, verification/, ...), with placeholders filled in
assert os.path.isfile(KIT_ZIP), f'{KIT_ZIP} not found: upload mesd_repo_kit.zip to MyDrive'
with zipfile.ZipFile(KIT_ZIP) as z:
    names = [n for n in z.namelist() if not n.endswith('/')]
    pre = os.path.commonprefix(names) if len(names) > 1 else ''
    pre = pre[:pre.rfind('/') + 1] if '/' in pre else ''
    for n in names:
        r_ = n[len(pre):]
        if not r_ or '__pycache__' in r_ or r_.endswith('.pyc'):
            continue
        assert not os.path.exists(f'{TREE}/{r_}'), f'kit file {r_} would overwrite a project file'
        os.makedirs(os.path.dirname(f'{TREE}/{r_}') or TREE, exist_ok=True)
        open(f'{TREE}/{r_}', 'wb').write(z.read(n))
        copied.append((r_, f'kit:{n}'))
assert os.path.isfile(f'{TREE}/docs/CHANGELOG.md'), 'the kit has no docs/CHANGELOG.md (the bootstrap needs it)'
# code/MANIFEST.sha256 for the published package: the code entries are the ones the pipeline verified in
# every session (unchanged); the docs entries cover the documentation files published here.
pub_docs = sorted(rel(p, TREE) for p in glob.glob(f'{TREE}/docs/**/*', recursive=True) if os.path.isfile(p))
for r_ in CODE_FILES:
    assert sha_file(f'{TREE}/{r_}') == manifest[r_], f'{r_} differs from the manifest entry'
open(f'{TREE}/code/MANIFEST.sha256', 'w').write(''.join(f'{manifest[r_]}  {r_}\n' for r_ in CODE_FILES)
                                                + ''.join(f'{sha_file(f"{TREE}/{r_}")}  {r_}\n' for r_ in pub_docs))
copied.append(('code/MANIFEST.sha256', 'generated'))
say(f'[PASS] code/MANIFEST.sha256 written: {len(CODE_FILES)} code files (hashes as run) + {len(pub_docs)} published docs')
doi_line = (f'[![DOI](https://zenodo.org/badge/DOI/{ZENODO_DOI}.svg)](https://doi.org/{ZENODO_DOI})  '
            f'Archived release: <https://doi.org/{ZENODO_DOI}>' if ZENODO_DOI else
            'Archived release (Zenodo DOI): to be added after the first release.')
FILL = {'{{GITHUB_OWNER}}': GITHUB_OWNER, '{{REPO_NAME}}': REPO_NAME, '{{RELEASE_TAG}}': RELEASE_TAG,
        '{{EXPORT_ZIP_NAME}}': os.path.basename(EXPORT_ZIP), '{{EXPORT_ZIP_SHA256}}': EXPORT_SHA,
        '{{EXPORT_N_FILES}}': str(len(ref)), '{{DOI_LINE}}': doi_line, '{{DOI_CFF}}': (f'doi: "{ZENODO_DOI}"\n' if ZENODO_DOI else '')}
for r_ in ('README.md', 'CITATION.cff', 'colab/00_setup_from_github.py'):
    p = f'{TREE}/{r_}'
    s = open(p, encoding='utf-8').read()
    for k, v in FILL.items():
        s = s.replace(k, v)
    left = re.findall(r'\{\{[A-Z_0-9]+\}\}', s)
    assert not left, f'unfilled placeholders in {r_}: {left}'
    open(p, 'w', encoding='utf-8').write(s)
say(f'[PASS] assembled {len(copied)} files in {TREE}')
PAPER_FIGS = {'figures/architecture/fig_architecture.png': 'fig2_architecture_cell.py',
              'figures/paper_combined/fig3_lopo_and_curve_coverage.png': 'fig4_fig5_side_by_side_cell.py',
              'figures/paper_combined/fig4_recalibration_budget_Id_Cgg.png': 'fig4_fig5_side_by_side_cell.py',
              'figures/paper_combined/fig6_recalibration_width.png': 'fig6_recalibration_width_cell.py'}
miss = [f'{f} (run colab/paper_figures/{c} first)' for f, c in PAPER_FIGS.items()
        if not all(os.path.isfile(f'{TREE}/{f[:-4]}{e}') for e in ('.png', '.pdf'))]
assert not miss, 'paper figures missing on Drive: ' + '; '.join(miss)
say(f'[PASS] all {len(PAPER_FIGS)} paper-specific figures present (PNG + PDF)')

# =================================================================================================
# 4. Provenance: is every result file byte-identical to a file in the frozen export?
# =================================================================================================
prov = []   # (repo path, status, export path)
stop = []
for r_, src in copied:
    if src.startswith('kit:') or r_.startswith(('code/', 'docs/')):
        continue
    h = sha_file(f'{TREE}/{r_}')
    if h in EXPORT_HASHES:
        prov.append((r_, 'identical to export', EXPORT_HASHES[h][0]))
        continue
    same_path = r_ in ref
    if r_.startswith('figures/') and re.search(r'/(architecture|paper_combined)/', r_):
        status = 'made after Step 11 by colab/paper_figures (from frozen data)'
    elif same_path:
        status = 'CHANGED since the export (same path, different content)'
    else:
        status = 'not in export'
    prov.append((r_, status, r_ if same_path else ''))
    if os.path.getsize(f'{TREE}/{r_}') <= 2:
        prov[-1] = (r_, 'empty placeholder file', prov[-1][2])
    elif (r_.startswith('results/') and re.search(r'\.(csv|txt|md|json)$', r_)
          and os.path.basename(r_) != 'README.txt'):
        stop.append(f'{r_}: {status}')
n_id = sum(s == 'identical to export' for _, s, _ in prov)
say(f'[INFO] provenance: {n_id} of {len(prov)} data/log/figure files are byte-identical to a file in the frozen export')
for r_, s, e in prov:
    if s != 'identical to export':
        say(f'        {s:<62} {r_}')
if stop and not ALLOW_RESULTS_NOT_IN_EXPORT:
    raise SystemExit('STOP: these result files differ from the frozen export (paper numbers must come from it):\n  '
                     + '\n  '.join(stop) + '\nInvestigate before publishing (set ALLOW_RESULTS_NOT_IN_EXPORT only if intended).')
say('[PASS] every result table/text file is byte-identical to the frozen export' if not stop else
    f'[WARN] {len(stop)} result files differ from the export (ALLOW_RESULTS_NOT_IN_EXPORT=True)')

# =================================================================================================
# 5. Large files -> deterministic gzip; checksums; build report
# =================================================================================================
gz_orig = []
for r_, _ in list(copied):
    p = f'{TREE}/{r_}'
    if os.path.isfile(p) and os.path.getsize(p) > GZIP_ABOVE_MB * 2**20:
        h = sha_file(p)
        with open(p, 'rb') as fi, open(p + '.gz', 'wb') as fo:
            with gzip.GzipFile(filename='', mode='wb', fileobj=fo, mtime=0, compresslevel=9) as gz:
                shutil.copyfileobj(fi, gz)
        say(f'[INFO] compressed {r_} ({os.path.getsize(p) / 2**20:.1f} MB) -> {r_}.gz ({os.path.getsize(p + ".gz") / 2**20:.1f} MB)')
        os.remove(p)
        gz_orig.append(f'{h}  {r_}')
if gz_orig:
    open(f'{TREE}/GZIP_ORIGINALS.sha256', 'w').write(
        '# SHA-256 of the original (uncompressed) content of every .gz file; path = file without .gz\n'
        + '\n'.join(gz_orig) + '\n')

report = [f'# How this repository was built', '',
          f'- built: {datetime.date.today():%Y-%m-%d} by `colab/build_and_push_repo.py` from the project folder `mesd_v1` on Google Drive',
          f'- code version: {CODE_VER}; the {len(CODE_FILES)} files in `code/` are byte-identical to the files that produced the results '
          '(SHA-256 equal to the entries of the manifest verified by the pipeline in every session); `code/MANIFEST.sha256` '
          'lists them and the documentation files in `docs/`',
          f'- frozen export of Step 11: `{os.path.basename(EXPORT_ZIP)}` ({len(ref)} files, verified against its `EXPORT_SHA256.txt`), '
          f'SHA-256 `{EXPORT_SHA}`',
          f'- {n_id} of {len(prov)} files in results/, figures/, records/, logs/ and work/ are byte-identical to a file in the frozen export.',
          '- Files that differ are listed below. Records and logs keep growing after the export (every later Colab session adds',
          '  a bootstrap line to `records/run_registry.csv` and `records/environment_log.txt`); the paper figures in',
          '  `figures/architecture/` and `figures/paper_combined/` were drawn after the export from frozen data.',
          f'- files larger than {GZIP_ABOVE_MB} MB are stored gzip-compressed; `GZIP_ORIGINALS.sha256` holds the hash of their original content.',
          '', '| file | status | counterpart in the export |', '|---|---|---|']
report += [f'| `{r_}` | {s} | {("`" + e + "`") if e else ""} |' for r_, s, e in prov if s != 'identical to export']
report += ['', '<details><summary>Byte-identical files and their path in the export</summary>', '',
           '| file | path in the export |', '|---|---|']
report += [f'| `{r_}` | `{e}` |' for r_, s, e in prov if s == 'identical to export']
report += ['', '</details>', '']
open(f'{TREE}/REPO_BUILD_REPORT.md', 'w').write('\n'.join(report) + '\n')

allf = sorted(rel(os.path.join(d, f), TREE) for d, _, fs in os.walk(TREE) for f in fs)
allf = [f for f in allf if f != 'CHECKSUMS.sha256']
open(f'{TREE}/CHECKSUMS.sha256', 'w').write(''.join(f'{sha_file(f"{TREE}/{f}")}  {f}\n' for f in allf))

sizes = sorted(((os.path.getsize(f'{TREE}/{f}'), f) for f in allf), reverse=True)
total = sum(s for s, _ in sizes)
say(f'[INFO] {len(allf) + 1} files, {total / 2**20:.1f} MB; largest: ' +
    ', '.join(f'{f} {s / 2**20:.1f} MB' for s, f in sizes[:3]))
assert sizes[0][0] < 95 * 2**20, 'a file is too large for GitHub (100 MB limit)'
warn50 = [f for s, f in sizes if s > 50 * 2**20]
if warn50:
    say(f'[WARN] files above 50 MB (GitHub warns, still accepted): {warn50}')

r = subprocess.run(['python', f'{TREE}/verification/verify_checksums.py', '--root', TREE, '--export', EXPORT_ZIP],
                   capture_output=True, text=True)
say(r.stdout.strip())
assert r.returncode == 0, 'verify_checksums.py failed on the assembled tree'
say(f'[PASS] verification/verify_checksums.py passed on the assembled tree')

# =================================================================================================
# 6. Push
# =================================================================================================
if MODE == 'dry_run':
    say(f'\nDRY RUN finished: nothing pushed. The repository content is in {TREE} (Colab file browser).')
elif MODE == 'push':
    st, info = api('GET', API_REPO, ok=(200,))
    if st == 404:
        st, info = api('POST', 'https://api.github.com/user/repos', {
            'name': REPO_NAME, 'private': VISIBILITY == 'private', 'auto_init': False,
            'description': 'Conformal uncertainty intervals for neural MOSFET models under shift: code, check logs and frozen results'})
        assert st == 201, f'could not create the repository ({st}): {info.get("message")}. Create it on github.com (empty, no README) and rerun.'
        say(f'[INFO] created repository {GITHUB_OWNER}/{REPO_NAME} ({VISIBILITY})')
    else:
        assert st == 200, f'cannot read {API_REPO} ({st}): {info.get("message")} (check GITHUB_OWNER, REPO_NAME and the token)'
        say(f'[INFO] repository exists ({"private" if info.get("private") else "public"})')
    shutil.rmtree(GITDIR, ignore_errors=True)
    has_branch = bool(git('ls-remote', '--heads', REMOTE, BRANCH, auth=True))
    if has_branch:
        git('clone', '--quiet', '--branch', BRANCH, REMOTE, GITDIR, auth=True)
        for x in os.listdir(GITDIR):          # replace the content, keep the history
            if x != '.git':
                (shutil.rmtree if os.path.isdir(f'{GITDIR}/{x}') else os.remove)(f'{GITDIR}/{x}')
    else:
        os.makedirs(GITDIR); git('init', '--quiet', '-b', BRANCH, cwd=GITDIR)
        git('remote', 'add', 'origin', REMOTE, cwd=GITDIR)
    shutil.copytree(TREE, GITDIR, dirs_exist_ok=True)
    email = GIT_EMAIL
    if not email:            # GitHub's private no-reply address, so the commit is linked to the account
        st, me = api('GET', 'https://api.github.com/user', ok=(200,))
        email = (f"{me['id']}+{me['login']}@users.noreply.github.com" if st == 200 and 'id' in me
                 else f'{GITHUB_OWNER}@users.noreply.github.com')
    git('config', 'user.name', GIT_NAME, cwd=GITDIR); git('config', 'user.email', email, cwd=GITDIR)
    git('config', 'core.autocrlf', 'false', cwd=GITDIR)
    git('add', '-A', cwd=GITDIR)
    ignored = git('ls-files', '--others', '--ignored', '--exclude-standard', cwd=GITDIR)
    assert not ignored, f'.gitignore would drop files listed in CHECKSUMS.sha256: {ignored.splitlines()[:10]}'
    if not git('status', '--porcelain', cwd=GITDIR):
        say('[INFO] nothing changed since the last push')
    else:
        git('commit', '--quiet', '-m', COMMIT_MESSAGE, cwd=GITDIR)
        git('push', '--quiet', 'origin', BRANCH, cwd=GITDIR, auth=True)
        say(f'[PASS] pushed commit {git("rev-parse", "--short", "HEAD", cwd=GITDIR)} to {REMOTE} ({BRANCH})')
    say(f'Check the repository on https://github.com/{GITHUB_OWNER}/{REPO_NAME}')

# =================================================================================================
# 7. Release with the frozen export zip as asset
# =================================================================================================
elif MODE == 'release':
    st, rel_info = api('GET', f'{API_REPO}/releases/tags/{RELEASE_TAG}', ok=(200,))
    if st == 404:
        st, br = api('GET', f'{API_REPO}/branches/{BRANCH}', ok=(200,))
        assert st == 200, f'branch {BRANCH} not found: run MODE = "push" first'
        st, rel_info = api('POST', f'{API_REPO}/releases', {
            'tag_name': RELEASE_TAG, 'target_commitish': BRANCH, 'name': f'{RELEASE_TAG}: code {CODE_VER} and frozen results',
            'body': (f'Code {CODE_VER}, check logs, figure data and frozen results of the MESD conformal-uncertainty study.\n\n'
                     'Verify the files with `python verification/verify_checksums.py` (see README, Section 3).'),
            'draft': False, 'prerelease': False})
        assert st == 201, f'release not created ({st}): {rel_info.get("message")}'
        say(f'[PASS] created release {RELEASE_TAG}')
    else:
        say(f'[INFO] release {RELEASE_TAG} already exists')
    assets = {a['name'] for a in rel_info.get('assets', [])}
    an = os.path.basename(EXPORT_ZIP)
    if not ATTACH_EXPORT_ZIP:
        say('[INFO] export zip not attached (ATTACH_EXPORT_ZIP = False)')
    elif an in assets:
        say(f'[INFO] asset {an} already attached')
    else:
        up = rel_info['upload_url'].split('{')[0] + f'?name={an}'
        st, ai = api('POST', up, data=open(EXPORT_ZIP, 'rb').read(), ctype='application/zip')
        assert st == 201, f'asset upload failed ({st}): {ai.get("message")}'
        say(f'[PASS] attached {an} ({ai["size"] / 2**20:.1f} MB)')
    say(f'Release page: https://github.com/{GITHUB_OWNER}/{REPO_NAME}/releases/tag/{RELEASE_TAG}')
    say('If Zenodo is switched on for this repository, the DOI appears on zenodo.org within minutes. Write it in '
        "ZENODO_DOI (in OVERRIDES of the launcher cell) and run once more with MODE 'push' to add it to README.md and CITATION.cff.")
