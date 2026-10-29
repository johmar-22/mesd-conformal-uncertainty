# Verify the integrity of this repository (and, optionally, of the frozen export zip).
#   1. every file listed in CHECKSUMS.sha256 exists and has the listed SHA-256;
#   2. every file in the repository is listed (nothing was added after the build);
#   3. every compressed file (*.gz) decompresses to the content listed in GZIP_ORIGINALS.sha256;
#   4. code/ and docs/ match code/MANIFEST.sha256 (the manifest the pipeline itself verified in every session);
#   5. with --export <zip>: every member of the frozen export matches the EXPORT_SHA256.txt inside it.
# Usage (from the repository root):  python verification/verify_checksums.py [--export MESD_results_v10_<time>.zip]
# Standard library only.
import argparse, gzip, hashlib, os, sys, zipfile

ap = argparse.ArgumentParser()
ap.add_argument('--root', default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                help='repository root (default: the folder above verification/)')
ap.add_argument('--export', help='path to the frozen export zip of Step 11 (optional; available from the authors)')
a = ap.parse_args()
ROOT = os.path.abspath(a.root)
SKIP_DIRS = {'.git', '__pycache__', '.ipynb_checkpoints', 'mesd_data'}
SELF = {'CHECKSUMS.sha256'}


def sha_file(p):
    h = hashlib.sha256()
    with open(p, 'rb') as fh:
        for b in iter(lambda: fh.read(1 << 20), b''):
            h.update(b)
    return h.hexdigest()


def read_list(p):
    out = {}
    for line in open(p, encoding='utf-8'):
        line = line.rstrip('\n')
        if line and not line.startswith('#'):
            h, rel = line.split('  ', 1)
            out[rel] = h
    return out


fails = []


def report(name, bad, n):
    print(f'[{"PASS" if not bad else "FAIL"}] {name}: {n - len(bad)} of {n} OK')
    for b in bad[:20]:
        print('       ', b)
    if len(bad) > 20:
        print(f'        ... and {len(bad) - 20} more')
    fails.extend(bad)


# 1 + 2: repository checksums
listed = read_list(os.path.join(ROOT, 'CHECKSUMS.sha256'))
bad = [f'{rel}: missing' if not os.path.isfile(os.path.join(ROOT, rel)) else f'{rel}: checksum differs'
       for rel, h in listed.items()
       if not os.path.isfile(os.path.join(ROOT, rel)) or sha_file(os.path.join(ROOT, rel)) != h]
report('CHECKSUMS.sha256', bad, len(listed))
present = set()
for d, dirs, files in os.walk(ROOT):
    dirs[:] = [x for x in dirs if x not in SKIP_DIRS]
    for f in files:
        rel = os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/')
        if rel not in SELF and not f.endswith('.pyc'):
            present.add(rel)
extra = sorted(present - set(listed))
report('no unlisted files', [f'{r}: not in CHECKSUMS.sha256' for r in extra], len(present))

# 3: originals of compressed files
gp = os.path.join(ROOT, 'GZIP_ORIGINALS.sha256')
if os.path.exists(gp):
    orig = read_list(gp)
    bad = []
    for rel, h in orig.items():
        gz = os.path.join(ROOT, rel + '.gz')
        if not os.path.isfile(gz):
            bad.append(f'{rel}.gz: missing')
            continue
        hh = hashlib.sha256()
        with gzip.open(gz, 'rb') as fh:
            for b in iter(lambda: fh.read(1 << 20), b''):
                hh.update(b)
        if hh.hexdigest() != h:
            bad.append(f'{rel}.gz: decompressed content differs from the original')
    report('GZIP_ORIGINALS.sha256', bad, len(orig))

# 4: pipeline manifest
man = read_list(os.path.join(ROOT, 'code', 'MANIFEST.sha256'))
bad = [f'{rel}: missing or changed' for rel, h in man.items()
       if not os.path.isfile(os.path.join(ROOT, rel)) or sha_file(os.path.join(ROOT, rel)) != h]
report('code/MANIFEST.sha256', bad, len(man))

# 5: frozen export zip
if a.export:
    with zipfile.ZipFile(a.export) as z:
        ref = {}
        for line in z.read('EXPORT_SHA256.txt').decode('utf-8').splitlines():
            if line.strip():
                h, rel = line.split('  ', 1)
                ref[rel] = h
        names = set(z.namelist())
        bad = [f'{rel}: missing' if rel not in names else f'{rel}: checksum differs'
               for rel, h in ref.items() if rel not in names or hashlib.sha256(z.read(rel)).hexdigest() != h]
    report(f'export {os.path.basename(a.export)} (EXPORT_SHA256.txt)', bad, len(ref))
    print('        SHA-256 of the zip itself:', sha_file(a.export))

print('ALL CHECKS PASSED' if not fails else f'{len(fails)} PROBLEM(S) FOUND')
sys.exit(1 if fails else 0)
