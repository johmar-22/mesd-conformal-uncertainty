# ===================================================================================================
# MESD paper: Figure 6 (median width of the recalibrated 90% intervals, log10 I_D).
# STANDALONE Colab cell (CPU, a few seconds). Paste the whole file into one cell and run it.
#
# Same plotting code as code/engine/mesd_05_figures_tables.py ("Figure 5: interval width after
# recalibration") and the same figstyle.py; the only change is the US spelling "normalized" in the
# panel (b) title, to match the paper. Nothing is recomputed: the plotted numbers are read from the
# frozen figure-data file results/Id/fig5_recalibration_width_data.csv.
#
# Output: BASE/figures/paper_combined/fig6_recalibration_width.png and .pdf
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
_spec = importlib.util.spec_from_file_location('figstyle', os.path.join(BASE, 'code', 'engine', 'figstyle.py'))
fs = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(fs)
fs.apply_style()

DATA = os.path.join(BASE, 'results', 'Id', 'fig5_recalibration_width_data.csv')
rw = pd.read_csv(DATA)
SC = ['S0_random', 'S1_Lextreme', 'S2_T125', 'S3_ff', 'S4_LOPO']
LBL = {'S0_random': 'S0 random', 'S1_Lextreme': 'S1 L-extreme', 'S2_T125': 'S2 125 °C',
       'S3_ff': 'S3 ff corner', 'S4_LOPO': 'S4 new PDK'}
FAMILIES = [('absolute score', 'absolute score'), ('normalised (NCP) score', 'normalized (NCP) score')]   # (key in data file, title)
assert set(rw.family) == {f for f, _ in FAMILIES}, f'unexpected families in {DATA}: {set(rw.family)}'

fig, axs = fs.fig_double(0.42, 1, 2, sharey=True)
for j, (ax, (fam, title)) in enumerate(zip(axs, FAMILIES)):
    for i, s in enumerate(SC):
        row = rw[(rw.family == fam) & (rw.scenario == s)]
        if len(row):
            ks = [5, 20, 100]
            ax.plot(ks, [float(row[str(k)].iloc[0]) for k in ks], label=LBL[s], **fs.series(i, n=len(SC)))
    ax.set_xscale('log'); ax.set_yscale('log'); ax.set_xticks([5, 20, 100]); ax.set_xticklabels(['5', '20', '100'])
    ax.xaxis.set_minor_locator(plt.NullLocator())
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f'{v:g}'))
    ax.yaxis.set_minor_formatter(plt.FuncFormatter(
        lambda v, _: f'{v:g}' if v > 0 and round(v / 10 ** np.floor(np.log10(v))) in (2, 5) else ''))
    ax.set_xlabel('$k$ target curves'); ax.set_title(f'recalibrated, {title}', fontsize=plt.rcParams['font.size'] - 1)
    fs.panel(ax, 'ab'[j], dy=1.08)
axs[0].set_ylabel('median 90% interval width (decades)')
fs.place_legend(axs[1], prefer='upper right')
info = fs.save_fig(fig, 'fig6_recalibration_width', OUT)
print(f"saved {info['png']} and .pdf | {info['width_cm']} x {info['height_cm']} cm | overlaps: {len(info['overlaps']) or 'none'}")
