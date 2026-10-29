# =====================================================================
# MESD project - Cell 03a: hyperparameter selection on an INNER VALIDATION split
# ENGINE script (executed by code/mesd_common.py run_step; never run it directly in Colab)
# Original note: STANDALONE Colab cell (GPU runtime). Run ONCE, after Cell 02 and before Cell 03.
# Needs: MESD_project/model_table.parquet, MESD_project/splits.parquet
# Output: MESD_project/tuning.json (read automatically by Cell 03), tuning_log.csv
# ---------------------------------------------------------------------
# Why this cell exists: hyperparameters must never be chosen on calibration or
# test curves (test-set reuse inflates accuracy; touching calibration data breaks
# the conformal guarantee). Here ONLY the 'train' curves of split S0 / seed 0 are
# used; they are divided BY CURVE into inner-train (85%) and inner-validation (15%),
# the same group-blocked logic used for leakage control by Kim et al. (Sci. Rep. 2026).
# The configuration with the lowest inner-validation MAE (decades) is written to
# tuning.json and is then FROZEN for every scenario, fold and seed.
# =====================================================================
import os, json, time
import numpy as np
import pandas as pd
import torch
import torch.nn as nn

# ---------- paths: set by code/mesd_common.py run_step() (no Drive mount here) ----------
WORK = os.environ.get('MESD_WORK', os.path.abspath('./MESD_project'))   # outputs of this step
DATA = os.environ.get('MESD_DATA', WORK)                                # fallback location of inputs
os.makedirs(WORK, exist_ok=True)
BASE = WORK
def inp(name):
    """Input file: taken from WORK if it exists there, otherwise from DATA."""
    p = os.path.join(WORK, name)
    return p if os.path.exists(p) else os.path.join(DATA, name)

# Candidate grid (architecture fixed at 4 x 256 SiLU; batch 8192; AdamW + one-cycle).
GRID = [dict(epochs=40, lr=2e-3, norm_wl=True),
        dict(epochs=40, lr=5e-3, norm_wl=True),
        dict(epochs=60, lr=3e-3, norm_wl=True),
        dict(epochs=60, lr=5e-3, norm_wl=True),
        dict(epochs=60, lr=5e-3, norm_wl=False),
        dict(epochs=100, lr=5e-3, norm_wl=True)]
HIDDEN, DEPTH, BATCH, WD = 256, 4, 8192, 1e-5
VAL_FRAC = 0.15
TUNE_CURVE_FRAC = float(os.environ.get('MESD_TUNE_FRAC', '1.0'))     # set 0.3 to tune on 30% of train curves if GPU time is short
MAX_GOOD_LOSS = 0.05
DEBUG = os.environ.get('MESD_DEBUG', '0') == '1'             # True = tiny CPU check (2 configs, 2 epochs, 3% of curves)
if DEBUG:
    GRID = [dict(epochs=2, lr=2e-3, norm_wl=True), dict(epochs=2, lr=5e-3, norm_wl=False)]
    TUNE_CURVE_FRAC, MAX_GOOD_LOSS = 0.03, np.inf

FEATS = ['lW', 'lL', 'lNode', 'Tn', 'corner_o', 'is_p', 'Vgs_eff', 'Vds_eff', 'Vgs_n', 'Vds_n',
         'Vov', 'Vdd', 'Vth_ref', 'lIon_ref', 'lIoff_ref']
DEV = 'cuda' if torch.cuda.is_available() else 'cpu'
print('device:', DEV)

tab = pd.read_parquet(inp('model_table.parquet'),
                      columns=['curve_id', 'valid_Id', 'region', 'y_logId'] + FEATS)
tab = tab[tab.valid_Id].reset_index(drop=True)
sp = pd.read_parquet(inp('splits.parquet'))
sp = sp[(sp.scenario == 'S0_random') & (sp.seed == 0) & (sp.role == 'train')]
train_curves = pd.Series(sp.curve_id.astype(str).unique())
if TUNE_CURVE_FRAC < 1:
    train_curves = train_curves.sample(frac=TUNE_CURVE_FRAC, random_state=0)
rng = np.random.default_rng(2026)
val_set = set(rng.choice(train_curves.values, int(VAL_FRAC * len(train_curves)), replace=False))
tab = tab[tab.curve_id.isin(set(train_curves))].reset_index(drop=True)
is_val = tab.curve_id.isin(val_set).to_numpy()
print(f'inner-train curves: {len(train_curves) - len(val_set):,} | inner-val curves: {len(val_set):,} '
      f'| cal/test curves used: 0')

X = tab[FEATS].to_numpy(np.float32); y = tab.y_logId.to_numpy(np.float32)
off_wl = (tab.lW - tab.lL).to_numpy(np.float32)
above = (tab.region == 'above').to_numpy()

class MLP(nn.Module):
    def __init__(self, d_in):
        super().__init__()
        L, d = [], d_in
        for _ in range(DEPTH):
            L += [nn.Linear(d, HIDDEN), nn.SiLU()]; d = HIDDEN
        self.net = nn.Sequential(*L, nn.Linear(d, 1))
    def forward(self, x):
        return self.net(x)

def fit_eval(cfg, seed=0):
    off = off_wl if cfg['norm_wl'] else np.zeros_like(y)
    yt = y - off
    tr = ~is_val
    mx, sx = X[tr].mean(0), X[tr].std(0) + 1e-8; my, sy = yt[tr].mean(), yt[tr].std() + 1e-8
    Xt = torch.tensor((X[tr] - mx) / sx, device=DEV); Yt = torch.tensor((yt[tr] - my) / sy, device=DEV)
    Xv = torch.tensor((X[is_val] - mx) / sx, device=DEV)
    torch.manual_seed(seed)
    net = MLP(X.shape[1]).to(DEV)
    opt = torch.optim.AdamW(net.parameters(), lr=cfg['lr'], weight_decay=WD)
    n = len(Xt); steps = cfg['epochs'] * int(np.ceil(n / BATCH))
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=cfg['lr'], total_steps=steps)
    g = torch.Generator(device='cpu').manual_seed(seed); tot = 0.0
    for ep in range(cfg['epochs']):
        perm = torch.randperm(n, generator=g).to(DEV); tot = 0.0
        for b in range(0, n, BATCH):
            i = perm[b:b + BATCH]
            loss = torch.mean((net(Xt[i])[:, 0] - Yt[i]) ** 2)
            opt.zero_grad(set_to_none=True); loss.backward(); opt.step(); sch.step()
            tot += loss.item() * len(i)
    net.eval()
    with torch.no_grad():
        pv = torch.cat([net(Xv[b:b + 65536]) for b in range(0, len(Xv), 65536)])[:, 0].cpu().numpy() * sy + my
    pv = pv + off[is_val]
    e = np.abs(pv - y[is_val]); ab = above[is_val]
    return dict(cfg, train_mse_std=tot / n, diverged=bool(not np.isfinite(tot / n) or tot / n > MAX_GOOD_LOSS),
                val_mae_dec=float(e.mean()), val_mae_sub=float(e[~ab].mean()),
                val_medrel_above=float(np.median(np.abs(10 ** (pv - y[is_val])[ab] - 1))))

log = []
for cfg in GRID:
    t0 = time.time(); r = fit_eval(cfg); r['minutes'] = round((time.time() - t0) / 60, 2)
    log.append(r); print(r)
lg = pd.DataFrame(log)
lg.to_csv(os.path.join(BASE, 'tuning_log.csv'), index=False)
ok = lg[~lg.diverged].sort_values(['val_mae_dec', 'epochs'])
assert len(ok), 'every configuration diverged: lower the learning rates in GRID'
best = ok.iloc[0]
choice = dict(epochs=int(best.epochs), lr=float(best.lr), norm_wl=bool(best.norm_wl),
              val_mae_dec=float(best.val_mae_dec), val_medrel_above=float(best.val_medrel_above),
              selected_on='S0_random seed 0, inner validation (15% of train curves)', debug=DEBUG)
if not DEBUG:
    with open(os.path.join(BASE, 'tuning.json'), 'w') as fh:
        json.dump(choice, fh, indent=2)
print('\nSELECTED:', choice)
print(lg[['epochs', 'lr', 'norm_wl', 'val_mae_dec', 'val_mae_sub', 'val_medrel_above', 'diverged', 'minutes']].round(4))
