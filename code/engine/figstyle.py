"""figstyle.py - one figure standard (author's thesis figstyle, Execution Plan v9.4), adopted for the
MESD study in code v4. Changes for MESD are marked "MESD v4" / "MESD v6"; everything else is unchanged.
MESD v6: legends inside the plot area sit in a thin-bordered opaque box placed where it covers no data
(else outside the axes), and save_fig() audits every figure for overlaps and reports the real file size.

Journal requirements implemented here (IOP-style author guidance):
  * single-column figures 8.5 cm wide, double-column 15 cm; text 8-12 pt AT FINAL SIZE;
  * a Times New Roman-like serif face for every character, matching the body text;
  * raster output at 600 dpi (plus a vector PDF of the same figure);
  * information never carried by colour alone: every series also differs in line style and marker,
    and the colour set stays distinguishable in greyscale;
  * panel labels as (a), (b), ... inside the axes;
  * micrographs carry a scale bar (scalebar() below).

Usage:
    import figstyle as fs
    fig, ax = fs.fig_single()          # or fs.fig_double(), fs.fig_grid(1, 2)
    ax.plot(x, y, **fs.series(0), label='route D')
    fs.panel(ax, 'a'); ax.legend()
    fs.save_fig(fig, 'fig_route_yields')      # writes .png (600 dpi) and .pdf into BASE/figures
"""
from __future__ import annotations
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties, findfont
from matplotlib.lines import Line2D

CM = 1 / 2.54
W_SINGLE = 8.5 * CM          # 3.346 in
W_DOUBLE = 15.0 * CM         # 5.906 in
DPI_RASTER = 600

# Times New Roman and its metric-compatible clones, then matplotlib's own Times-like face.
SERIF_STACK = ['Times New Roman', 'Nimbus Roman', 'Nimbus Roman No9 L', 'Liberation Serif',
               'Tinos', 'FreeSerif', 'STIXGeneral', 'DejaVu Serif']

# MESD v4 - colours follow Kaspar & Crameri, Angew. Chem. Int. Ed. 61 (2022) e202114910
# ("Coloring chemistry - how mindful color choices improve chemical communication"):
#   (1) the figure must stay fully comprehensible in greyscale (colour is optional): every series
#       also differs in line style and marker, and colours are taken with MONOTONIC lightness;
#   (2) where colour codes information, use a perceptually uniform, perceptually ordered scientific
#       colour map (batlow, viridis, cividis ...), never rainbow/jet and never red-green pairs;
#   (3) the plotted data are also provided as tables (the CSV files written next to every figure).
# Discrete series colours are therefore sampled from Crameri's 'batlow' map (perceptually uniform,
# colour-vision-deficiency friendly, lightness rising monotonically from dark blue to light pink;
# Crameri, Scientific colour maps, Zenodo doi:10.5281/zenodo.1243862; Crameri, Shephard & Heron,
# Nat. Commun. 11 (2020) 5444). The 256-step table below was exported from cmcrameri 1.8 (MIT
# licence), so no extra package is needed in Colab.
_BATLOW_HEX = ('011959021b59031c5a041e5a051f5a06215b07225b07245b08255b09275c0a285c0a2a5c0b2b5c0b2d5d0c2e5d0c2f5d0d315d0d325e0d335e0e355e0e365e0e375e0f385f0f395f0f3b5f0f3c5f103d5f103e5f103f60104060114160114260114360114460124561124661124761124861134961134a61134b61144c62144d62144e62154f62154f621650621651621752621753621854621855621956621957621a57621b58621b59621c5a621d5b621e5c621e5d621f5d61205e61215f6122606123606024616025626026635f27635f28645f2a655e2b655e2c665d2d675d2f675c30685c31695b33695a346a5a356a59376b58386c583a6c573b6d563c6d563e6e553f6e54416f53426f5244705245705147715048714f4a724e4c724d4d734d4f734c50744b52744a5375495575485776475876465a77455b77455d78445f7843607942627941637a40657a3f677b3e687b3e6a7b3d6c7c3c6d7c3b6f7d3a717d39737e38747e38767f37787f367980357b80347d81347f813381823282823184833186833088842f8a842f8c852e8e852e8f862d91862d93872c95872c97882c99882c9b892b9d892b9f892ba18a2ba38a2ca58b2ca78b2ca98c2cab8c2dad8c2daf8d2eb18d2fb38e2fb58e30b78e31b98f32bb8f33bd8f34be9035c09036c29037c49138c6913ac8913bca923ccb923ecd923fcf9340d19342d29343d49445d69446d89448d9954adb954bdd954dde964fe09651e19752e39754e49756e69858e7985ae9995cea995eeb9a60ed9a62ee9b64ef9b67f09c69f19d6bf29d6df39e70f49f72f59f74f6a077f7a179f8a17bf8a27ef9a380f9a382faa485faa587fba689fba68cfca78efca890fca993fca995fdaa97fdab9afdac9cfdac9efdada0fdaea2fdafa5fdafa7fdb0a9fdb1abfdb2adfdb2affdb3b1fdb4b4fdb4b6fdb5b8fdb6bafdb7bcfdb7befdb8c0fdb9c2fdbac4fdbac7fdbbc9fdbccbfdbccdfcbdcffcbed1fcbfd3fcbfd6fcc0d8fcc1dafcc2dcfcc3dffcc3e1fcc4e3fcc5e5fbc6e8fbc6eafbc7ecfbc8effbc9f1fbcaf3fbcaf6facbf8faccfa')
BATLOW = ['#' + _BATLOW_HEX[i:i + 6] for i in range(0, len(_BATLOW_HEX), 6)]
SAMPLE_RANGE = (0.0, 0.75)      # the lightest quarter (pale pink) is skipped: too little contrast on white


def palette(n: int) -> list:
    """n colours evenly spaced along batlow (dark -> light), so they are ordered by lightness and
    remain distinguishable in greyscale and for colour-vision deficiencies."""
    import numpy as np
    if n <= 1:
        return [BATLOW[0]]
    pos = np.linspace(SAMPLE_RANGE[0], SAMPLE_RANGE[1], n)
    return [BATLOW[int(round(p * 255))] for p in pos]


def batlow_cmap():
    """Continuous batlow colormap for colour-coded quantities (heatmaps, scatter colour)."""
    from matplotlib.colors import ListedColormap
    return ListedColormap(BATLOW, name='batlow')


COLORS = palette(7)              # default 7-colour set (series(i) without n)
LINESTYLES = ['-', '--', ':', '-.', (0, (5, 1, 1, 1)), (0, (3, 1, 1, 1, 1, 1)), (0, (1, 1))]
MARKERS = ['o', 's', '^', 'D', 'v', 'P', 'X']


def refresh_fonts():
    """Call once after installing new system fonts (matplotlib caches the font list)."""
    import os, shutil, matplotlib as mpl
    from matplotlib import font_manager
    cache = mpl.get_cachedir()
    shutil.rmtree(cache, ignore_errors=True)
    os.makedirs(cache, exist_ok=True)        # matplotlib needs the directory back before it rebuilds the list
    try:
        font_manager._load_fontmanager(try_read_cache=False)
    except Exception:
        font_manager.fontManager.__init__()
    apply_style()
    return font_in_use()


def font_in_use() -> str:
    """The serif face matplotlib actually resolved (report it in the thesis appendix)."""
    return FontProperties(fname=findfont(FontProperties(family='serif'))).get_name()


def apply_style(base_pt: float = 9.0) -> dict:
    """Set the journal defaults. Text is 8-12 pt at final size because the figure is created at
    final size (no scaling in the manuscript)."""
    plt.rcParams.update({
        'font.family': 'serif', 'font.serif': SERIF_STACK, 'mathtext.fontset': 'stix',
        'font.size': base_pt, 'axes.labelsize': base_pt, 'axes.titlesize': base_pt,
        'xtick.labelsize': base_pt - 1, 'ytick.labelsize': base_pt - 1, 'legend.fontsize': base_pt - 1,
        'figure.titlesize': base_pt + 1,
        'axes.linewidth': 0.6, 'lines.linewidth': 1.1, 'lines.markersize': 3.6,
        'xtick.direction': 'in', 'ytick.direction': 'in', 'xtick.top': True, 'ytick.right': True,
        'xtick.major.width': 0.6, 'ytick.major.width': 0.6,
        'xtick.minor.visible': True, 'ytick.minor.visible': True,
        'legend.frameon': False, 'legend.handlelength': 2.6, 'legend.borderaxespad': 0.4,
        'axes.grid': False, 'axes.spines.top': True, 'axes.spines.right': True,
        'figure.dpi': 150, 'savefig.dpi': DPI_RASTER, 'savefig.bbox': 'tight', 'savefig.pad_inches': 0.02,
        'pdf.fonttype': 42, 'ps.fonttype': 42,        # embed real TrueType text, never outlines
        'errorbar.capsize': 2.0,
    })
    return dict(font=font_in_use(), base_pt=base_pt, dpi=DPI_RASTER)


def series(i: int, line: bool = True, marker: bool = True, n: int | None = None) -> dict:
    """Style of series i: colour AND line style AND marker, so the figure survives greyscale printing.
    MESD v4: pass n (number of series in the panel) to spread the colours over the whole batlow range."""
    cols = palette(n) if n else COLORS
    d = {'color': cols[i % len(cols)]}
    if line:
        d['linestyle'] = LINESTYLES[i % len(LINESTYLES)]
    if marker:
        d['marker'] = MARKERS[i % len(MARKERS)]
        d['markerfacecolor'] = 'none' if i % 2 else d['color']
        d['markeredgewidth'] = 0.8
    return d


def _fig(width, h_ratio, nrows, ncols, **kw):
    apply_style()
    fig, ax = plt.subplots(nrows, ncols, figsize=(width, width * h_ratio), constrained_layout=True, **kw)
    return fig, ax


def fig_single(h_ratio: float = 0.78, nrows: int = 1, ncols: int = 1, **kw):
    """8.5 cm wide figure (single column)."""
    return _fig(W_SINGLE, h_ratio, nrows, ncols, **kw)


def fig_double(h_ratio: float = 0.45, nrows: int = 1, ncols: int = 1, **kw):
    """15 cm wide figure (double column / full page width)."""
    return _fig(W_DOUBLE, h_ratio, nrows, ncols, **kw)


def panel(ax, letter: str, dx: float = 0.0, dy: float = 1.015, **kw):
    """Panel label as (a), (b), ... just ABOVE the top-left corner, OUTSIDE the plot area.

    v10.38.  It used to sit INSIDE the axes at (0.02, 0.97), where on a figure whose data rises to
    the top left - which is most of them - it lands on the curve.  Journal house style puts the
    letter outside the frame anyway, so it now sits immediately above the top-left corner: outside
    the plot area, but close enough that it still reads as that panel's label and not as a title.

    clip_on is off because an artist in axes coordinates above 1.0 is outside the axes patch and
    would otherwise be clipped away entirely.  savefig(bbox='tight') expands the canvas to include
    it, so nothing is cut off at the top of the page either.
    """
    t = ax.text(dx, dy, f'({letter})', transform=ax.transAxes, va='bottom', ha='left',
                fontsize=plt.rcParams['font.size'], **kw)
    t.set_clip_on(False)
    return ax


# Candidate legend positions, tried in this order when the requested one sits on top of the data.
LEGEND_LOCS = ['best', 'upper right', 'upper left', 'lower left', 'lower right',
               'center right', 'center left', 'upper center', 'lower center', 'center']

# MESD v6: a legend INSIDE the plot area sits in a box with a thin border and an opaque white fill, so
# it reads as separate from the data.  borderaxespad 0.9 (x font size) keeps the box clear of the
# inward ticks (major tick 3.5 pt < 0.9 x 8 pt = 7.2 pt).  Legends OUTSIDE the axes stay frameless.
LEGEND_BOX = dict(frameon=True, framealpha=1.0, fancybox=False, edgecolor='0.15', facecolor='white',
                  borderpad=0.4, borderaxespad=0.9)
LEGEND_BOX_LW = 0.5      # points


def _densify(d, step=1.5):
    """Points every `step` display pixels along a polyline, so a LINE crossing a box is detected even
    when none of its vertices lies inside (v6; v4 tested vertices only)."""
    import numpy as np
    out = [d[:1]]
    for p0, p1 in zip(d[:-1], d[1:]):
        n = int(np.hypot(*(p1 - p0)) / step) + 1
        out.append(p0 + (p1 - p0) * np.linspace(0, 1, n + 1)[1:, None])
    return np.concatenate(out)


def _data_geometry(ax, exclude=()):
    """Everything plotted on `ax`, in display coordinates: an (N, 2) array of points (markers, line
    vertices and densified line segments, scatter offsets, LineCollection segments) and a list of
    Bbox for bars/patches and texts drawn inside the axes.  Each artist's OWN transform is used, so
    axhline/axvline (blended transforms) are handled correctly (v4 used transData for everything)."""
    import numpy as np
    from matplotlib.collections import LineCollection
    fig = ax.get_figure(); rend = fig.canvas.get_renderer()
    pts, boxes = [], []
    for ln in ax.get_lines():
        if not ln.get_visible() or ln in exclude:
            continue
        xy = ln.get_xydata()
        if xy is None or len(xy) == 0:
            continue
        d = ln.get_transform().transform(np.asarray(xy, float))
        d = d[np.isfinite(d).all(axis=1)]
        if not len(d):
            continue
        pts.append(d)
        if ln.get_linestyle() not in ('None', 'none', '', ' ') and len(d) > 1:
            pts.append(_densify(d))
    for col in ax.collections:
        if not col.get_visible() or col in exclude:
            continue
        if isinstance(col, LineCollection):
            for seg in col.get_segments():
                d = col.get_transform().transform(np.asarray(seg, float))
                d = d[np.isfinite(d).all(axis=1)]
                if len(d) > 1:
                    pts.append(_densify(d))
            continue
        try:
            off = col.get_offsets()
        except Exception:
            continue
        if off is None or len(off) == 0:
            continue
        d = col.get_offset_transform().transform(np.asarray(off, float))
        pts.append(d[np.isfinite(d).all(axis=1)])
    for pa in ax.patches:
        if pa.get_visible() and pa not in exclude:
            boxes.append(pa.get_window_extent(rend))
    for t in ax.texts:
        if t.get_visible() and t.get_text().strip() and t not in exclude:
            boxes.append(t.get_window_extent(rend))
    P = np.concatenate(pts) if pts else np.zeros((0, 2))
    return P, boxes


def _hits(bb, P, boxes, pad=4.0):
    """(points inside bb padded by `pad` pt, number of boxes intersecting bb)."""
    b = bb.padded(pad)
    n = int(((P[:, 0] >= b.x0) & (P[:, 0] <= b.x1) & (P[:, 1] >= b.y0) & (P[:, 1] <= b.y1)).sum()) if len(P) else 0
    return n, sum(1 for o in boxes if o.overlaps(bb))


def legend_data_cover(ax, leg) -> float:
    """Fraction of the axes' plotted points (incl. line segments) under this legend box; any bar or
    text under the legend counts as full cover (1.0)."""
    fig = ax.get_figure(); fig.canvas.draw()
    try:
        bb = leg.get_window_extent(renderer=fig.canvas.get_renderer())
    except Exception:
        return 0.0
    P, boxes = _data_geometry(ax)
    n, nb = _hits(bb, P, boxes)
    if nb:
        return 1.0
    return (n / len(P)) if len(P) else 0.0


def _style_box(leg, inside=True):
    if inside and leg.get_frame_on():
        leg.get_frame().set_linewidth(LEGEND_BOX_LW)
    return leg


def place_legend(ax, handles=None, labels=None, prefer='best', tol: float = 0.0, box: bool = True,
                 outside_fallback: str = 'right', **kw):
    """Draw a legend inside the axes where it covers NO data, in a thin-bordered box (v6).

    Tries `prefer` first, then the other positions, each with the requested number of columns and
    then 1 and 2 columns.  The first position whose box covers no marker, line, bar or text is kept.
    If no inside position is clear, the legend is moved OUTSIDE the axes (`outside_fallback`:
    'right' or 'top'; frameless), so it never sits on the data.  Returns
    (legend, loc_used, cover_used, cover_requested).
    """
    if box:
        kw = {**LEGEND_BOX, **kw}
    nent = len(labels) if labels is not None else len(ax.get_legend_handles_labels()[1])
    ncols = []
    for c in [kw.pop('ncol', 1), 1, 2]:
        if c not in ncols and c <= max(nent, 1):
            ncols.append(c)

    def draw(loc, nc, **extra):
        args = (handles, labels) if handles is not None else ()
        return ax.legend(*args, loc=loc, ncol=nc, **{**kw, **extra})

    tried = [prefer] + [l for l in LEGEND_LOCS if l != prefer]
    cov_pref = None
    for loc in tried:
        for nc in ncols:
            leg = draw(loc, nc)
            cov = legend_data_cover(ax, leg)
            if cov_pref is None:
                cov_pref = cov
            if cov <= tol:
                return _style_box(leg), loc, cov, cov_pref
            leg.remove()
    # no clear spot inside: put it outside the plot area (never over the data)
    out = {k: v for k, v in kw.items() if k not in LEGEND_BOX}
    if outside_fallback == 'top':
        leg = ax.legend(*((handles, labels) if handles is not None else ()), loc='lower center',
                        bbox_to_anchor=(0.5, 1.02), ncol=min(nent, 4), frameon=False, borderaxespad=0.0, **out)
        return leg, 'outside top', 0.0, cov_pref
    leg = ax.legend(*((handles, labels) if handles is not None else ()), loc='center left',
                    bbox_to_anchor=(1.02, 0.5), ncol=1, frameon=False, borderaxespad=0.0, **out)
    return leg, 'outside right', 0.0, cov_pref


def _drawn_ticklabels(axis):
    """Tick labels that are actually DRAWN (inside the view limits). get_ticklabels() also returns
    labels of ticks outside the limits, which are never drawn and must not count as overlaps."""
    try:
        ticks = axis._update_ticks()                     # the ticks Axis.draw() will render
        return [lab for t in ticks for lab in (t.label1, t.label2) if lab.get_visible()]
    except Exception:
        lo, hi = sorted(axis.get_view_interval())
        locs = list(axis.get_majorticklocs()); labs = axis.get_majorticklabels()
        return [l for x, l in zip(locs, labs) if lo - 1e-12 <= x <= hi + 1e-12]


def audit_overlaps(fig) -> list:
    """List every overlap in a finished figure (v6).  Empty list = clean.  Checks:
    (1) legends inside an axes vs that axes' data (markers, lines incl. segments, bars, texts);
    (2) every pair of visible texts/legends in the figure (tick labels, axis labels, titles, panel
        labels, annotations, legends) by bounding box; rotated tick labels of one axis are tested by
        their spacing instead, because their axis-aligned boxes overlap even when the glyphs do not;
    (3) annotations inside an axes vs that axes' data points."""
    import numpy as np
    fig.canvas.draw(); rend = fig.canvas.get_renderer()
    issues, items = [], []          # items: (label, bbox, group)
    for k, ax in enumerate(fig.axes):
        if not ax.get_visible():
            continue
        tag = f'axes{k}' + (f" '{ax.get_title()}'" if ax.get_title() else '')
        abb = ax.get_window_extent(rend)
        leg = ax.get_legend()
        P, boxes = _data_geometry(ax)
        if leg is not None and leg.get_visible():
            lbb = leg.get_window_extent(rend)
            if abb.overlaps(lbb) and abb.x0 <= lbb.x0 + 1 and lbb.x1 <= abb.x1 + 1 and abb.y0 <= lbb.y0 + 1 and lbb.y1 <= abb.y1 + 1:
                n, nb = _hits(lbb, P, boxes, pad=2.0)
                if n or nb:
                    issues.append(f'{tag}: legend covers {n} data points and {nb} bars/texts')
            items.append((f'{tag} legend', lbb, f'{k}:legend'))
        for t in ax.texts:
            if t.get_visible() and t.get_text().strip():
                tb = t.get_window_extent(rend)
                items.append((f"{tag} text '{t.get_text()}'", tb, f'{k}:text{id(t)}'))
                if abb.overlaps(tb):
                    n, _ = _hits(tb, P, [], pad=0.0)
                    if n:
                        issues.append(f"{tag}: text '{t.get_text()}' lies on {n} data points")
        for axis, nm in [(ax.xaxis, 'x'), (ax.yaxis, 'y')]:
            tl = [t for t in _drawn_ticklabels(axis) if t.get_visible() and t.get_text().strip()]
            rot = [t for t in tl if abs(t.get_rotation() % 180) > 1]
            if rot:
                c = np.array([[*(lambda b: ((b.x0 + b.x1) / 2, (b.y0 + b.y1) / 2))(t.get_window_extent(rend))] for t in rot])
                h = rot[0].get_fontsize() * fig.dpi / 72
                ang = np.deg2rad(rot[0].get_rotation())
                if len(c) > 1:
                    gap = np.min(np.abs(np.diff(c[:, 0 if nm == 'x' else 1]))) * abs(np.sin(ang) if nm == 'x' else np.cos(ang))
                    if gap < h:
                        issues.append(f'{tag}: rotated {nm} tick labels collide (spacing {gap:.1f} px < text height {h:.1f} px)')
                grp = f'{k}:{nm}rot'
                for t in rot:
                    items.append((f"{tag} {nm}-tick '{t.get_text()}'", t.get_window_extent(rend), grp))
                tl = [t for t in tl if t not in rot]
            for t in tl:
                items.append((f"{tag} {nm}-tick '{t.get_text()}'", t.get_window_extent(rend), f'{k}:{nm}tick{id(t)}'))
            if axis.label.get_visible() and axis.label.get_text().strip():
                items.append((f'{tag} {nm}-label', axis.label.get_window_extent(rend), f'{k}:{nm}label'))
        for tt in (ax.title, ax._left_title, ax._right_title):
            if tt.get_visible() and tt.get_text().strip():
                items.append((f'{tag} title', tt.get_window_extent(rend), f'{k}:title{id(tt)}'))
    for t in fig.texts:
        if t.get_visible() and t.get_text().strip():
            items.append((f"figure text '{t.get_text()}'", t.get_window_extent(rend), f'fig:{id(t)}'))
    for lg in fig.legends:
        items.append(('figure legend', lg.get_window_extent(rend), f'fig:{id(lg)}'))
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            (na, ba, ga), (nb_, bb, gb) = items[i], items[j]
            if ga == gb:
                continue
            ix = min(ba.x1, bb.x1) - max(ba.x0, bb.x0); iy = min(ba.y1, bb.y1) - max(ba.y0, bb.y0)
            if ix > 0.5 and iy > 0.5:          # more than half a pixel of real overlap
                issues.append(f'{na} overlaps {nb_}')
    return issues


def scalebar(ax, length_data: float, label: str, loc=(0.06, 0.08), lw: float = 2.5, color='k'):
    """Scale bar for a micrograph or a real-space map (e.g. scalebar(ax, 1.0, '1 um'))."""
    x0, y0 = loc
    t = ax.transAxes
    ax.plot([x0, x0 + length_data], [y0, y0], transform=t, color=color, lw=lw, solid_capstyle='butt')
    ax.text(x0 + length_data / 2, y0 + 0.03, label, transform=t, ha='center', va='bottom',
            fontsize=plt.rcParams['font.size'] - 1, color=color)
    return ax


def grey(hex_color: str) -> float:
    """Relative luminance (ITU-R BT.709) of a hex colour, 0 = black, 1 = white."""
    h = hex_color.lstrip('#')
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def greyscale_min_gap(n: int) -> float:
    """Smallest luminance difference between the n colours of palette(n) (MESD v4: palette(n), not COLORS[:n]).
    Distinct line styles and markers carry the information as well, so this only has to stay visible."""
    vals = sorted(grey(c) for c in palette(n))
    return min(b - a for a, b in zip(vals, vals[1:])) if n > 1 else 1.0


def save_fig(fig, name: str, outdir: str | None = None, dpi: int = DPI_RASTER, close: bool = True) -> dict:
    """Write <name>.png at 600 dpi and <name>.pdf (vector) and report the real pixel size."""
    if outdir is None:                                   # MESD v4: the engine always passes outdir
        base = os.environ.get('THESIS_BASE', '/content/drive/MyDrive/thesis_v1')
        outdir = f'{base}/figures'
    os.makedirs(outdir, exist_ok=True)
    png, pdf = f'{outdir}/{name}.png', f'{outdir}/{name}.pdf'
    issues = audit_overlaps(fig)                         # MESD v6: overlap audit before writing
    fig.savefig(png, dpi=dpi)
    fig.savefig(pdf)
    w_in, h_in = fig.get_size_inches()
    try:                                                 # MESD v6: the REAL size of the written PNG
        from PIL import Image                            # (savefig bbox='tight' trims the canvas)
        with Image.open(png) as im:
            px = list(im.size)
    except Exception:
        px = [int(round(float(w_in) * dpi)), int(round(float(h_in) * dpi))]
    info = dict(name=name, png=png, pdf=pdf, dpi=int(dpi), width_cm=round(px[0] / dpi * 2.54, 2),
                height_cm=round(px[1] / dpi * 2.54, 2), canvas_cm=[round(float(w_in) / CM, 2), round(float(h_in) / CM, 2)],
                px=px, font=font_in_use(), overlaps=issues)
    if close:
        plt.close(fig)
    return info


def selftest(outdir: str | None = None) -> dict:
    """Render a demo figure with every rule applied and report what a checker would measure."""
    import numpy as np
    st = apply_style()
    fig, axes = fig_double(0.42, 1, 2)
    x = np.linspace(0, 6, 60)
    for i, k in enumerate([1, 2, 3, 4]):
        axes[0].plot(x, np.sin(k * x / 2) / k, label=f'series {i + 1}', markevery=8, **series(i))
    axes[0].set_xlabel('input (arb. units)'); axes[0].set_ylabel('response (arb. units)')
    axes[0].legend(ncol=2); panel(axes[0], 'a')
    axes[1].imshow(np.add.outer(np.linspace(0, 1, 40), np.linspace(0, 1, 40)), cmap='Greys',
                   extent=(0, 4, 0, 4), origin='lower')
    axes[1].set_xlabel('x (um)'); axes[1].set_ylabel('y (um)')
    scalebar(axes[1], 0.25, '1 um'); panel(axes[1], 'b', color='k')
    info = save_fig(fig, 'fig_style_selftest', outdir)
    info.update(base_pt=float(st['base_pt']), grey_gap=round(float(greyscale_min_gap(4)), 3),
                width_ok=bool(abs(info['width_cm'] - 15.0) < 0.6), dpi_ok=bool(info['dpi'] == DPI_RASTER),
                serif_ok=bool(any(s.lower() in info['font'].lower() for s in
                              ['times', 'nimbus', 'liberation', 'tinos', 'stix', 'freeserif'])))
    return info


apply_style()
