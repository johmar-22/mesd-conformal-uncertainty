# =====================================================================
# MESD project - Cell 03: train neural surrogates for every split
# ENGINE script (executed by code/mesd_common.py run_step; never run it directly in Colab)
# Original note: STANDALONE Colab cell (run in its own notebook, GPU runtime: T4 is enough).
# Needs: MESD_project/model_table.parquet, MESD_project/splits.parquet (Cell 02).
# Output: MESD_project/preds/<target>/<scenario>__<fold>__seed<k>.parquet
#         (predictions for calibration + test rows only) and a run log.
# Resumable: runs whose output file exists are skipped, so after a Colab
# disconnect just re-run the cell.
# ---------------------------------------------------------------------
# Models per run (same inputs, same training rows; calibration rows are
# NEVER used for training or model selection, which conformal validity needs):
#   * deep ensemble: N_ENS MLPs with MSE loss, different init + shuffling
#     (Lakshminarayanan et al., NeurIPS 2017)
#   * one quantile MLP with pinball loss for q = 0.05, 0.5, 0.95, used for
#     conformalized quantile regression (Romano et al., NeurIPS 2019)
# =====================================================================
import os, time, json
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

# ------------------------------ configuration ------------------------------
TARGET = os.environ.get('MESD_TARGET', 'y_logId')                # 'y_logId' (main) or 'y_logCgg' (secondary)
SCENARIOS = os.environ.get('MESD_SCENARIOS', 'S0_random,S1_Lextreme,S2_T125,S3_ff,S4_LOPO').split(',')
SEEDS_MAIN = [int(s) for s in os.environ.get('MESD_SEEDS_MAIN', '0,1,2,3,4').split(',')]      # seeds for S0-S3
SEEDS_LOPO = [int(s) for s in os.environ.get('MESD_SEEDS_LOPO', '0,1,2').split(',')]            # seeds for each of the 8 LOPO folds
N_ENS = 5
HIDDEN, DEPTH = 256, 4
EPOCHS, BATCH, LR, WD = 60, 8192, 5e-3, 1e-5   # tested: 25 ep/2e-3 -> 16% median rel. error; 100 ep/5e-3 -> 3.5%; 1e-2 diverges
NORM_WL = True                     # learn log10(Id*L/W) (current per square), add log10(W/L) back
MAX_GOOD_LOSS = 0.05               # standardized train MSE above this (or NaN) => retrain with LR/2
QUANTILES = (0.05, 0.5, 0.95)
DEBUG = os.environ.get('MESD_DEBUG', '0') == '1'                     # True = tiny run for a syntax/logic check on CPU
# Hyperparameters chosen on inner-validation curves by Cell 03a override the defaults above
# (the defaults are only a fallback; the paper must report the values in tuning.json).
_tj = inp('tuning.json')
if not DEBUG and os.path.exists(_tj):
    with open(_tj) as fh:
        _t = json.load(fh)
    EPOCHS, LR, NORM_WL = int(_t['epochs']), float(_t['lr']), bool(_t['norm_wl'])
    print(f'using tuning.json: epochs={EPOCHS}, lr={LR}, norm_wl={NORM_WL}')
elif not DEBUG:
    print('WARNING: tuning.json not found - run Cell 03a first; using fallback defaults')
if DEBUG:
    EPOCHS, N_ENS, SEEDS_MAIN, SEEDS_LOPO, MAX_GOOD_LOSS = 2, 2, [0], [0], np.inf

FEATS = ['lW', 'lL', 'lNode', 'Tn', 'corner_o', 'is_p', 'Vgs_eff', 'Vds_eff', 'Vgs_n', 'Vds_n',
         'Vov', 'Vdd', 'Vth_ref', 'lIon_ref', 'lIoff_ref']
DEV = 'cuda' if torch.cuda.is_available() else 'cpu'
OUT = os.path.join(BASE, 'preds', TARGET); os.makedirs(OUT, exist_ok=True)
print('device:', DEV)

# ------------------------------ data ------------------------------
tab = pd.read_parquet(inp('model_table.parquet'),
                      columns=['curve_id', 'valid_Id', TARGET] + FEATS)
if TARGET != 'y_logId':
    NORM_WL = False                # Cgg scales with W*L, not W/L: no per-square normalization
if TARGET == 'y_logId':
    tab = tab[tab.valid_Id].reset_index(drop=True)      # Vds = 0 has Id = 0 by physics
tab['row'] = np.arange(len(tab), dtype=np.int64)
splits = pd.read_parquet(inp('splits.parquet'))
for c in ['curve_id', 'scenario', 'fold', 'role']:          # categorical = low memory, fast comparisons
    if not isinstance(splits[c].dtype, pd.CategoricalDtype):
        splits[c] = splits[c].astype('category')
CID_CATS = splits.curve_id.cat.categories
TAB_CODES = pd.Categorical(tab.curve_id.astype(str), categories=CID_CATS).codes   # -1 = curve not in splits

def roles_for(s):
    """Role of every row of tab for one run (same result as a left merge on curve_id; missing -> 'unused')."""
    lut = np.full(len(CID_CATS) + 1, 'unused', dtype=object)          # last slot catches code -1
    lut[s.curve_id.cat.codes.to_numpy()] = s.role.astype(str).to_numpy()
    return lut[TAB_CODES]
X_all = tab[FEATS].to_numpy(np.float32)
y_all = tab[TARGET].to_numpy(np.float32)
OFF = (tab.lW - tab.lL).to_numpy(np.float32) if NORM_WL else np.zeros(len(tab), np.float32)
y_fit = y_all - OFF                # training target; predictions get OFF added back

if DEBUG:   # keep 3% of curves
    keep = pd.Series(tab.curve_id.unique()).sample(frac=0.03, random_state=0)
    sel = tab.curve_id.isin(set(keep)).to_numpy()
else:
    sel = np.ones(len(tab), bool)

# ------------------------------ model ------------------------------
class MLP(nn.Module):
    def __init__(self, d_in, d_out):
        super().__init__()
        layers, d = [], d_in
        for _ in range(DEPTH):
            layers += [nn.Linear(d, HIDDEN), nn.SiLU()]; d = HIDDEN
        layers += [nn.Linear(d, d_out)]
        self.net = nn.Sequential(*layers)
    def forward(self, x):
        return self.net(x)

def pinball(pred, y, qs):
    e = y.unsqueeze(1) - pred
    q = torch.tensor(qs, device=pred.device).unsqueeze(0)
    return torch.mean(torch.maximum(q * e, (q - 1) * e))

def train_one(Xtr, ytr, seed, quantile=False, lr=None, attempt=0):
    lr = LR if lr is None else lr
    torch.manual_seed(seed); np.random.seed(seed)
    model = MLP(Xtr.shape[1], len(QUANTILES) if quantile else 1).to(DEV)
    opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=WD)
    n = Xtr.shape[0]; steps = EPOCHS * int(np.ceil(n / BATCH))
    sch = torch.optim.lr_scheduler.OneCycleLR(opt, max_lr=lr, total_steps=steps)
    g = torch.Generator(device='cpu').manual_seed(seed)
    model.train()
    for ep in range(EPOCHS):
        perm = torch.randperm(n, generator=g).to(DEV)
        tot = 0.0
        for b in range(0, n, BATCH):
            idx = perm[b:b + BATCH]
            out = model(Xtr[idx])
            loss = pinball(out, ytr[idx], QUANTILES) if quantile else torch.mean((out[:, 0] - ytr[idx]) ** 2)
            opt.zero_grad(set_to_none=True); loss.backward(); opt.step(); sch.step()
            tot += loss.item() * len(idx)
    model.eval()
    final = tot / n
    limit = MAX_GOOD_LOSS * (0.5 if quantile else 1.0)          # pinball loss is on a smaller scale
    if (not np.isfinite(final) or final > limit) and attempt < 2:
        print(f'  loss {final:.4f} too high at lr={lr:g}; retraining with lr={lr / 2:g}')
        return train_one(Xtr, ytr, seed, quantile, lr=lr / 2, attempt=attempt + 1)
    return model, final

@torch.no_grad()
def predict(model, X):
    return torch.cat([model(X[b:b + 65536]) for b in range(0, X.shape[0], 65536)]).cpu().numpy()

# ------------------------------ runs ------------------------------
runs = []
for sc in SCENARIOS:
    for seed in (SEEDS_LOPO if sc == 'S4_LOPO' else SEEDS_MAIN):
        folds = sorted(str(f) for f in splits.loc[(splits.scenario == sc) & (splits.seed == seed), 'fold'].unique())
        for fold in folds:
            runs.append((sc, fold, seed))
# ---- per-run checkpoint: a run is skipped only if its file exists AND was made with the same fingerprint
# (same training code, tuning.json, splits and settings). Otherwise it is (re)trained; an outdated file is
# moved to preds/<target>/_superseded/ first. Files made before checkpoint tracking are adopted once.
FP = os.environ.get('MESD_FP', '')
import shutil

def ckpt_ok(fn):
    side = fn + '.fp'
    if not os.path.exists(fn):
        return False
    if not FP:
        return True
    if not os.path.exists(side):
        open(side, 'w').write(FP)          # adopt a pre-v3 file (no fingerprint yet)
        return True
    if open(side).read().strip() == FP:
        return True
    sup = os.path.join(OUT, '_superseded'); os.makedirs(sup, exist_ok=True)
    stamp = time.strftime('%Y%m%d_%H%M%S')
    for f in (fn, side):
        shutil.move(f, os.path.join(sup, os.path.basename(f) + '.' + stamp))
    print(f'  outdated (amended) run moved to _superseded: {os.path.basename(fn)}')
    return False

done = [ckpt_ok(os.path.join(OUT, f'{a}__{b}__seed{c}.parquet')) for a, b, c in runs]
print(len(runs), 'runs |', sum(done), 'already done with the current fingerprint (reused from checkpoint) |',
      len(runs) - sum(done), 'to train | fingerprint', FP or 'none')

log_path = os.path.join(OUT, 'train_log.jsonl')
for sc, fold, seed in runs:
    fn = os.path.join(OUT, f'{sc}__{fold}__seed{seed}.parquet')
    if os.path.exists(fn) and (not FP or (os.path.exists(fn + '.fp') and open(fn + '.fp').read().strip() == FP)):
        continue
    t0 = time.time()
    s = splits[(splits.scenario == sc) & (splits.fold == fold) & (splits.seed == seed)][['curve_id', 'role']]
    role = roles_for(s)
    tr = np.where((role == 'train') & sel)[0]
    ev = np.where(((role == 'cal') | (role == 'test')) & sel)[0]
    # standardize with TRAIN statistics only
    mu_x, sd_x = X_all[tr].mean(0), X_all[tr].std(0) + 1e-8
    mu_y, sd_y = y_fit[tr].mean(), y_fit[tr].std() + 1e-8
    Xtr = torch.tensor((X_all[tr] - mu_x) / sd_x, device=DEV)
    ytr = torch.tensor((y_fit[tr] - mu_y) / sd_y, device=DEV)
    Xev = torch.tensor((X_all[ev] - mu_x) / sd_x, device=DEV)
    res = {'row': tab.row.values[ev], 'role': role[ev], 'y': y_all[ev]}
    losses = []
    for k in range(N_ENS):
        m, l = train_one(Xtr, ytr, seed=1000 * seed + k)
        res[f'mu{k}'] = predict(m, Xev)[:, 0] * sd_y + mu_y + OFF[ev]; losses.append(l)
    mq, lq = train_one(Xtr, ytr, seed=1000 * seed + 99, quantile=True)
    q = predict(mq, Xev) * sd_y + mu_y + OFF[ev][:, None]
    q.sort(axis=1)                                   # repair rare quantile crossing
    res['q_lo'], res['q_med'], res['q_hi'] = q[:, 0], q[:, 1], q[:, 2]
    out = pd.DataFrame(res)
    for c in out.columns:
        if out[c].dtype == np.float64:
            out[c] = out[c].astype(np.float32)
    out.to_parquet(fn + '.tmp', index=False)
    os.replace(fn + '.tmp', fn)                # atomic: a disconnect never leaves a half-written run file
    if FP:
        open(fn + '.fp', 'w').write(FP)        # checkpoint fingerprint of this run
    rec = dict(fp=FP, scenario=sc, fold=fold, seed=seed, n_train=int(len(tr)), n_eval=int(len(ev)),
               train_loss_ens=[round(x, 5) for x in losses], train_loss_q=round(lq, 5),
               minutes=round((time.time() - t0) / 60, 2))
    with open(log_path, 'a') as fh:
        fh.write(json.dumps(rec) + '\n')
    print(rec)
    del Xtr, ytr, Xev
    if DEV == 'cuda':
        torch.cuda.empty_cache()
print('done')
