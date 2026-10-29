# ===================================================================================================
# MESD paper: Figures 4 and 5 as ONE image each, two panels side by side, labelled (a) and (b).
# STANDALONE Colab cell (CPU, about 20 s). Paste the whole file into one cell and run it.
#
# Nothing is recomputed. Each panel is drawn from the frozen figure-data file that the engine wrote
# next to the original single figure (<figure>_data.csv = exactly the plotted numbers), with the SAME
# plotting code as code/engine/mesd_05_figures_tables.py (code v10) and the SAME figstyle.py.
# Each panel keeps the size of the original single-column figure (8.5 cm x 0.78), so markers, fonts,
# axes and legends are unchanged, with two exceptions: the (a)/(b) labels are added, and the legend of
# Figure 4a moves above its axes because inside it hid one data point (see draw_lopo).
#
#   Paper Figure 4 = (a) fig4_lopo_coverage_by_pdk (I_D)      + (b) fig6_curve_coverage (I_D)
#   Paper Figure 5 = (a) fig3_recalibration_budget (I_D)      + (b) fig3_recalibration_budget (C_gg)
#
# Output: BASE/figures/paper_combined/  fig3_lopo_and_curve_coverage.png/.pdf
#                                       fig4_recalibration_budget_Id_Cgg.png/.pdf
# ===================================================================================================
import os
# BASE = the project root. In Colab this is the Drive folder; to run from a clone of the GitHub
# repository instead, set the environment variable MESD_BASE to the repository root first.
BASE = os.environ.get('MESD_BASE', '/content/drive/MyDrive/mesd_v1')
if BASE.startswith('/content/drive') and not os.path.isdir(BASE):
    from google.colab import drive; drive.mount('/content/drive')

import os, importlib.util
import numpy as np, pandas as pd
import matplotlib.pyplot as plt

OUT = os.path.join(BASE, 'figures', 'paper_combined'); os.makedirs(OUT, exist_ok=True)

# ---------- the paper's figure standard (same file the engine used) ----------
_spec = importlib.util.spec_from_file_location('figstyle', os.path.join(BASE, 'code', 'engine', 'figstyle.py'))
fs = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(fs)
fs.apply_style()

# ---------- constants copied verbatim from mesd_05_figures_tables.py ----------
INK = '#000000'
SC_ORDER = ['S0_random', 'S1_Lextreme', 'S2_T125', 'S3_ff', 'S4_LOPO']
SC_LABEL = {'S0_random': 'S0 random', 'S1_Lextreme': 'S1 L-extreme', 'S2_T125': 'S2 125 °C',
            'S3_ff': 'S3 ff corner', 'S4_LOPO': 'S4 new PDK'}
SC_SHORT = {'S0_random': 'S0', 'S1_Lextreme': 'S1', 'S2_T125': 'S2', 'S3_ff': 'S3', 'S4_LOPO': 'S4'}


def nominal(ax):
    ax.axhline(0.90, color=INK, lw=0.8, ls=(0, (4, 2)), zorder=0)


def data_file(target, name):
    """Frozen figure data: BASE/results/<Id|Cgg>/ (published copy), else the original in work/main/paper/."""
    tdir = {'Id': 'y_logId', 'Cgg': 'y_logCgg'}[target]
    for p in (os.path.join(BASE, 'results', target, name + '_data.csv'),
              os.path.join(BASE, 'work', 'main', 'paper', tdir, name + '_data.csv')):
        if os.path.isfile(p):
            print('reading', p)
            return pd.read_csv(p, index_col=0)
    raise FileNotFoundError(f'{name}_data.csv for {target} not found in results/{target}/ or work/main/paper/{tdir}/')


def pair_figure():
    """Two original single-column panels (8.5 cm wide, height ratio 0.78) next to each other."""
    fs.apply_style()
    return plt.subplots(1, 2, figsize=(2 * fs.W_SINGLE, fs.W_SINGLE * 0.78), constrained_layout=True)


def label_panels(fig, axs):
    """(a), (b) at the SAME height above both panels, just clear of anything drawn above the axes
    (the legend of a panel whose legend sits on top), as in the other figures (figstyle.panel)."""
    fig.canvas.draw()
    r = fig.canvas.get_renderer()
    dy = 1.015
    for ax in axs:
        h_ax = ax.get_window_extent(r).height
        top_ax = ax.get_window_extent(r).y1
        leg = ax.get_legend()
        if leg is not None:
            bb = leg.get_window_extent(r)
            if bb.y0 >= top_ax - 1:                               # legend above the plot area
                dy = max(dy, 1 + (bb.y1 - top_ax) / h_ax + 0.015)
    for ax, letter in zip(axs, 'ab'):
        fs.panel(ax, letter, dy=dy)


def save(fig, name):
    info = fs.save_fig(fig, name, OUT)
    print(f"saved {info['png']} and .pdf | {info['width_cm']} x {info['height_cm']} cm | "
          f"font {info['font']} | overlaps: {len(info['overlaps']) or 'none'}")
    for o in info['overlaps']:
        print('   OVERLAP:', o)
    return info


# ---------- panel bodies: identical to mesd_05_figures_tables.py ----------
def draw_recal(ax, r3):                                       # engine "Figure 3: recalibration budget"
    scs = [s for s in SC_ORDER if s in r3.columns]
    for i, s in enumerate(scs):
        d = r3[s].dropna()
        ax.plot(d.index, d.values, label=SC_LABEL[s], **fs.series(i, n=len(scs)))
    nominal(ax)
    ax.set_xscale('symlog', linthresh=5); ax.set_xticks([0, 5, 20, 100]); ax.set_xticklabels(['0', '5', '20', '100'])
    ax.xaxis.set_minor_locator(plt.NullLocator())
    ax.set_xlabel('target-domain curves used for calibration, $k$'); ax.set_ylabel('coverage (nominal 0.90)')
    fs.place_legend(ax, prefer='lower right')


def draw_lopo(ax, d4):                                        # engine "Figure 4: LOPO coverage per PDK"
    M4 = ['SCP-ens', 'NCP', 'CQR', 'SCP-curve']
    order = list(d4.index)                                    # already ordered by node in the data file
    xs = np.arange(len(order)); off = np.linspace(-0.24, 0.24, len(M4))
    for i, m in enumerate(M4):
        ax.plot(xs + off[i], d4[m].values, linestyle='none', ms=4.2, label=m, **fs.series(i, line=False, n=len(M4)))
    nominal(ax)
    ax.set_xticks(xs); ax.set_xticklabels(order, rotation=45, ha='right'); ax.xaxis.set_minor_locator(plt.NullLocator())
    ax.set_xlabel('held-out PDK (ordered by node)'); ax.set_ylabel('coverage (nominal 0.90)'); ax.set_ylim(-0.02, 1.08)
    # The only change from the engine: the engine's place_legend kept this legend INSIDE (lower right),
    # where its box hides the NCP marker of N180B (0.746); the overlap audit flags it. The legend is
    # therefore drawn where place_legend's own fallback puts it: above the axes, frameless, 4 columns.
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.02), ncol=len(M4), frameon=False, borderaxespad=0.0,
              handlelength=1.2, columnspacing=1.0)


def draw_curve(ax, d6):                                       # engine "Figure 6: whole-curve coverage"
    scs = [s for s in SC_ORDER if s in d6.index]
    cm = ['SCP-ens', 'NCP', 'SCP-curve']
    xs = np.arange(len(scs)); wbar = 0.26
    cols = fs.palette(len(cm)); hatches = ['', '////', '....']
    for i, m in enumerate(cm):
        if m in d6:
            ax.bar(xs + (i - 1) * wbar, d6[m].reindex(scs).values, width=wbar - 0.02, color=cols[i],
                   edgecolor=INK, linewidth=0.5, hatch=hatches[i], label=m)
    nominal(ax)
    ax.set_xticks(xs); ax.set_xticklabels([SC_SHORT[x] for x in scs]); ax.minorticks_off()
    ax.set_xlabel('split'); ax.set_ylabel('fraction of curves fully inside band'); ax.set_ylim(0, 1.05)
    ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1.01), ncol=3, columnspacing=1.0, handlelength=1.6)


# ---------- load the frozen data ----------
d4 = data_file('Id', 'fig4_lopo_coverage_by_pdk')
d6 = data_file('Id', 'fig6_curve_coverage')
r3_id = data_file('Id', 'fig3_recalibration_budget')
r3_cgg = data_file('Cgg', 'fig3_recalibration_budget')
assert list(d4.index) == sorted(d4.index, key=lambda p: (int(''.join(c for c in p if c.isdigit())), p)), 'PDK order changed'
assert {'SCP-ens', 'NCP', 'CQR', 'SCP-curve'} <= set(d4.columns) and {'SCP-ens', 'NCP', 'SCP-curve'} <= set(d6.columns)
assert list(r3_id.index) == list(r3_cgg.index) == [0, 5, 20, 100], 'unexpected k values'

# ---------- paper Figure 4: (a) LOPO coverage per PDK, (b) whole-curve coverage ----------
fig, axs = pair_figure()
draw_lopo(axs[0], d4)
draw_curve(axs[1], d6)
label_panels(fig, axs)
i3 = save(fig, 'fig3_lopo_and_curve_coverage')

# ---------- paper Figure 5: recalibration budget, (a) I_D, (b) C_gg ----------
fig, axs = pair_figure()
draw_recal(axs[0], r3_id)
draw_recal(axs[1], r3_cgg)
label_panels(fig, axs)
i4 = save(fig, 'fig4_recalibration_budget_Id_Cgg')

print('PASS' if not (i3['overlaps'] or i4['overlaps']) else 'CHECK the overlaps listed above')
try:                                   # inline preview in Colab/Jupyter; skipped when run as a plain script
    from IPython.display import Image as _Img, display
    for i in (i3, i4):
        display(_Img(filename=i['png'], width=900))
except ImportError:
    pass
