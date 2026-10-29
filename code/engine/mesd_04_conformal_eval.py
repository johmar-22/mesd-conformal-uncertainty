# =====================================================================
# MESD project - Cell 04: conformal / uncertainty evaluation   (v2)
# ENGINE script (executed by code/mesd_common.py run_step; never run it directly in Colab)
# Original note: STANDALONE Colab cell (CPU runtime is enough; High-RAM helps).
# Needs: model_table.parquet (Cell 02), preds/<target>/*.parquet (Cell 03).
# Output: MESD_project/results/<target>/results_long.csv  (one row per
#         run x method x alpha), curve_checks.csv (one row per test curve)
# ---------------------------------------------------------------------
# Unit of exchangeability: the CURVE (one Vgs sweep). Points inside a curve are
# correlated, so point-wise conformal coverage is exact only marginally over
# curves and approximately per point (Dunn, Wasserman & Ramdas, JASA 2023).
# We therefore also report (i) a curve-level simultaneous band, SCP-curve,
# whose guarantee is exact for whole curves (Diquigiovanni, Fontana & Vantini,
# J. Multivariate Anal. 2022), and (ii) cluster-bootstrap CIs (resampling curves).
#
# Methods (all calibrated on the CAL split = training side of each shift):
#   SCP-single : split conformal, |y - mu_0|                      (Lei et al., JASA 2018)
#   SCP-ens    : split conformal, |y - mean_k(mu_k)|
#   Ens-Gauss  : mean +/- z * sd_k(mu_k), NOT calibrated (baseline; Lakshminarayanan 2017)
#   NCP        : normalized conformal, |y - mu| / sd               (Lei et al. 2018)
#   CQR        : conformalized quantile regression, alpha=0.10 only (Romano et al. 2019)
#   Mondrian-region : SCP-ens with separate quantiles for sub-/above-threshold
#                (region from inputs only: Vov = Vgs - Vth_ref)    (Vovk et al. 2005)
#   SCP-curve  : simultaneous band; score per calibration CURVE = max_i |y_i-mu_i|/sd_i
#   WCP        : weighted conformal under covariate shift          (Tibshirani et al. 2019)
#   Recal-k / RecalNCP-k : SCP-ens / NCP recalibrated on k curves of the TARGET domain
# Metrics: point coverage (+ 95% cluster-bootstrap CI at alpha=0.10), curve coverage
# (all points of a curve inside the band), widths, Winkler score, group coverage,
# accuracy, AUROC of ensemble spread, monotonicity, Vth error and Vth-interval coverage.
# =====================================================================
import os, glob
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.metrics import roc_auc_score
from sklearn.ensemble import HistGradientBoostingClassifier

# ---------- paths: set by code/mesd_common.py run_step() (no Drive mount here) ----------
WORK = os.environ.get('MESD_WORK', os.path.abspath('./MESD_project'))   # outputs of this step
DATA = os.environ.get('MESD_DATA', WORK)                                # fallback location of inputs
os.makedirs(WORK, exist_ok=True)
BASE = WORK
def inp(name):
    """Input file: taken from WORK if it exists there, otherwise from DATA."""
    p = os.path.join(WORK, name)
    return p if os.path.exists(p) else os.path.join(DATA, name)

TARGET = os.environ.get('MESD_TARGET', 'y_logId')
N_ENS_USE = int(os.environ.get('MESD_N_ENS_USE', '0'))   # 0 = all ensemble members; 3 = sensitivity check
RES_TAG = os.environ.get('MESD_RES_TAG', '')              # e.g. '_ens3' -> results/y_logId_ens3
ALPHAS = [0.20, 0.10, 0.05]
RECAL_K = [5, 20, 100]
ERR_FLAG = 0.30            # decades; "large error" (factor 2) for the AUROC check
MONO_TOL = 0.01            # decades; tolerance for the non-monotonicity check
MIN_GROUP = 1000           # points; smallest group counted in worst-group coverage
N_BOOT = 500               # cluster-bootstrap resamples (curves) for coverage CIs
EPS = 1e-6
PRED_DIR = os.path.join(BASE, 'preds', TARGET)
RES_DIR = os.path.join(BASE, 'results', TARGET + RES_TAG); os.makedirs(RES_DIR, exist_ok=True)

FEATS = ['lW', 'lL', 'lNode', 'Tn', 'corner_o', 'is_p', 'Vgs_eff', 'Vds_eff', 'Vgs_n', 'Vds_n',
         'Vov', 'Vdd', 'Vth_ref', 'lIon_ref', 'lIoff_ref']
meta = pd.read_parquet(inp('model_table.parquet'),
                       columns=['curve_id', 'pdk', 'valid_Id', 'region', 'W_nm', 'L_nm'] + FEATS)
if TARGET == 'y_logId':
    meta = meta[meta.valid_Id].reset_index(drop=True)
meta['row'] = np.arange(len(meta), dtype=np.int64)

# ------------------------------ helpers ------------------------------
def cq(scores, alpha):
    """Finite-sample conformal quantile: the ceil((n+1)(1-alpha))-th smallest score."""
    s = np.sort(np.asarray(scores)); n = len(s)
    k = int(np.ceil((n + 1) * (1 - alpha)))
    return np.inf if k > n else s[k - 1]

def weighted_cq(cal_scores, cal_w, test_w, alpha):
    """Per-test-point weighted conformal quantile (Tibshirani et al. 2019).
    The test point's own weight sits at +inf, so the threshold is infinite when
    (1 - alpha) of the total weight cannot be reached by calibration points."""
    o = np.argsort(cal_scores); s = cal_scores[o]; cw = np.cumsum(cal_w[o]); W = cw[-1]
    need = (1 - alpha) * (W + test_w)
    idx = np.searchsorted(cw, need, side='left')
    out = np.full(len(test_w), np.inf)
    ok = idx < len(s)
    out[ok] = s[idx[ok]]
    return out

def cluster_boot_ci(cov, codes, seed, B=N_BOOT, chunk=50):
    """95% percentile CI of pooled point coverage, resampling CURVES with replacement
    (cluster bootstrap; Field & Welsh, JRSS-B 2007)."""
    k = np.bincount(codes, weights=cov.astype(float)); n = np.bincount(codes).astype(float)
    nc = len(n); rng = np.random.default_rng(seed); est = []
    for b in range(0, B, chunk):
        idx = rng.integers(0, nc, size=(min(chunk, B - b), nc))
        est.append(k[idx].sum(1) / n[idx].sum(1))
    est = np.concatenate(est)
    return np.percentile(est, 2.5), np.percentile(est, 97.5)

def interval_metrics(y, lo, hi, alpha, groups=None, codes=None, boot_seed=None):
    cov = (y >= lo) & (y <= hi)
    width = hi - lo
    fin = np.isfinite(width)
    pen = np.where(y < lo, lo - y, 0.0) + np.where(y > hi, y - hi, 0.0)
    wink = width + (2 / alpha) * pen
    m = dict(coverage=cov.mean(), width_mean=np.mean(width[fin]) if fin.any() else np.inf,
             width_median=np.median(width), frac_infinite=1 - fin.mean(),
             winkler=np.mean(wink[fin]) if fin.any() else np.inf)
    if codes is not None:
        n_c = np.bincount(codes); k_c = np.bincount(codes, weights=cov.astype(float))
        m['curve_coverage'] = np.mean(k_c[n_c > 0] == n_c[n_c > 0])   # whole curve inside band
        if boot_seed is not None:
            m['cov_ci_lo'], m['cov_ci_hi'] = cluster_boot_ci(cov, codes, boot_seed)
    if groups is not None:
        g = pd.DataFrame({'g': groups, 'c': cov}).groupby('g')['c'].agg(['mean', 'size'])
        g = g[g['size'] >= MIN_GROUP]
        m['worst_group_cov'] = g['mean'].min() if len(g) else np.nan
        for name, v in g['mean'].items():
            m[f'cov[{name}]'] = v
    return m

def domain_weights(Xc, Xt, cid_c, cid_t, seed):
    """Likelihood-ratio weights w(x) = p/(1-p) from a cal(0)-vs-test(1) classifier.
    CROSS-FITTED BY CURVE: the classifier never scores points of curves it was trained on.
    (In-sample scoring memorises each curve's unique input combination and reports a
    spurious AUC near 1 even for a random split.) Classes are balanced in training."""
    rng = np.random.default_rng(seed)
    ids = np.unique(np.r_[cid_c, cid_t]); fold_of = dict(zip(ids, rng.integers(0, 2, len(ids))))
    fc = np.array([fold_of[c] for c in cid_c]); ft = np.array([fold_of[c] for c in cid_t])
    pc = np.empty(len(Xc)); pt = np.empty(len(Xt))
    for f in (0, 1):
        ic, it = np.where(fc != f)[0], np.where(ft != f)[0]          # train on the other fold
        n = min(len(ic), len(it), 100_000)
        ic = rng.choice(ic, n, replace=False); it = rng.choice(it, n, replace=False)
        clf = HistGradientBoostingClassifier(max_iter=100, max_leaf_nodes=15, learning_rate=0.1,
                                             random_state=seed)
        clf.fit(np.vstack([Xc[ic], Xt[it]]), np.r_[np.zeros(n), np.ones(n)])
        pc[fc == f] = clf.predict_proba(Xc[fc == f])[:, 1]
        pt[ft == f] = clf.predict_proba(Xt[ft == f])[:, 1]
    auc = roc_auc_score(np.r_[np.zeros(len(pc)), np.ones(len(pt))], np.r_[pc, pt])
    pc = np.clip(pc, 1e-4, 1 - 1e-4); pt = np.clip(pt, 1e-4, 1 - 1e-4)
    return pc / (1 - pc), pt / (1 - pt), auc

def vth_from_curve(vgs, logid, icrit_log):
    """Constant-current Vth: first upward crossing of log10(Icrit), linear interpolation."""
    k = np.where((logid[:-1] < icrit_log) & (logid[1:] >= icrit_log))[0]
    if len(k) == 0:
        return np.nan
    k = k[0]
    return vgs[k] + (icrit_log - logid[k]) * (vgs[k + 1] - vgs[k]) / (logid[k + 1] - logid[k])

def curve_max_scores(y, mu, sig, codes):
    """Per-curve max normalized residual (one score per calibration curve)."""
    s = np.abs(y - mu) / sig
    out = np.full(codes.max() + 1, -np.inf)
    np.maximum.at(out, codes, s)
    return out[np.isfinite(out)]

# ------------------------------ main loop ------------------------------
rows, curve_rows = [], []
files = sorted(glob.glob(os.path.join(PRED_DIR, '*.parquet')))
print(len(files), 'prediction files | ensemble members used:', N_ENS_USE or 'all')
# ---- per-file checkpoint: each prediction file's results are cached in RES_DIR/parts/. They are reused
# when this evaluation code, its settings and the prediction file's own training fingerprint are unchanged,
# so an interrupted evaluation resumes and an unchanged one is not recomputed.
import pickle, hashlib
FP = os.environ.get('MESD_FP', '')
PARTS = os.path.join(RES_DIR, 'parts'); os.makedirs(PARTS, exist_ok=True)
n_cached = 0
for fn in files:
    _name = os.path.basename(fn)[:-8]
    _pfp = open(fn + '.fp').read().strip() if os.path.exists(fn + '.fp') else 'nofp'
    _kfp = hashlib.sha256(f'{FP}|{_pfp}|{N_ENS_USE}|{TARGET}'.encode()).hexdigest()[:16]
    _part = os.path.join(PARTS, _name + '.pkl')
    if FP and os.path.exists(_part):
        with open(_part, 'rb') as _fh:
            _d = pickle.load(_fh)
        if _d.get('fp') == _kfp:
            rows.extend(_d['rows']); curve_rows.extend(_d['curve_rows']); n_cached += 1
            print(_name, '| reused from checkpoint')
            continue
    _r0, _c0 = len(rows), len(curve_rows)
    sc, fold, sd = os.path.basename(fn)[:-8].split('__'); seed = int(sd.replace('seed', ''))
    P = pd.read_parquet(fn).merge(meta, on='row', how='left')
    mcols = sorted([c for c in P.columns if c.startswith('mu') and c[2:].isdigit()], key=lambda c: int(c[2:]))
    if N_ENS_USE:
        mcols = mcols[:N_ENS_USE]
    mus = P[mcols].to_numpy()
    P['mu'] = mus.mean(1); P['sig'] = mus.std(1) + EPS; P['mu0'] = mus[:, 0]
    C = P[P.role == 'cal'].reset_index(drop=True); T = P[P.role == 'test'].reset_index(drop=True)
    yC, yT = C.y.to_numpy(), T.y.to_numpy()
    cC = pd.factorize(C.curve_id)[0]; cT = pd.factorize(T.curve_id)[0]
    grp = (T.pdk.astype(str) + '|' + T.region.astype(str)).to_numpy()
    base = dict(scenario=sc, fold=fold, seed=seed, n_cal=len(C), n_test=len(T),
                n_cal_curves=int(cC.max() + 1), n_test_curves=int(cT.max() + 1))

    # ---- accuracy & reliability (method-independent) ----
    err = np.abs(T.mu - yT).to_numpy()
    above = (T.region == 'above').to_numpy()
    acc = dict(base, method='accuracy', alpha=np.nan,
               mae_dec=err.mean(), mae_dec_sub=err[~above].mean() if (~above).any() else np.nan,
               mae_dec_above=err[above].mean() if above.any() else np.nan,
               medrel_above=np.median(np.abs(10 ** (T.mu - yT)[above] - 1)) if above.any() else np.nan,
               auroc_sigma_err=roc_auc_score(err > ERR_FLAG, T.sig) if 0 < (err > ERR_FLAG).mean() < 1 else np.nan,
               frac_err_gt_flag=(err > ERR_FLAG).mean())
    rows.append(acc)

    # ---- domain-classifier weights for WCP ----
    XC, XT = C[FEATS].to_numpy(np.float32), T[FEATS].to_numpy(np.float32)
    wC, wT, dom_auc = domain_weights(XC, XT, C.curve_id.to_numpy(), T.curve_id.to_numpy(), seed)
    s_curve = curve_max_scores(yC, C.mu.to_numpy(), C.sig.to_numpy(), cC)

    for a in ALPHAS:
        z = norm.ppf(1 - a / 2)
        meth = {}
        q = cq(np.abs(yC - C.mu0), a);           meth['SCP-single'] = (T.mu0 - q, T.mu0 + q)
        q = cq(np.abs(yC - C.mu), a);            meth['SCP-ens'] = (T.mu - q, T.mu + q)
        meth['Ens-Gauss'] = (T.mu - z * T.sig, T.mu + z * T.sig)
        q = cq(np.abs(yC - C.mu) / C.sig, a);    meth['NCP'] = (T.mu - q * T.sig, T.mu + q * T.sig)
        if abs(a - 0.10) < 1e-9:
            s = np.maximum(C.q_lo - yC, yC - C.q_hi); q = cq(s, a)
            meth['CQR'] = (T.q_lo - q, T.q_hi + q)
        lo = np.empty(len(T)); hi = np.empty(len(T))
        for r in ['sub', 'above']:
            mc, mt = (C.region == r).to_numpy(), (T.region == r).to_numpy()
            q = cq(np.abs(yC[mc] - C.mu[mc]), a) if mc.sum() > 0 else np.inf
            lo[mt], hi[mt] = T.mu[mt] - q, T.mu[mt] + q
        meth['Mondrian-region'] = (lo, hi)
        q = cq(s_curve, a);                      meth['SCP-curve'] = (T.mu - q * T.sig, T.mu + q * T.sig)
        qw = weighted_cq(np.abs(yC - C.mu.to_numpy()), wC, wT, a)
        meth['WCP'] = (T.mu - qw, T.mu + qw)
        for name, (l, h) in meth.items():
            m = interval_metrics(yT, np.asarray(l), np.asarray(h), a, grp, cT,
                                 boot_seed=(seed if abs(a - 0.10) < 1e-9 else None))
            if name == 'WCP':
                m['domain_auc'] = dom_auc
            rows.append(dict(base, method=name, alpha=a, **m))
        # ---- recalibration with k target-domain curves ----
        tc = T.curve_id.unique()
        for k in RECAL_K:
            if k >= len(tc) // 2:
                continue
            for rep in range(5):
                rng = np.random.default_rng(10_000 * seed + 100 * k + rep)
                pick = set(rng.choice(tc, k, replace=False))
                mk = T.curve_id.isin(pick).to_numpy()
                rest_codes = pd.factorize(T.curve_id[~mk])[0]
                q = cq(np.abs(yT[mk] - T.mu[mk]), a)
                m = interval_metrics(yT[~mk], (T.mu[~mk] - q).to_numpy(), (T.mu[~mk] + q).to_numpy(), a,
                                     grp[~mk], rest_codes)
                rows.append(dict(base, method=f'Recal-{k}', alpha=a, rep=rep, **m))
                qn = cq((np.abs(yT[mk] - T.mu[mk]) / T.sig[mk]).to_numpy(), a)
                lo_n = (T.mu[~mk] - qn * T.sig[~mk]).to_numpy(); hi_n = (T.mu[~mk] + qn * T.sig[~mk]).to_numpy()
                m = interval_metrics(yT[~mk], lo_n, hi_n, a, grp[~mk], rest_codes)
                rows.append(dict(base, method=f'RecalNCP-{k}', alpha=a, rep=rep, **m))

    # ---- curve-level checks at Vds = VDD: monotonicity and Vth ----
    qe = cq(np.abs(yC - C.mu), 0.10)            # point-wise SCP-ens band (for comparison)
    qc = cq(s_curve, 0.10)                       # simultaneous curve band (used for the Vth interval)
    top = T[np.isclose(T.Vds_eff, T.Vdd)] if TARGET == 'y_logId' else T.iloc[0:0]   # Vth checks: drain current only
    for cid, g in top.groupby('curve_id', sort=False):
        g = g.sort_values('Vgs_eff')
        if len(g) < 4:
            continue
        v, yt, mu, sg = g.Vgs_eff.to_numpy(), g.y.to_numpy(), g.mu.to_numpy(), g.sig.to_numpy()
        ab = g.Vov.to_numpy() > 0           # monotonicity is required by physics only above threshold;
                                            # near Vgs = 0 the TRUE curves can fall (GIDL, ~10% of curves)
        icl = np.log10(1e-7 * g.W_nm.iloc[0] / g.L_nm.iloc[0])
        vt, vp = vth_from_curve(v, yt, icl), vth_from_curve(v, mu, icl)
        c_lo, c_hi = vth_from_curve(v, mu + qc * sg, icl), vth_from_curve(v, mu - qc * sg, icl)  # upper band -> lower Vth
        p_lo, p_hi = vth_from_curve(v, mu + qe, icl), vth_from_curve(v, mu - qe, icl)
        curve_rows.append(dict(base, curve_id=cid, pdk=g.pdk.iloc[0],
                               nonmono_pred_above=bool(np.any(np.diff(mu[ab]) < -MONO_TOL)) if ab.sum() > 1 else np.nan,
                               nonmono_true_above=bool(np.any(np.diff(yt[ab]) < -MONO_TOL)) if ab.sum() > 1 else np.nan,
                               nonmono_pred_all=bool(np.any(np.diff(mu) < -MONO_TOL)),
                               nonmono_true_all=bool(np.any(np.diff(yt) < -MONO_TOL)),
                               vth_true=vt, vth_pred=vp,
                               vth_err_mV=1000 * abs(vp - vt) if np.isfinite(vp + vt) else np.nan,
                               vth_covered=bool(c_lo <= vt <= c_hi) if np.isfinite(c_lo + c_hi + vt) else np.nan,
                               vth_width_mV=1000 * (c_hi - c_lo) if np.isfinite(c_lo + c_hi) else np.nan,
                               vth_covered_pointwise=bool(p_lo <= vt <= p_hi) if np.isfinite(p_lo + p_hi + vt) else np.nan))
    print(sc, fold, seed, '| MAE %.3f dec | AUROC %.2f | dom-AUC %.2f' % (acc['mae_dec'], acc['auroc_sigma_err'], dom_auc))
    if FP:
        with open(_part + '.tmp', 'wb') as _fh:
            pickle.dump(dict(fp=_kfp, rows=rows[_r0:], curve_rows=curve_rows[_c0:]), _fh)
        os.replace(_part + '.tmp', _part)

print(f'{len(files)} prediction files | {n_cached} reused from checkpoint | {len(files) - n_cached} computed now')
res = pd.DataFrame(rows); res.to_csv(os.path.join(RES_DIR, 'results_long.csv'), index=False)
cur = pd.DataFrame(curve_rows); cur.to_csv(os.path.join(RES_DIR, 'curve_checks.csv'), index=False)

# ------------------------------ quick summary ------------------------------
pd.set_option('display.width', 250); pd.set_option('display.max_columns', None)
a10 = res[res.alpha == 0.10]
print(a10.groupby(['scenario', 'method'])['coverage'].mean().unstack('method').round(3))
print(a10.groupby(['scenario', 'method'])['curve_coverage'].mean().unstack('method').round(3))
print(res[res.method == 'accuracy'].groupby('scenario')[['mae_dec', 'medrel_above', 'auroc_sigma_err']].mean().round(3))
if len(cur):
    print(cur.groupby('scenario')[['nonmono_pred_above', 'nonmono_true_above', 'vth_err_mV',
                                   'vth_covered', 'vth_width_mV', 'vth_covered_pointwise']].mean().round(3))
