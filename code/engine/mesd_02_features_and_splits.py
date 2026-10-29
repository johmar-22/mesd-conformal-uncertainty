# =====================================================================
# MESD project - Cell 02: modelling table, device anchors, shift splits
# ENGINE script (executed by code/mesd_common.py run_step; never run it directly in Colab)
# Original note: STANDALONE Colab cell. Needs: MESD_project/mesd_long.parquet (Cell 01).
# Output: MESD_project/model_table.parquet, MESD_project/splits.parquet,
#         MESD_project/anchors.csv
# Runtime: ~1-2 min on CPU.
# ---------------------------------------------------------------------
# Design decisions (see proposal, section "Data and split protocol"):
#  * Main study = 8 planar PDKs (FinFET subset is too small, 4,250 curves).
#  * Target 1 = log10(Id) for Vds > 0 (Vds = 0 rows have Id ~ 0 by physics).
#  * Target 2 = log10(Cgg) (Cgs/Cgd excluded: gm/(2*pi*f) artefact).
#  * Each device (PDK x device flavour) gets 3 ANCHOR descriptors taken
#    from ONE reference curve (tt, 25 C, middle W, middle L, Vds = VDD):
#    Vth_ref (constant-current, 100 nA * W/L), log10 Ion_ref, log10 Ioff_ref.
#    These mimic "a few measured points on a new device" and let the model
#    tell device flavours apart without a device ID (needed for held-out PDKs).
#  * All reference-geometry curves (same W, L, 25 C, tt; every Vds) are
#    tagged 'anchor' and are NEVER used for calibration or testing.
#  * Splits are by whole curve (Vgs sweep), never by point.
#  * N180A-pmos1 is EXCLUDED: in 100% of its curves |Id| falls as |Vgs| rises and the
#    curve labelled Vds = -1.8 V carries zero current, i.e. its bias labels are offset
#    (audit finding 6). All other 35 planar devices pass this check.
# =====================================================================
import os, gc
import numpy as np
import pandas as pd

# ---------- paths: set by code/mesd_common.py run_step() (no Drive mount here) ----------
WORK = os.environ.get('MESD_WORK', os.path.abspath('./MESD_project'))   # outputs of this step
DATA = os.environ.get('MESD_DATA', WORK)                                # fallback location of inputs
os.makedirs(WORK, exist_ok=True)
BASE = WORK
def inp(name):
    """Input file: taken from WORK if it exists there, otherwise from DATA."""
    p = os.path.join(WORK, name)
    return p if os.path.exists(p) else os.path.join(DATA, name)

SEEDS = [0, 1, 2, 3, 4]
CAL_FRAC = float(os.environ.get('MESD_CAL_FRAC', '0.20'))         # fraction of training-side curves held out for conformal calibration
S0_TEST_FRAC = 0.20
I_FLOOR = 1e-15          # A; floor before log10 (numerical-noise level of the simulator)
EXCLUDE_DEVICES = {'N180A-pmos1'}

LONG_COLS = ['pdk', 'node_nm', 'model', 'device', 'type', 'family', 'W_nm', 'L_nm', 'corner', 'T_C',
             'Vds_eff', 'Vgs_eff', 'Id_A', 'Cgg_F', 'reverse_bias', 'curve_id']   # only what is used (memory)
df = pd.read_parquet(inp('mesd_long.parquet'), columns=LONG_COLS)
df = df[(df.family == 'planar') & (~df.reverse_bias)].copy()
for c in ['pdk', 'device', 'type', 'corner', 'model', 'curve_id']:
    df[c] = df[c].astype(str)
df['dev_key'] = df.pdk + '-' + df.device
df = df[~df.dev_key.isin(EXCLUDE_DEVICES)].copy()
# Sensitivity 'model family control' (plan Step 10): keep only the listed PDKs, e.g. the BSIM4 PDKs
PDK_KEEP = [p for p in os.environ.get('MESD_PDK_KEEP', '').split(',') if p]
if PDK_KEEP:
    df = df[df.pdk.isin(PDK_KEEP)].copy()
    print('PDK_KEEP (model-family sensitivity):', PDK_KEEP)

# ---------- grid indices of W and L per device (grids are log-spaced, 10 values) ----------
for col in ['W_nm', 'L_nm']:
    df[col[0] + '_idx'] = df.groupby('dev_key')[col].rank(method='dense').astype(int) - 1

# ---------- device anchors from one reference curve ----------
def vth_cc(vgs, idd, icrit):
    """Constant-current Vth by log-linear interpolation; NaN if not crossed."""
    o = np.argsort(vgs); v, i = vgs[o], np.log10(np.maximum(idd[o], I_FLOOR))
    t = np.log10(icrit)
    k = np.where((i[:-1] < t) & (i[1:] >= t))[0]
    if len(k) == 0:
        return np.nan
    k = k[0]
    return v[k] + (t - i[k]) * (v[k + 1] - v[k]) / (i[k + 1] - i[k])

anchors, anchor_curves = [], set()
for dk, g in df.groupby('dev_key'):
    corner_ref = 'tt' if 'tt' in set(g.corner) else sorted(set(g.corner))[0]
    wi = int(np.median(np.unique(g.W_idx))); li = int(np.median(np.unique(g.L_idx)))
    ref = g[(g.corner == corner_ref) & (g.T_C == 25) & (g.W_idx == wi) & (g.L_idx == li)]
    vdd = g.Vds_eff.max()
    cur = ref[np.isclose(ref.Vds_eff, vdd)]
    W, Lg = cur.W_nm.iloc[0], cur.L_nm.iloc[0]
    v, i = cur.Vgs_eff.values, cur.Id_A.values
    anchors.append(dict(dev_key=dk, Vdd=vdd, W_ref=W, L_ref=Lg,
                        Vth_ref=vth_cc(v, i, 1e-7 * W / Lg),
                        lIon_ref=np.log10(max(i[np.argmax(v)], I_FLOOR)),
                        lIoff_ref=np.log10(max(i[np.argmin(np.abs(v))], I_FLOOR))))
    anchor_curves |= set(ref.curve_id)
anc = pd.DataFrame(anchors)
assert anc.Vth_ref.notna().all(), anc[anc.Vth_ref.isna()]
anc.to_csv(os.path.join(BASE, 'anchors.csv'), index=False)
df = df.merge(anc, on='dev_key', how='left')
df['is_anchor'] = df.curve_id.isin(anchor_curves)

# ---------- features ----------
df['lW'] = np.log10(df.W_nm); df['lL'] = np.log10(df.L_nm); df['lNode'] = np.log10(df.node_nm)
df['Tn'] = df.T_C / 100.0
df['corner_o'] = df.corner.map({'ss': -1.0, 'tt': 0.0, 'ff': 1.0})
df['is_p'] = (df.type == 'PMOS').astype(float)
df['Vgs_n'] = df.Vgs_eff / df.Vdd; df['Vds_n'] = df.Vds_eff / df.Vdd
df['Vov'] = df.Vgs_eff - df.Vth_ref                       # overdrive w.r.t. the device anchor
df['region'] = np.where(df.Vov < 0, 'sub', 'above')      # input-only region label (no target leakage)
df['y_logId'] = np.log10(np.maximum(df.Id_A, I_FLOOR))
df['y_logCgg'] = np.log10(np.maximum(df.Cgg_F, 1e-21))
df['valid_Id'] = df.Vds_eff > 1e-9

keep = ['curve_id', 'dev_key', 'pdk', 'device', 'type', 'model', 'node_nm', 'corner', 'T_C',
        'W_nm', 'L_nm', 'W_idx', 'L_idx', 'Vgs_eff', 'Vds_eff', 'Id_A', 'Cgg_F',
        'lW', 'lL', 'lNode', 'Tn', 'corner_o', 'is_p', 'Vgs_n', 'Vds_n', 'Vov', 'Vdd',
        'Vth_ref', 'lIon_ref', 'lIoff_ref', 'region', 'y_logId', 'y_logCgg', 'valid_Id', 'is_anchor']
df[keep].to_parquet(os.path.join(BASE, 'model_table.parquet'), index=False)

# ---------- curve-level split definitions ----------
cur = df.groupby('curve_id').agg(pdk=('pdk', 'first'), T_C=('T_C', 'first'), corner=('corner', 'first'),
                                 L_idx=('L_idx', 'first'), is_anchor=('is_anchor', 'first')).reset_index()
pdks = sorted(cur.pdk.unique())
n_planar_rows = len(df)
del df; gc.collect()                    # free ~4 GB before building the split table (pandas 2.x uses much more RAM)

def assign(test_mask, seed):
    """Return role per curve: train / cal / test / unused. Anchors -> train (never cal/test)."""
    rng = np.random.default_rng(seed)
    role = np.where(test_mask, 'test', 'train').astype(object)
    role[cur.is_anchor.values & test_mask] = 'unused'      # anchor curves never tested
    tr = np.where((role == 'train') & (~cur.is_anchor.values))[0]
    cal = rng.choice(tr, size=int(CAL_FRAC * len(tr)), replace=False)
    role[cal] = 'cal'
    return role

# Memory-lean split table: categorical columns with fixed categories (same random draws as before).
CID = pd.Categorical(cur.curve_id.astype(str))
ROLES = ['train', 'cal', 'test', 'unused']
SCN = ['S0_random', 'S1_Lextreme', 'S2_T125', 'S3_ff', 'S4_LOPO']
FOLDS = ['all'] + list(pdks)

def piece(name, fold, seed, role):
    n = len(cur)
    return pd.DataFrame({'curve_id': CID,
                         'scenario': pd.Categorical.from_codes(np.full(n, SCN.index(name), np.int8), SCN),
                         'fold': pd.Categorical.from_codes(np.full(n, FOLDS.index(fold), np.int8), FOLDS),
                         'seed': np.full(n, seed, np.int64),
                         'role': pd.Categorical(role, categories=ROLES)})

rows = []
for seed in SEEDS:
    rng = np.random.default_rng(1000 + seed)
    scen = {
        'S0_random': rng.random(len(cur)) < S0_TEST_FRAC,
        'S1_Lextreme': cur.L_idx.isin([0, cur.L_idx.max()]).values,     # shortest + longest L
        'S2_T125': (cur.T_C == 125).values,
        'S3_ff': (cur.corner == 'ff').values,
    }
    for name, m in scen.items():
        rows.append(piece(name, 'all', seed, assign(m, seed)))
    # S4: leave-one-PDK-out; held-out PDK's anchor curves are dropped (only its 3 anchor scalars are used)
    for p in pdks:
        m = (cur.pdk == p).values
        rows.append(piece('S4_LOPO', p, seed, assign(m, seed)))
sp = pd.concat(rows, ignore_index=True); del rows
assert all(isinstance(sp[c].dtype, pd.CategoricalDtype) for c in ['curve_id', 'scenario', 'fold', 'role'])
sp.to_parquet(os.path.join(BASE, 'splits.parquet'), index=False)

# ---------- sanity report ----------
print(anc.round(3).to_string(index=False))
print('\nplanar rows:', n_planar_rows, '| curves:', len(cur), '| anchor curves:', len(anchor_curves))
print('CAL_FRAC used:', CAL_FRAC)
summ = sp[sp.seed == 0].groupby(['scenario', 'fold', 'role'], observed=True).size().unstack(fill_value=0)
print(summ)
