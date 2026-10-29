# =====================================================================
# MESD project - Cell 05: paper tables and figures
# ENGINE script (executed by code/mesd_common.py run_step; never run it directly in Colab)
# Original note: STANDALONE Colab cell (CPU). Needs: results/<target>/results_long.csv,
# results/<target>/curve_checks.csv (Cell 04), mesd_long.parquet (Cell 01).
# Output: <work>/paper/<target>/  (PNG at 600 dpi + vector PDF + <figure>_data.csv, CSV tables).
#         Figures follow figstyle.py (8.5 cm single column, 15 cm double column, serif text 8-9 pt)
#         with batlow colours (Kaspar & Crameri 2022). Code v4.
# =====================================================================
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

# ---------- paths: set by code/mesd_common.py run_step() (no Drive mount here) ----------
WORK = os.environ.get('MESD_WORK', os.path.abspath('./MESD_project'))
DATA = os.environ.get('MESD_DATA', WORK)
BASE = WORK
def inp(name):
    p = os.path.join(WORK, name)
    return p if os.path.exists(p) else os.path.join(DATA, name)

TARGET = os.environ.get('MESD_TARGET', 'y_logId')
RES_TAG = os.environ.get('MESD_RES_TAG', '')
RES = os.path.join(BASE, 'results', TARGET + RES_TAG)
OUT = os.path.join(BASE, 'paper', TARGET + RES_TAG); os.makedirs(OUT, exist_ok=True)
# ---------- figure standard: the author's figstyle.py (Times-like serif, 8.5 cm / 15 cm wide, 600 dpi PNG +
# vector PDF, colour AND line style AND marker per series, panel labels outside the axes, legends placed
# where they hide the least data) with colours from Crameri's batlow map (Kaspar & Crameri 2022).
import importlib.util
_spec = importlib.util.spec_from_file_location('figstyle', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'figstyle.py'))
fs = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(fs)
fs.apply_style()
print('figure font in use:', fs.font_in_use())
INK = '#000000'
SC_ORDER = ['S0_random', 'S1_Lextreme', 'S2_T125', 'S3_ff', 'S4_LOPO']
SC_LABEL = {'S0_random': 'S0 random', 'S1_Lextreme': 'S1 L-extreme', 'S2_T125': 'S2 125 \u00b0C',
            'S3_ff': 'S3 ff corner', 'S4_LOPO': 'S4 new PDK'}
SC_SHORT = {'S0_random': 'S0', 'S1_Lextreme': 'S1', 'S2_T125': 'S2', 'S3_ff': 'S3', 'S4_LOPO': 'S4'}
M_ORDER = ['SCP-single', 'SCP-ens', 'Ens-Gauss', 'NCP', 'CQR', 'Mondrian-region', 'SCP-curve', 'WCP']
FIG_INFO = []
AUDIT = os.path.join(OUT, 'figure_audit.csv')
if os.path.exists(AUDIT):
    os.remove(AUDIT)


def save(fig, name, data=None):
    """PNG (600 dpi) + PDF via figstyle, plus the plotted numbers as <name>_data.csv (Kaspar & Crameri:
    graphically represented data should also be available in tabulated form)."""
    info = fs.save_fig(fig, name, OUT)
    if data is not None:
        data.to_csv(os.path.join(OUT, name + '_data.csv'))
    FIG_INFO.append(info)
    print(f"  {name}: {info['width_cm']} x {info['height_cm']} cm as written ({info['px'][0]} x {info['px'][1]} px, "
          f"canvas {info['canvas_cm'][0]} cm wide), font {info['font']} | overlaps: {len(info['overlaps']) or 'none'}")
    for o in info['overlaps']:
        print(f'      OVERLAP: {o}')
    # v6: one row per figure; Step 8 / 9.8 check logs read this file
    pd.DataFrame([dict(figure=name, width_cm=info['width_cm'], height_cm=info['height_cm'], canvas_width_cm=info['canvas_cm'][0],
                       n_overlaps=len(info['overlaps']), overlaps=' | '.join(info['overlaps']))]) \
        .to_csv(AUDIT, mode='a', header=not os.path.exists(AUDIT), index=False)


def nominal(ax):
    ax.axhline(0.90, color=INK, lw=0.8, ls=(0, (4, 2)), zorder=0)


res = pd.read_csv(os.path.join(RES, 'results_long.csv'))
try:
    cur = pd.read_csv(os.path.join(RES, 'curve_checks.csv'))
except pd.errors.EmptyDataError:            # Cgg target: no curve-level Vth checks
    cur = pd.DataFrame(columns=['scenario', 'nonmono_pred_above', 'nonmono_true_above', 'nonmono_pred_all',
                                'nonmono_true_all', 'vth_err_mV', 'vth_covered', 'vth_width_mV',
                                'vth_covered_pointwise'])
scs = [s for s in SC_ORDER if s in set(res.scenario)]

# ---------------- Table 1: accuracy and reliability ----------------
acc = res[res.method == 'accuracy']
t1 = acc.groupby('scenario')[['mae_dec', 'mae_dec_sub', 'mae_dec_above', 'medrel_above',
                              'auroc_sigma_err', 'frac_err_gt_flag']].agg(['mean', 'std']).round(3)
CC_COLS = ['nonmono_pred_above', 'nonmono_true_above', 'nonmono_pred_all', 'nonmono_true_all',
           'vth_err_mV', 'vth_covered', 'vth_width_mV', 'vth_covered_pointwise']
cc = cur[['scenario'] + CC_COLS].astype({c: float for c in CC_COLS}).groupby('scenario')[CC_COLS].mean().round(3)
t1.to_csv(os.path.join(OUT, 'table1_accuracy.csv')); cc.to_csv(os.path.join(OUT, 'table1b_curve_checks.csv'))

# ---------------- Table 2: coverage / width at alpha = 0.10 ----------------
a10 = res[(res.alpha == 0.10) & res.method.isin(M_ORDER)]
t2 = a10.groupby(['scenario', 'method'])[['coverage', 'cov_ci_lo', 'cov_ci_hi', 'curve_coverage', 'width_median',
                                         'worst_group_cov', 'frac_infinite']].agg(['mean', 'std']).round(3)
t2.to_csv(os.path.join(OUT, 'table2_coverage_alpha0.10.csv'))
lopo = a10[a10.scenario == 'S4_LOPO'].groupby(['fold', 'method'])['coverage'].mean().unstack().round(3)
lopo.to_csv(os.path.join(OUT, 'table3_lopo_coverage_by_pdk.csv'))

# ---------------- Figure 1: audit - stored Cgs equals gm / (2 pi f) ----------------
lg = pd.read_parquet(inp('mesd_long.parquet'),
                     columns=['pdk', 'device', 'curve_id', 'Vds_eff', 'Vgs_eff', 'Id_A', 'Cgs_F', 'Cgg_F'])
g = lg[(lg.pdk.astype(str) == 'N55A') & (lg.device.astype(str) == 'nmos1') & (lg.Vds_eff > 0)].copy()
g = g.sort_values(['curve_id', 'Vgs_eff'])
g['gm'] = g.groupby('curve_id', observed=True).apply(
    lambda d: pd.Series(np.gradient(d.Id_A.values, d.Vgs_eff.values), index=d.index)).reset_index(level=0, drop=True)
g = g[g.gm > 0].sample(min(20000, len(g)), random_state=0)
g['gm_over_2pif'] = g.gm / (2 * np.pi * 1e6)
fig, ax = fs.fig_single(0.85)
s0, s1 = fs.series(0, line=False, n=2), fs.series(1, line=False, n=2)
# rasterized=True: the 2 x 20,000 markers are embedded as a 600 dpi image inside the PDF (text,
# axes and legend stay vector), which keeps the PDF small and fast to open (v5)
ax.loglog(g.gm_over_2pif, g.Cgs_F, linestyle='none', alpha=0.35, ms=2.2, label='stored $C_{gs}$', rasterized=True, **s0)
ax.loglog(g.gm_over_2pif, g.Cgg_F, linestyle='none', alpha=0.35, ms=2.2, label='stored $C_{gg}$', rasterized=True, **s1)
lim = [g.gm_over_2pif.min(), g.gm_over_2pif.max()]
ax.plot(lim, lim, color=INK, lw=0.9, ls='--', label='$y = g_m/(2\\pi f)$')
ax.set_xlabel('$g_m/(2\\pi\\cdot 1\\,$MHz$)$ (F)'); ax.set_ylabel('stored value (F)')
_leg = fs.place_legend(ax, prefer='upper left', markerscale=2.5)[0]
for _h in getattr(_leg, 'legend_handles', None) or getattr(_leg, 'legendHandles', []):
    _h.set_alpha(1.0)          # v6: legend symbols fully opaque (the plotted points stay translucent)
save(fig, 'fig1_audit_cgs_artifact', g[['curve_id', 'Vgs_eff', 'gm_over_2pif', 'Cgs_F', 'Cgg_F']].reset_index(drop=True))

# ---------------- Figure 2: coverage by scenario, one panel per method ----------------
ms = [m for m in M_ORDER if m in set(a10.method)]
ncol = int(np.ceil(len(ms) / 2))
fig, axs = fs.fig_double(0.62, 2, ncol, sharey=True, squeeze=False)
for ax in axs.ravel()[len(ms):]:
    ax.set_visible(False)
d2 = a10.groupby(['method', 'scenario'])['coverage'].agg(['mean', 'min', 'max'])
c = fs.palette(1)[0]
ylo = min(0.0, a10.coverage.min() - 0.02)
for k, (ax, m) in enumerate(zip(axs.ravel(), ms)):
    d = d2.loc[m].reindex(scs) if m in d2.index.get_level_values(0) else None
    xs = np.arange(len(scs))
    nominal(ax)
    ax.vlines(xs, d['min'], d['max'], color=c, lw=1.2)
    ax.plot(xs, d['mean'], linestyle='none', marker='o', ms=4, color=c, markerfacecolor=c)
    ax.set_xticks(xs); ax.set_xticklabels([SC_SHORT[x] for x in scs]); ax.minorticks_off()
    ax.set_ylim(ylo, 1.17); ax.set_title(m, fontsize=plt.rcParams['font.size'] - 1)
    # v8: the infinity mark (infinite intervals = trivial coverage) goes ABOVE the marker, where no data
    # can be (coverage <= 1); the y axis has headroom to 1.17. Each mark is checked against the data
    # as it is drawn and moved further up if it touches anything (font metrics differ between machines).
    ax.set_yticks([0, 0.2, 0.4, 0.6, 0.8, 1.0])
    inf = a10[a10.method == m].groupby('scenario')['frac_infinite'].mean().reindex(scs)
    for xi, f in zip(xs, inf.values):
        if np.isfinite(f) and f > 0.5:
            for dy in (3, 5, 7, 9):
                t = ax.annotate('\u221e', (xi, d['mean'].iloc[xi]), xytext=(0, dy), textcoords='offset points',
                                ha='center', va='bottom', fontsize=8, color=INK)
                fig.canvas.draw()
                P, _ = fs._data_geometry(ax, exclude=(t,))
                if fs._hits(t.get_window_extent(fig.canvas.get_renderer()), P, [], pad=0.5)[0] == 0:
                    break
                t.remove()
    fs.panel(ax, 'abcdefgh'[k], dy=1.09)
for r in range(axs.shape[0]):
    axs[r, 0].set_ylabel('coverage')
save(fig, 'fig2_coverage_by_method', d2.round(4))

# ---------------- Figure 3: recalibration budget ----------------
rc = res[(res.alpha == 0.10) & res.method.str.match(r'^Recal-\d+$')].copy()
rc['k'] = rc.method.str.replace('Recal-', '').astype(int)
base = a10[a10.method == 'SCP-ens'].groupby('scenario')['coverage'].mean()
fig, ax = fs.fig_single(0.78)
rows3 = {}
for i, s in enumerate(scs):
    d = rc[rc.scenario == s].groupby('k')['coverage'].mean()
    if s in base.index:
        d = pd.concat([pd.Series({0: base[s]}), d])
    if len(d) == 0:
        continue
    rows3[s] = d
    ax.plot(d.index, d.values, label=SC_LABEL[s], **fs.series(i, n=len(scs)))
nominal(ax)
ax.set_xscale('symlog', linthresh=5); ax.set_xticks([0, 5, 20, 100]); ax.set_xticklabels(['0', '5', '20', '100'])
ax.xaxis.set_minor_locator(plt.NullLocator())
ax.set_xlabel('target-domain curves used for calibration, $k$'); ax.set_ylabel('coverage (nominal 0.90)')
fs.place_legend(ax, prefer='lower right')
save(fig, 'fig3_recalibration_budget', pd.DataFrame(rows3).round(4))

# ---------------- Figure 5: interval width after recalibration, absolute vs NCP scores ----------------
rw = res[(res.alpha == 0.10) & res.method.str.match(r'^(Recal|RecalNCP)-\d+$')].copy()
if len(rw):
    rw['family'] = np.where(rw.method.str.startswith('RecalNCP'), 'normalised (NCP) score', 'absolute score')
    rw['k'] = rw.method.str.split('-').str[1].astype(int)
    fig, axs = fs.fig_double(0.42, 1, 2, sharey=True)
    for j, (ax, fam) in enumerate(zip(axs, ['absolute score', 'normalised (NCP) score'])):
        for i, s in enumerate(scs):
            d = rw[(rw.scenario == s) & (rw.family == fam)].groupby('k')['width_median'].mean()
            if len(d):
                ax.plot(d.index, d.values, label=SC_LABEL[s], **fs.series(i, n=len(scs)))
        ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xticks([5, 20, 100]); ax.set_xticklabels(['5', '20', '100'])
        ax.xaxis.set_minor_locator(plt.NullLocator())
        # plain numbers; minor ticks labelled only at 2 and 5 of each decade (v6: labelling every
        # minor tick made 0.6/0.7/0.8/0.9 collide on the real Step 8 data)
        _fmt = plt.FuncFormatter(lambda v, _: f'{v:g}')
        _fmt_minor = plt.FuncFormatter(lambda v, _: f'{v:g}' if v > 0 and
                                       round(v / 10 ** np.floor(np.log10(v))) in (2, 5) else '')
        ax.yaxis.set_major_formatter(_fmt); ax.yaxis.set_minor_formatter(_fmt_minor)
        ax.set_xlabel('$k$ target curves'); ax.set_title(f'recalibrated, {fam}', fontsize=plt.rcParams['font.size'] - 1)
        fs.panel(ax, 'ab'[j], dy=1.08)
    axs[0].set_ylabel('median 90% interval width (decades)')
    fs.place_legend(axs[1], prefer='upper right')
    save(fig, 'fig5_recalibration_width', rw.groupby(['family', 'scenario', 'k'])['width_median'].mean().unstack('k').round(4))

# ---------------- Figure 4: LOPO coverage per held-out PDK, ordered by node ----------------
# PDKs are categories on the x axis (two PDKs share 45 nm and two share 180 nm, so a numeric node
# axis would draw misleading vertical joins); markers only, methods side by side.
if 'S4_LOPO' in scs:
    M4 = ['SCP-ens', 'NCP', 'CQR', 'SCP-curve']
    d = a10[(a10.scenario == 'S4_LOPO') & a10.method.isin(M4)]
    node = {p: int(''.join(ch for ch in p if ch.isdigit())) for p in d.fold.unique()}
    order = sorted(node, key=lambda p: (node[p], p))
    fig, ax = fs.fig_single(0.78)
    rows4 = {}
    xs = np.arange(len(order)); off = np.linspace(-0.24, 0.24, len(M4))
    for i, m in enumerate(M4):
        e = d[d.method == m].groupby('fold')['coverage'].mean().reindex(order)
        rows4[m] = e
        ax.plot(xs + off[i], e.values, linestyle='none', ms=4.2, label=m, **fs.series(i, line=False, n=len(M4)))
    nominal(ax)
    ax.set_xticks(xs); ax.set_xticklabels(order, rotation=45, ha='right'); ax.xaxis.set_minor_locator(plt.NullLocator())
    ax.set_xlabel('held-out PDK (ordered by node)'); ax.set_ylabel('coverage (nominal 0.90)'); ax.set_ylim(-0.02, 1.08)
    # v6: the markers fill the whole plot area, so the legend goes ABOVE the axes (keeps the full width)
    fs.place_legend(ax, prefer='lower right', outside_fallback='top', handlelength=1.2, columnspacing=1.0)
    save(fig, 'fig4_lopo_coverage_by_pdk', pd.DataFrame(rows4).assign(node_nm=[node[p] for p in order]).round(4))

# ---------------- Table 4: paired tests across the 8 held-out PDKs ----------------
# Unit = PDK fold (seeds averaged first, so folds are the independent units). Exact two-sided
# Wilcoxon signed-rank test on |coverage - 0.90| versus SCP-ens; Holm correction (Holm 1979)
# within the pre-specified primary family only.
# With n = 8 folds the smallest attainable p is 2/256 = 0.0078. S0-S3 have only one fold
# (5 seeds), where the smallest attainable Wilcoxon p is 0.0625, so no test is run there:
# report cluster-bootstrap CIs (cov_ci_lo/hi, Table 2) and the seed-to-seed SD instead.
from scipy.stats import wilcoxon
lo4 = a10[a10.scenario == 'S4_LOPO'].assign(gap=lambda d: (d.coverage - 0.90).abs()) \
         .groupby(['fold', 'method'])['gap'].mean().unstack()
tests = []
if 'SCP-ens' in lo4 and len(lo4) >= 6:
    for m in [c for c in lo4.columns if c != 'SCP-ens']:
        x = lo4[['SCP-ens', m]].dropna()
        if len(x) >= 6 and (x['SCP-ens'] != x[m]).any():
            p = wilcoxon(x['SCP-ens'], x[m], alternative='two-sided', method='exact').pvalue
            # v5: the test is two-sided, so the table must say WHICH way the difference goes.
            # 'closer' = the method's coverage is nearer to 0.90 than SCP-ens in that fold.
            n_closer = int((x[m] < x['SCP-ens']).sum())
            better = x[m].median() < x['SCP-ens'].median()
            tests.append(dict(method=m, n_folds=len(x), median_gap_SCPens=x['SCP-ens'].median(),
                              median_gap_method=x[m].median(), folds_closer_to_090=n_closer,
                              direction='closer to 0.90 than SCP-ens' if better else 'FARTHER from 0.90 than SCP-ens',
                              p_raw=p))
# Pre-specified PRIMARY family (Holm within it). With 8 folds the minimum p is 0.0078, so a
# family of 7 could never pass Holm at 0.05 (7 x 0.0078 = 0.055); 3 primary tests can.
PRIMARY = ['NCP', 'SCP-curve', 'CQR']
tt = pd.DataFrame(tests)
if len(tt):
    tt['family'] = np.where(tt.method.isin(PRIMARY), 'primary', 'exploratory (unadjusted)')
    tt['p_holm'] = np.nan
    # WCP: its "coverage" under shift comes from infinite intervals (H3), not from a usable interval
    tt['note'] = np.where(tt.method == 'WCP', 'coverage from infinite intervals; not a usable improvement', '')
    pr = tt[tt.family == 'primary'].sort_values('p_raw')
    k = len(pr)
    tt.loc[pr.index, 'p_holm'] = np.minimum(1, np.maximum.accumulate((k - np.arange(k)) * pr.p_raw.values))
    tt = tt.sort_values(['family', 'p_raw']).reset_index(drop=True)
    tt.to_csv(os.path.join(OUT, 'table4_lopo_paired_tests.csv'), index=False)
    print(tt.round(4))
else:
    print('Table 4 skipped: needs at least 6 LOPO folds (run the full S4 rotation).')

# ---------------- Figure 6: whole-curve coverage (all points of a curve inside the band) ----------------
cm = ['SCP-ens', 'NCP', 'SCP-curve']
d6 = a10[a10.method.isin(cm)].groupby(['scenario', 'method'])['curve_coverage'].mean().unstack()
if len(d6):
    fig, ax = fs.fig_single(0.78)
    xs = np.arange(len(scs)); wbar = 0.26
    cols = fs.palette(len(cm)); hatches = ['', '////', '....']
    for i, m in enumerate(cm):
        if m in d6:
            ax.bar(xs + (i - 1) * wbar, d6[m].reindex(scs).values, width=wbar - 0.02, color=cols[i],
                   edgecolor=INK, linewidth=0.5, hatch=hatches[i], label=m)
    nominal(ax)
    ax.set_xticks(xs); ax.set_xticklabels([SC_SHORT[x] for x in scs]); ax.minorticks_off()
    ax.set_xlabel('scenario'); ax.set_ylabel('fraction of curves fully inside band'); ax.set_ylim(0, 1.05)
    # bars are not checked by place_legend (it measures lines and markers), so the legend goes above the axes
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.01), ncol=3, columnspacing=1.0, handlelength=1.6)
    save(fig, 'fig6_curve_coverage', d6.reindex(scs).round(4))

print(t1); print(cc if len(cc) else '(no curve-level Vth checks for this target)'); print(t2.xs('coverage', axis=1, level=0)['mean'].unstack().round(3)); print(lopo)
print('saved to', OUT, sorted(os.listdir(OUT)))
