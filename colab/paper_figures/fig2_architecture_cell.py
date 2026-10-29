# Figure - surrogate architecture (Section 4.3) - STANDALONE Colab cell (CPU is enough, about 20 s)
# Every number in the figure is read from the study's own code and settings on Drive, not typed in:
#   code/engine/mesd_03_train_models.py : FEATS, N_ENS, HIDDEN, DEPTH, BATCH, WD, QUANTILES, MAX_GOOD_LOSS, MLP layers
#   work/main/tuning.json               : epochs, learning rate, per-square normalisation (frozen in Step 3)
#   code/engine/figstyle.py             : the paper's figure standard (batlow colours, serif text, 600 dpi PNG + PDF)
# The parameter count is computed by building the exact torch layer stack used in training.
# Output: <BASE>/figures/architecture/fig_architecture.png and .pdf (+ fig_architecture_facts.json)
import os
# BASE = the project root. In Colab this is the Drive folder; to run from a clone of the GitHub
# repository instead, set the environment variable MESD_BASE to the repository root first.
BASE = os.environ.get('MESD_BASE', '/content/drive/MyDrive/mesd_v1')
if BASE.startswith('/content/drive') and not os.path.isdir(BASE):
    from google.colab import drive; drive.mount('/content/drive')

import ast, json, os, importlib.util
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Circle, FancyArrowPatch

# ---------------- 1. read the architecture from the training code ----------------
SRC = f'{BASE}/code/engine/mesd_03_train_models.py'
tree = ast.parse(open(SRC).read())
C = {}
for node in tree.body:                                   # module-level constant assignments only
    if isinstance(node, ast.Assign):
        try:
            val = ast.literal_eval(node.value)
        except Exception:
            continue
        for t in node.targets:
            if isinstance(t, ast.Name):
                C[t.id] = val
            elif isinstance(t, ast.Tuple) and isinstance(val, tuple):
                for n_, v_ in zip(t.elts, val):
                    if isinstance(n_, ast.Name):
                        C[n_.id] = v_
FEATS, N_ENS, HIDDEN, DEPTH = C['FEATS'], C['N_ENS'], C['HIDDEN'], C['DEPTH']
BATCH, WD, QUANTILES, MAX_GOOD_LOSS = C['BATCH'], C['WD'], C['QUANTILES'], C['MAX_GOOD_LOSS']
TUNE = json.load(open(f'{BASE}/work/main/tuning.json'))
EPOCHS, LR, NORM_WL = int(TUNE['epochs']), float(TUNE['lr']), bool(TUNE['norm_wl'])
assert len(FEATS) == 15, FEATS

def n_params(d_in, d_out):
    """Parameters of the exact training network: DEPTH x [Linear(HIDDEN) + SiLU] + Linear(d_out)."""
    try:
        import torch.nn as nn
        layers, d = [], d_in
        for _ in range(DEPTH):
            layers += [nn.Linear(d, HIDDEN), nn.SiLU()]; d = HIDDEN
        layers += [nn.Linear(d, d_out)]
        return sum(p.numel() for p in nn.Sequential(*layers).parameters())
    except ImportError:                                    # same count without torch
        return (d_in + 1) * HIDDEN + (DEPTH - 1) * (HIDDEN + 1) * HIDDEN + (HIDDEN + 1) * d_out
P_ENS, P_Q = n_params(len(FEATS), 1), n_params(len(FEATS), len(QUANTILES))
FACTS = dict(n_inputs=len(FEATS), features=FEATS, n_ensemble=N_ENS, hidden=HIDDEN, depth=DEPTH,
             params_member=P_ENS, params_quantile=P_Q, epochs=EPOCHS, lr=LR, batch=BATCH, weight_decay=WD,
             quantiles=list(QUANTILES), per_square=NORM_WL, divergence_limit=MAX_GOOD_LOSS)
print(json.dumps(FACTS, indent=1))

# ---------------- 2. figure standard ----------------
spec = importlib.util.spec_from_file_location('figstyle', f'{BASE}/code/engine/figstyle.py')
fs = importlib.util.module_from_spec(spec); spec.loader.exec_module(fs)
fs.apply_style()
PAL = fs.palette(4)                                       # batlow, lightness range 0-0.75 (Kaspar & Crameri 2022)
INK, MUTED = '#1a1a1a', '#6b6b6b'

def tint(hex_c, f):
    """Mix a palette colour with white (f = share of white); keeps hue, raises lightness."""
    h = hex_c.lstrip('#'); rgb = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255
    return tuple(rgb + (1 - rgb) * f)

# feature groups, in the order of FEATS; labels are the physical meaning of each column
LBL = {'lW': r'$\log_{10}W$', 'lL': r'$\log_{10}L$', 'lNode': r'$\log_{10}$node', 'Tn': r'$T$/100 °C',
       'corner_o': r'corner (ss, tt, ff = −1, 0, 1)', 'is_p': 'PMOS flag', 'Vgs_eff': r'$V_{GS}$', 'Vds_eff': r'$V_{DS}$',
       'Vgs_n': r'$V_{GS}/V_{DD}$', 'Vds_n': r'$V_{DS}/V_{DD}$', 'Vov': r'$V_{GS}-V_{th,\mathrm{ref}}$', 'Vdd': r'$V_{DD}$',
       'Vth_ref': r'$V_{th,\mathrm{ref}}$', 'lIon_ref': r'$\log_{10}I_{on,\mathrm{ref}}$', 'lIoff_ref': r'$\log_{10}I_{off,\mathrm{ref}}$'}
GROUPS = [('geometry & node', ['lW', 'lL', 'lNode']),
          ('operating condition', ['Tn', 'corner_o', 'is_p']),
          ('bias', ['Vgs_eff', 'Vds_eff', 'Vgs_n', 'Vds_n', 'Vov', 'Vdd']),
          ('device anchors', ['Vth_ref', 'lIon_ref', 'lIoff_ref'])]
assert sorted(f for _, g in GROUPS for f in g) == sorted(FEATS), 'feature groups must cover FEATS exactly'
GCOL = {f: PAL[i] for i, (_, g) in enumerate(GROUPS) for f in g}

fig = plt.figure(figsize=(fs.W_DOUBLE, fs.W_DOUBLE * 0.60))
gsp = fig.add_gridspec(1, 3, width_ratios=[0.95, 1.6, 1.2], wspace=0.10, left=0.005, right=0.995, top=0.94, bottom=0.01)
axA, axB, axC = (fig.add_subplot(gsp[0, i]) for i in range(3))
for ax in (axA, axB, axC):
    ax.set_xlim(0, 1); ax.set_ylim(0, 1); ax.set_xticks([]); ax.set_yticks([]); ax.axis('off')
S = plt.rcParams['font.size'] - 2          # 7 pt at final size
SB = S + 1                                 # 8 pt headings

def box(ax, x, y, w, h, fc, ec, lw=0.8, r=0.02, z=2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle=f'round,pad=0,rounding_size={r}', fc=fc, ec=ec, lw=lw, zorder=z))

def arrow(ax, p0, p1, color=INK, lw=0.9, ms=7, z=3):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle='-|>', mutation_scale=ms, color=color, lw=lw, zorder=z))

def sci(v):
    m, e = f'{v:.0e}'.split('e'); return rf'{int(float(m))}\times10^{{{int(e)}}}'

# ---------------- (a) inputs ----------------
axA.text(0.0, 0.995, f'{len(FEATS)} inputs per bias point', fontsize=SB, weight='bold', va='top', color=INK)
HH, IH, GAP = 0.050, 0.043, 0.016
y = 0.935
for gi, (gname, feats) in enumerate(GROUPS):
    h = HH + IH * len(feats) + 0.010
    box(axA, 0.0, y - h, 1.0, h, tint(PAL[gi], 0.85), PAL[gi], lw=0.9)
    box(axA, 0.0, y - HH, 1.0, HH, PAL[gi], PAL[gi], lw=0.9, z=3)
    axA.text(0.05, y - HH / 2, gname, fontsize=S, color='white' if gi < 2 else INK, va='center', weight='bold', zorder=4)
    for k, f in enumerate(feats):
        yy = y - HH - IH * (k + 0.6)
        axA.scatter([0.075], [yy], s=9, c=[PAL[gi]], zorder=4, linewidths=0)
        axA.text(0.13, yy, LBL[f], fontsize=S, va='center', color=INK, zorder=4)
    y -= h + GAP

# ---------------- (b) one network of the deep ensemble ----------------
OFF = 0.014                                                   # offset of the stacked cards (other members)
cx0, cy0, cw, ch = 0.0, 0.27, 1.0 - OFF * (N_ENS - 1), 0.725 - OFF * (N_ENS - 1)
for s_ in range(N_ENS - 1, 0, -1):
    box(axB, cx0 + OFF * s_, cy0 + OFF * s_, cw, ch, tint(PAL[0], 0.80 + 0.03 * s_), tint(PAL[0], 0.35), lw=0.6, z=1)
box(axB, cx0, cy0, cw, ch, 'white', PAL[0], lw=1.1, z=2)
axB.text(cx0 + 0.03, cy0 + ch - 0.025, f'one of {N_ENS} ensemble members', fontsize=SB, weight='bold', color=INK, va='top', zorder=5)
axB.text(cx0 + 0.03, cy0 + ch - 0.075, f'identical architecture, k = 0…{N_ENS - 1}, seed 1000·s + k', fontsize=S - 0.5, color=MUTED, va='top', zorder=5)
ncol = DEPTH + 2
xs = np.linspace(cx0 + 0.07, cx0 + cw - 0.07, ncol)
ytop, ybot = cy0 + ch - 0.135, cy0 + 0.095
ymid = (ytop + ybot) / 2
yin = np.linspace(ytop, ybot, len(FEATS))
yhid = np.r_[np.linspace(ytop, ymid + 0.075, 3), np.linspace(ymid - 0.075, ybot, 3)]
cols = [yin] + [yhid] * DEPTH + [np.array([ymid])]
for a in range(ncol - 1):
    for y0 in cols[a]:
        for y1 in cols[a + 1]:
            axB.plot([xs[a], xs[a + 1]], [y0, y1], color='#a8a8a8', lw=0.22, alpha=0.55, zorder=3)
axB.scatter(np.full(len(FEATS), xs[0]), yin, s=11, c=[GCOL[f] for f in FEATS], zorder=4, edgecolors='white', linewidths=0.3)
for a in range(1, DEPTH + 1):
    axB.scatter(np.full(len(yhid), xs[a]), yhid, s=34, c='white', edgecolors=PAL[0], linewidths=0.9, zorder=4)
    axB.scatter([xs[a]] * 3, ymid + np.array([-0.03, 0, 0.03]), s=1.6, c=[PAL[0]], zorder=4)   # vertical ellipsis
    axB.text(xs[a], ybot - 0.035, f'{HIDDEN}', ha='center', va='top', fontsize=S, color=INK)
    axB.text(xs[a], ybot - 0.068, 'SiLU', ha='center', va='top', fontsize=S - 0.5, color=MUTED, style='italic')
axB.scatter([xs[-1]], [ymid], s=70, c=[PAL[3]], edgecolors=INK, linewidths=0.6, zorder=4)
axB.text(xs[-1], ymid + 0.045, r'$\hat y_k$', ha='center', va='bottom', fontsize=SB, color=INK, zorder=5)
axB.text(xs[0], ybot - 0.035, f'{len(FEATS)}', ha='center', va='top', fontsize=S, color=INK)
axB.text(xs[-1], ybot - 0.035, '1', ha='center', va='top', fontsize=S, color=INK)
axB.text(xs[-1], ybot - 0.068, 'linear', ha='center', va='top', fontsize=S - 0.5, color=MUTED, style='italic')
axB.text(0.5, 0.241, rf'MSE loss · AdamW, weight decay ${sci(WD)}$',
         ha='center', va='center', fontsize=S - 0.5, color=INK)
axB.text(0.5, 0.205, rf'one-cycle, peak lr ${sci(LR)}$ · {EPOCHS} epochs · batch {BATCH:,}',
         ha='center', va='center', fontsize=S - 0.5, color=INK)
axB.text(0.5, 0.169, f'{P_ENS:,} parameters per network',
         ha='center', va='center', fontsize=S - 0.5, color=INK)
axB.text(0.5, 0.133, f'divergence guard: retrained at lr/2 if training MSE > {MAX_GOOD_LOSS:g}',
         ha='center', va='center', fontsize=S - 0.5, color=MUTED, style='italic')
box(axB, 0.0, 0.0, 1.0, 0.105, tint(PAL[2], 0.85), PAL[2], lw=0.9)
qtxt = ', '.join(f'{q:g}' for q in QUANTILES)
axB.text(0.5, 0.071, f'+ one quantile MLP: same {DEPTH} × {HIDDEN} SiLU body, {len(QUANTILES)} outputs',
         ha='center', va='center', fontsize=S - 0.5, color=INK, zorder=5)
axB.text(0.5, 0.032, f'q = {qtxt} · pinball loss · {P_Q:,} parameters',
         ha='center', va='center', fontsize=S - 0.5, color=INK, zorder=5)

# ---------------- (c) from network outputs to intervals ----------------
axC.text(0.0, 0.995, 'outputs and intervals', fontsize=SB, weight='bold', va='top', color=INK)
box(axC, 0.0, 0.775, 1.0, 0.16, tint(PAL[0], 0.85), PAL[0], lw=0.9)
axC.text(0.05, 0.893, r'$\mu=\mathrm{mean}_k\,\hat y_k$', fontsize=SB, va='center', color=INK, zorder=5)
axC.text(0.55, 0.893, r'$\sigma=\mathrm{SD}_k\,\hat y_k$', fontsize=SB, va='center', color=INK, zorder=5)
axC.text(0.05, 0.815, r'$\hat q_{0.05},\ \hat q_{0.5},\ \hat q_{0.95}$ from the quantile MLP', fontsize=S, va='center', color=INK, zorder=5)
tgt1 = (r'$I_D$: learns $\log_{10}(I_D L/W)$, adds $\log_{10}(W/L)$' if NORM_WL else r'$I_D$: learns $\log_{10} I_D$')
axC.text(0.5, 0.738, tgt1, ha='center', va='center', fontsize=S - 0.5, color=MUTED)
axC.text(0.5, 0.700, r'$C_{gg}$: learns $\log_{10} C_{gg}$ directly', ha='center', va='center', fontsize=S - 0.5, color=MUTED)
arrow(axC, (0.5, 0.675), (0.5, 0.632))
box(axC, 0.0, 0.0, 1.0, 0.625, 'white', PAL[1], lw=1.1)
axC.text(0.5, 0.590, 'split-conformal calibration', ha='center', va='center', fontsize=SB, weight='bold', color=INK, zorder=5)
axC.text(0.5, 0.545, r'$q$ from scores on held-out calibration curves', ha='center', va='center', fontsize=S - 0.5, color=MUTED, zorder=5)
ROWS = [('SCP-ens', r'$\mu \pm q$', r'score $|y-\mu|$'),
        ('NCP', r'$\mu \pm q\,\sigma$', r'score $|y-\mu|/\sigma$'),
        ('SCP-curve', r'$\mu \pm q_c\,\sigma$', r'max over curve of $|y-\mu|/\sigma$'),
        ('CQR', r'$[\hat q_{0.05}-q,\ \hat q_{0.95}+q]$', 'quantile-based score'),
        ('Ens-Gauss', r'$\mu \pm 1.645\,\sigma$', 'not calibrated')]
yy = 0.465
for i, (name, form, note) in enumerate(ROWS):
    if i % 2 == 0:
        box(axC, 0.03, yy - 0.047, 0.94, 0.088, tint(PAL[1], 0.86), 'none', lw=0, r=0.012, z=3)
    axC.text(0.06, yy + 0.010, name, fontsize=S, weight='bold', va='center', color=INK, zorder=5)
    axC.text(0.38, yy + 0.010, form, fontsize=S, va='center', color=INK, zorder=5)
    axC.text(0.38, yy - 0.026, note, fontsize=S - 1, va='center', color=MUTED, zorder=5)
    yy -= 0.090
for ax, letter in zip((axA, axB, axC), 'abc'):
    fs.panel(ax, letter, dy=1.005)
for (a0, a1, lab) in [(axA, axB, 'standardized\n(train stats)'), (axB, axC, '')]:
    b0, b1 = a0.get_position(), a1.get_position()
    ym = b0.y0 + 0.62 * b0.height
    fig.patches.append(FancyArrowPatch((b0.x1 + 0.002, ym), (b1.x0 - 0.002, ym), transform=fig.transFigure,
                                       arrowstyle='-|>', mutation_scale=9, color=INK, lw=1.0))
OUT = f'{BASE}/figures/architecture'
os.makedirs(OUT, exist_ok=True)
# text must stay inside its own panel (panel letters excepted)
fig.canvas.draw(); _r = fig.canvas.get_renderer(); spill = []
for ax in (axA, axB, axC):
    ab = ax.get_window_extent(_r)
    for t in ax.texts:
        if t.get_text().startswith('('):
            continue
        tb = t.get_window_extent(_r)
        if tb.x0 < ab.x0 - 1 or tb.x1 > ab.x1 + 1 or tb.y0 < ab.y0 - 1 or tb.y1 > ab.y1 + 1:
            spill.append(t.get_text())
info = fs.save_fig(fig, 'fig_architecture', OUT, close=False)
info['overlaps'] += [f'text outside its panel: {t}' for t in spill]
json.dump(FACTS, open(f'{OUT}/fig_architecture_facts.json', 'w'), indent=1)
print(f"saved {info['png']} and .pdf | {info['width_cm']} x {info['height_cm']} cm | font {info['font']} | "
      f"overlaps: {len(info['overlaps']) or 'none'}")
for o in info['overlaps']:
    print('  OVERLAP:', o)
plt.show()
