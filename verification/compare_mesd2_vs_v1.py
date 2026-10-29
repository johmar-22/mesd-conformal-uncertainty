# Compares I_D and C_gg in MESD2.0/ (used here) with MESD/ (identical to release tag v1.0.0) at the
# pinned commit, for the 8 planar PDKs (paper Section 3: agreement within 1e-4 relative, except N45A C_gg).
# Written independently of the pipeline (it does not import code/).
# Usage:  git clone https://github.com/SJTU-YONGFU-RESEARCH-GRP/MESD-MOSFET-Electrical-Simulation-Dataset mesd_data
#         git -C mesd_data checkout 5dcc2236ac5b5eeb6228503f544053c2a359b636
#         python verification/compare_mesd2_vs_v1.py mesd_data
import json, glob, os, numpy as np
import sys
R = sys.argv[1] if len(sys.argv) > 1 else 'mesd_data'
assert os.path.isdir(os.path.join(R, 'MESD2.0')), f'MESD clone not found at {R}; pass its path as the first argument'
P = {'N40A','N45A','N45B','N55A','N90A','N180A','N180B','N350A'}
print('file | Ids: max rel diff over points with |Vds|>0 and |Id|>1e-15 (count >1e-4) | Cgg: max rel diff (count >1e-4)')
for f2 in sorted(glob.glob(f'{R}/MESD2.0/*.json')):
    b = os.path.basename(f2); 
    if b.split('-')[0] not in P: continue
    r2 = json.load(open(f2))['Records']; r1 = json.load(open(f'{R}/MESD/{b}'))['Records']
    mi = ci = 0.0; ni = nc = 0; ex = None
    for a, c in zip(r1, r2):
        x, y = np.abs(np.asarray(a['Ids'], float)), np.abs(np.asarray(c['Ids'], float))
        m = (abs(a['Vds']) > 0) & (x > 1e-15) & (y > 1e-15)
        if m.any():
            rel = np.abs(x[m] - y[m]) / x[m]; 
            if rel.max() > mi: mi = rel.max(); ex = (a['Vds'], a['Temp'], a['Corner'], x[m][rel.argmax()], y[m][rel.argmax()])
            ni += (rel > 1e-4).sum()
        x, y = np.abs(np.asarray(a['Cgg'], float)), np.abs(np.asarray(c['Cgg'], float))
        rel = np.abs(x - y) / np.maximum(x, 1e-300); ci = max(ci, rel.max()); nc += (rel > 1e-4).sum()
    print(f'{b:18s} Ids {mi:.1e} ({ni})  Cgg {ci:.1e} ({nc})  worst Ids example {ex}')
