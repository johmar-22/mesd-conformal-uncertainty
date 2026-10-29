# =====================================================================
# MESD project - Cell 01: build harmonized long-format table + data audit
# ENGINE script (executed by code/mesd_common.py run_step; never run it directly in Colab)
# Original note: STANDALONE Colab cell (own imports, own Drive mount, own paths).
# Output (in Drive): MESD_project/mesd_long.parquet, audit_per_file.csv
# Runtime: ~1-3 min on a standard Colab CPU runtime (1.4 GB clone + parse; tested: 50 s).
# =====================================================================
import os, json, glob, subprocess
import numpy as np
import pandas as pd

# ---------- paths / Drive ----------
# ---------- paths: set by code/mesd_common.py run_step() (no Drive mount here) ----------
WORK = os.environ.get('MESD_WORK', os.path.abspath('./MESD_project'))   # outputs of this step
DATA = os.environ.get('MESD_DATA', WORK)                                # fallback location of inputs
os.makedirs(WORK, exist_ok=True)
BASE = WORK
def inp(name):
    """Input file: taken from WORK if it exists there, otherwise from DATA."""
    p = os.path.join(WORK, name)
    return p if os.path.exists(p) else os.path.join(DATA, name)
# clone to the Colab LOCAL disk (much faster than Drive); only the parquet/csv outputs go to Drive
CLONE = os.environ.get('MESD_CLONE', '/content/mesd_repo' if os.path.isdir('/content') else os.path.abspath('./mesd_repo'))

REPO = 'https://github.com/SJTU-YONGFU-RESEARCH-GRP/MESD-MOSFET-Electrical-Simulation-Dataset.git'
# Pin the exact dataset version used for the study (commit "add cgs cgb cgd", 26 Dec 2025, which created MESD2.0).
# If the authors later fix or extend the data, the study stays reproducible; report this hash in the paper.
PINNED_COMMIT = '5dcc2236ac5b5eeb6228503f544053c2a359b636'
if not os.path.isdir(CLONE):
    subprocess.run(['git', 'clone', '--depth', '1', REPO, CLONE], check=True)
head = subprocess.run(['git', '-C', CLONE, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
if head != PINNED_COMMIT:
    print(f'repository HEAD {head[:7]} differs from pinned {PINNED_COMMIT[:7]}: fetching pinned commit')
    subprocess.run(['git', '-C', CLONE, 'fetch', '--depth', '1', 'origin', PINNED_COMMIT], check=True)
    subprocess.run(['git', '-C', CLONE, 'checkout', '--quiet', PINNED_COMMIT], check=True)
print('MESD commit in use:', subprocess.run(['git', '-C', CLONE, 'rev-parse', 'HEAD'],
                                          capture_output=True, text=True).stdout.strip())
DATA_DIR = os.path.join(CLONE, 'MESD2.0')  # MESD2.0 = MESD + Cgs/Cgd/Cgb fields

TWO_PI_F = 2 * np.pi * 1e6                 # AC frequency stated in the descriptor (1 MHz)
FINFET_PDKS = {'N3A', 'N7A', 'N15A'}

def node_from_pdk(pdk):                    # 'N45B' -> 45 (Node key is missing in some files)
    return int(''.join(c for c in pdk if c.isdigit()))

blocks, audit = [], []
files = sorted(glob.glob(os.path.join(DATA_DIR, '*.json')))
assert len(files) == 44, f'expected 44 files, found {len(files)}'

for f in files:
    d = json.load(open(f))
    R = d.get('Records', d.get('Record'))
    pdk, dev, typ = d['PDK'], d['Device'], d['Type']
    is_p = (typ == 'PMOS')
    s = -1.0 if is_p else 1.0             # harmonize PMOS to NMOS-like polarity
    node = d.get('Node', node_from_pdk(pdk))
    model = d.get('Model', 'unknown')
    cols = {k: [] for k in ['cid', 'W', 'L', 'Nfin', 'corner', 'T', 'vds', 'vgs', 'id',
                            'cgg', 'cgs', 'cgd', 'cgb', 'capok', 'rev']}
    n_cons_bad = n_cgs_big = n_rev = 0
    ratios = []
    for cid, r in enumerate(R):
        Vgs = np.asarray(r['Vgs'], float); Ids = np.asarray(r['Ids'], float)
        Cgg = np.abs(np.asarray(r['Cgg'], float)); Cgs = np.abs(np.asarray(r['Cgs'], float))
        Cgd = np.abs(np.asarray(r['Cgd'], float)); Cgb = np.abs(np.asarray(r['Cgb'], float))
        n = len(Vgs); vds = float(r['Vds'])
        rev = (s * vds) < -1e-9            # e.g. N180A-pmos1 has Vds=+0.3 V (reverse bias for PMOS)
        n_rev += int(rev)
        # charge conservation check: Cgg = Cgs + Cgd + Cgb
        cons_err = np.abs(Cgg - (Cgs + Cgd + Cgb)) / np.maximum(Cgg, 1e-30)
        cap_ok = bool(np.median(cons_err) < 0.05)
        n_cons_bad += int(not cap_ok)
        n_cgs_big += int(np.any(Cgs > 1.5 * Cgg))
        # hypothesis test: invalid Cgs equals gm / (2*pi*f)
        if (not cap_ok) and n > 2 and abs(vds) > 0:
            o = np.argsort(Vgs)
            gm = np.abs(np.gradient(Ids[o], Vgs[o])); m = gm > 0
            if m.any():
                ratios.append(np.median(Cgs[o][m] / (gm[m] / TWO_PI_F)))
        for k, v in (('cid', cid), ('W', r.get('W')), ('L', r.get('L')), ('Nfin', r.get('Nfin')),
                     ('corner', r['Corner']), ('T', r['Temp']), ('vds', s * vds),
                     ('capok', cap_ok), ('rev', rev)):
            cols[k].append(np.repeat(np.nan if v is None else v, n))
        cols['vgs'].append(s * Vgs); cols['id'].append(np.abs(Ids))
        cols['cgg'].append(Cgg); cols['cgs'].append(Cgs); cols['cgd'].append(Cgd); cols['cgb'].append(Cgb)
    C = {k: np.concatenate(v) for k, v in cols.items()}
    blk = pd.DataFrame({
        'pdk': pdk, 'node_nm': node, 'model': model, 'device': dev, 'type': typ,
        'family': 'FinFET' if pdk in FINFET_PDKS else 'planar',
        'curve_idx': C['cid'].astype(np.int32),
        'W_nm': C['W'].astype(float), 'L_nm': C['L'].astype(float), 'Nfin': C['Nfin'].astype(float),
        'corner': C['corner'], 'T_C': C['T'].astype(np.int16),
        'Vds_eff': C['vds'], 'Vgs_eff': C['vgs'], 'Id_A': C['id'],
        'Cgg_F': C['cgg'], 'Cgs_F': C['cgs'], 'Cgd_F': C['cgd'], 'Cgb_F': C['cgb'],
        'cap_terminal_valid': C['capok'].astype(bool), 'reverse_bias': C['rev'].astype(bool),
    })
    blk['curve_id'] = pdk + '-' + dev + '-' + blk['curve_idx'].astype(str)
    blocks.append(blk)
    audit.append(dict(file=os.path.basename(f), pdk=pdk, node_nm=node, model=model, type=typ,
                      n_curves=len(R), n_points=len(blk),
                      frac_cap_conservation_violated=round(n_cons_bad / len(R), 3),
                      frac_Cgs_gt_1p5_Cgg=round(n_cgs_big / len(R), 3),
                      median_Cgs_over_gm_div_omega=(round(float(np.median(ratios)), 3) if ratios else np.nan),
                      n_reverse_bias_curves=n_rev))
    del d, R
    print('parsed', os.path.basename(f), len(blk))

df = pd.concat(blocks, ignore_index=True); del blocks
for c in ['pdk', 'model', 'device', 'type', 'family', 'corner', 'curve_id']:
    df[c] = df[c].astype('category')

aud = pd.DataFrame(audit)
df.to_parquet(os.path.join(BASE, 'mesd_long.parquet'), index=False)
aud.to_csv(os.path.join(BASE, 'audit_per_file.csv'), index=False)

# ---------- summary ----------
print(f'rows (bias points): {len(df):,} | curves: {df.curve_id.nunique():,}')
print(df.groupby('pdk', observed=True).agg(curves=('curve_id', 'nunique'), points=('Id_A', 'size'),
      corners=('corner', 'nunique'), temps=('T_C', 'nunique')).sort_values('curves'))
print('\nFiles whose terminal caps (Cgs/Cgd) violate charge conservation in >10% of curves:',
      (aud.frac_cap_conservation_violated > 0.10).sum(), 'of', len(aud))
print('Median ratio Cgs / (gm/2*pi*f) over violating curves (1.0 => Cgs field is a gm artifact):')
print(aud[['file', 'frac_cap_conservation_violated', 'median_Cgs_over_gm_div_omega']].to_string(index=False))
mc_present = any('-mc' in os.path.basename(f) for f in glob.glob(os.path.join(CLONE, '**', '*.json'), recursive=True))
print('\nMonte Carlo files present:', mc_present)
commit = subprocess.run(['git', '-C', CLONE, 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
with open(os.path.join(BASE, 'dataset_flags.json'), 'w') as fh:      # read by the Step 1 check log
    json.dump(dict(commit=commit, mc_present=bool(mc_present), n_json=len(files), n_rows=int(len(df)),
                   n_curves=int(df.curve_id.nunique())), fh, indent=2)
