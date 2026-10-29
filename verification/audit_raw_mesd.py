# Independent re-check of the dataset facts stated in the paper (Section 3: file counts, curve and point
# counts, charge-conservation failures, model cards) directly from the raw MESD JSON files.
# Written independently of the pipeline (it does not import code/).
# Usage:  git clone https://github.com/SJTU-YONGFU-RESEARCH-GRP/MESD-MOSFET-Electrical-Simulation-Dataset mesd_data
#         git -C mesd_data checkout 5dcc2236ac5b5eeb6228503f544053c2a359b636
#         python verification/audit_raw_mesd.py mesd_data
# Independent re-check of Section 3 claims from the raw MESD JSON at the pinned commit (written fresh, not the pipeline).
import json, glob, os, numpy as np, subprocess, collections
import sys
R = sys.argv[1] if len(sys.argv) > 1 else 'mesd_data'
assert os.path.isdir(os.path.join(R, 'MESD2.0')), f'MESD clone not found at {R}; pass its path as the first argument'
head = subprocess.run(['git', '-C', R, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
print('HEAD', head, subprocess.run(['git', '-C', R, 'log', '-1', '--format=%ci %s'], capture_output=True, text=True).stdout.strip())
F2 = sorted(glob.glob(f'{R}/MESD2.0/*.json')); F1 = sorted(glob.glob(f'{R}/MESD/*.json'))
print('MESD2.0 files', len(F2), '| MESD (v1.0.0 data) files', len(F1))
allj = glob.glob(f'{R}/**/*.json', recursive=True)
print('json files with "-mc" or "mc" in name:', [os.path.basename(f) for f in allj if 'mc' in os.path.basename(f).lower()])
TW = 2 * np.pi * 1e6
FIN = {'N3A', 'N7A', 'N15A'}
tot_pts = tot_cur = 0
fail_files, ratio_rng, hdr, corners_all, temps_all, fam = [], [], [], collections.Counter(), set(), {}
planar = dict(curves=0, points=0, pos=0, devices=set())
fin = dict(curves=0, L=set())
rows = []
for f in F2:
    d = json.load(open(f)); recs = d['Records']; pdk = d['PDK']; dev = d['Device']; key = f'{pdk}-{dev}'
    hdr.append((key, 'Node' in d, d.get('Model', 'MISSING'), d.get('Simulator')))
    s = -1.0 if d['Type'] == 'PMOS' else 1.0
    bad = 0; rat = []
    npts = 0
    for r in recs:
        v = np.asarray(r['Vgs'], float); i = np.asarray(r['Ids'], float); n = len(v); npts += n
        cg = np.abs(np.asarray(r['Cgg'], float)); cs = np.abs(np.asarray(r['Cgs'], float))
        cd = np.abs(np.asarray(r['Cgd'], float)); cb = np.abs(np.asarray(r['Cgb'], float))
        err = np.median(np.abs(cg - (cs + cd + cb)) / np.maximum(cg, 1e-30))
        if err >= 0.05:
            bad += 1
            if n > 2 and abs(r['Vds']) > 0:
                o = np.argsort(v); gm = np.abs(np.gradient(i[o], v[o])); m = gm > 0
                if m.any(): rat.append(np.median(cs[o][m] / (gm[m] / TW)))
        corners_all[(pdk, r['Corner'])] += 1; temps_all.add(r['Temp'])
        if pdk in FIN:
            fin['curves'] += 1; fin['L'].add((pdk, r.get('L')))
        elif key != 'N180A-pmos1' and s * r['Vds'] >= -1e-9:
            planar['curves'] += 1; planar['points'] += n; planar['devices'].add(key)
            planar['pos'] += n if s * r['Vds'] > 1e-9 else 0
    tot_pts += npts; tot_cur += len(recs)
    frac = bad / len(recs)
    rows.append((key, len(recs), npts, round(frac, 3), round(float(np.median(rat)), 3) if rat else None))
    if frac > 0.10:
        fail_files.append(key); ratio_rng.append(np.median(rat))
print('total points', tot_pts, 'curves', tot_cur)
print('files with >10% violating curves:', len(fail_files), '| passing:', sorted(set(k for k, *_ in rows) - set(fail_files)))
print('per-file median Cgs/(gm/2pi f) over failing files: %.3f to %.3f' % (min(ratio_rng), max(ratio_rng)))
print('N55A-nmos1:', [r for r in rows if r[0] == 'N55A-nmos1'])
print('headers without Node:', [h[0] for h in hdr if not h[1]])
print('headers with Model missing/unknown:', [(h[0], h[2]) for h in hdr if h[2] in ('MISSING', '', None, 'unknown')])
print('models by PDK:', sorted(set((h[0].split('-')[0], h[2], h[3]) for h in hdr)))
print('temperatures:', sorted(temps_all))
print('corners by PDK:', sorted(set((p, c) for (p, c) in corners_all)))
print('planar (8 PDKs, excl. N180A-pmos1 and reverse-bias curves): devices', len(planar['devices']), 'curves', planar['curves'],
      'points', planar['points'], 'points Vds>0', planar['pos'])
print('FinFET curves', fin['curves'], '| distinct L per FinFET PDK', collections.Counter(p for p, L in fin['L']))
