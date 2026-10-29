# ===================================================================================================
# MESD study: first cell when rerunning the study from the GitHub repository (replaces Step 0.0a).
# STANDALONE Colab cell (any runtime, about 1 minute). Paste the whole file into one cell and run it.
#
# What it does:
#   1. mounts Google Drive and clones the repository (release tag below);
#   2. checks code/ and docs/ against code/MANIFEST.sha256;
#   3. packs code/ and docs/ into MyDrive/execution_plan_mesd_<version>_code.zip, the package format the
#      pipeline's bootstrap installs from, and checks the zip against the manifest as well;
#   4. runs the bootstrap (Step 0.0), which installs the code into BASE/code and prints the next step.
# Afterwards, start every session with Step 0.0 and follow docs/COLAB_CELLS.txt (README, Section 4.3).
# ===================================================================================================
from google.colab import drive; drive.mount('/content/drive')
BASE = '/content/drive/MyDrive/mesd_v1'            # all outputs go here; change it to keep runs apart
REPO_URL = 'https://github.com/johmar-22/mesd-conformal-uncertainty.git'
TAG = 'v1.0.0'                            # the release used for the paper; 'main' for the latest commit

import os, glob, hashlib, shutil, subprocess, zipfile

CLONE = '/content/mesd_code_repo'
shutil.rmtree(CLONE, ignore_errors=True)
subprocess.run(['git', 'clone', '--quiet', '--depth', '1', '--branch', TAG, REPO_URL, CLONE], check=True)
print('cloned', REPO_URL, 'at', TAG, '->', subprocess.run(['git', '-C', CLONE, 'rev-parse', 'HEAD'],
                                                          capture_output=True, text=True).stdout.strip())


def sha(b):
    return hashlib.sha256(b).hexdigest()


manifest = {}
for line in open(f'{CLONE}/code/MANIFEST.sha256'):
    h, rel = line.strip().split('  ', 1)
    manifest[rel] = h
bad = [rel for rel, h in manifest.items()
       if not os.path.isfile(f'{CLONE}/{rel}') or sha(open(f'{CLONE}/{rel}', 'rb').read()) != h]
assert not bad, f'files in the clone do not match code/MANIFEST.sha256: {bad}'
print(f'manifest: all {len(manifest)} files of code/ and docs/ verified')

ver = open(f'{CLONE}/code/VERSION.txt').read().strip()
zpath = f'/content/drive/MyDrive/execution_plan_mesd_{ver}_code.zip'
if os.path.exists(zpath):                          # keep an existing package zip of the same version
    bak = zpath[:-4] + '_backup_' + __import__('datetime').datetime.now().strftime('%Y%m%d_%H%M%S') + '.zip.bak'
    os.rename(zpath, bak)
    print('existing', os.path.basename(zpath), 'renamed to', os.path.basename(bak), '(the bootstrap ignores it)')
with zipfile.ZipFile(zpath, 'w', zipfile.ZIP_DEFLATED) as z:
    for sub in ('code', 'docs'):
        for p in sorted(glob.glob(f'{CLONE}/{sub}/**/*', recursive=True)):
            if os.path.isfile(p) and '__pycache__' not in p:
                z.write(p, os.path.relpath(p, CLONE))
with zipfile.ZipFile(zpath) as z:
    bad = [rel for rel, h in manifest.items() if rel not in z.namelist() or sha(z.read(rel)) != h]
assert not bad, f'the new zip does not match the manifest: {bad}'
print('package written and verified:', zpath)

others = [p for p in glob.glob('/content/drive/MyDrive/execution_plan_mesd_v*_code.zip') if p != zpath]
if others:
    print('WARNING: other package zips in MyDrive; the bootstrap installs the one with the highest version:', others)
if os.path.isdir(f'{BASE}/work'):
    print(f'WARNING: {BASE} already holds a run; checkpoints there will be reused. Use a new BASE for a clean rerun.')

# Step 0.0a: take the bootstrap from the zip and run it
os.makedirs(f'{BASE}/code', exist_ok=True)
with zipfile.ZipFile(zpath) as z:
    open(f'{BASE}/code/00a_bootstrap.py', 'wb').write(z.read('code/00a_bootstrap.py'))
exec(open(f'{BASE}/code/00a_bootstrap.py').read())
