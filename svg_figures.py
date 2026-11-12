#!/usr/bin/env python3
"""
Render the paper's four figures as true vector SVG from results.json.

raster.py draws text with a 5x7 bitmap font, so the PNG figures stay chunky at
any size and Word's "compress pictures" ruins them further. SVG keeps text as
text and shapes as paths, so the figure stays sharp when zoomed, printed, or
resized to the column width.

Labels, titles and axis wording are taken verbatim from make_figures.py, so
these are the original English figures, only re-rendered as vectors. Data,
ordering, log axes and the censored-cell convention are identical too: this is
a format change, not a different experiment.

Figure 2 is written in two conventions because the manuscript uses both:
  fig2_speedup_ratio.svg         cur/base  -- matches make_figures.py
  fig2_speedup_faster_is_1.svg   base/cur  -- matches Tables 5 and 6
"""
from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

RESULTS = os.path.join(HERE, "results", "results.json")
OUTDIR = os.path.join(HERE, "figures_svg")

CENSOR_LIMIT_MS = 45_000.0

# Okabe-Ito, darkened for print -- identical to raster.PALETTE so the SVG and
# the legacy PNG read as the same figure.
PALETTE = ["#000000", "#D55E00", "#0072B2", "#008A3E", "#7B4EA8"]
LGREY = "#D9D9D9"
CENSORED = "#999999"
BLACK = "#000000"

FONT = "Times New Roman, Liberation Serif, Nimbus Roman, serif"

# --- verbatim from make_figures.py ----------------------------------------
SHORT: dict[str, str] = {
    "W1.1": "W1.1",
    "W1.2": "W1.2",
    "W1.3": "W1.3",
    "W2.1 non-SARG month": "W2.1\nnon-SARG\nmonth",
    "W2.2 SARG month": "W2.2\nSARG\nmonth",
    "W2.3 non-SARG year": "W2.3\nnon-SARG\nyear",
    "W2.4 SARG year": "W2.4\nSARG\nyear",
    "W3.1": "W3.1",
    "W4.1 JOIN": "W4.1\nJOIN",
    "W4.2 IN": "W4.2\nIN",
    "W4.3 EXISTS": "W4.3\nEXISTS",
    "W5.1 LEFT JOIN": "W5.1\nLEFT JOIN",
    "W5.2 NOT IN": "W5.2\nNOT IN",
    "W5.3 NOT EXISTS": "W5.3\nNOT EX",
    "W6.1 flat JOIN": "W6.1\nflat JOIN",
    "W6.2 derived table": "W6.2\nderived",
    "W7.1": "W7.1",
    "W8.1": "W8.1",
}
QUERY_ORDER = list(SHORT)
CONFIG_ORDER = ["C0_zero", "C1_fk", "C2_single", "C3_composite", "C4_covering"]
CONFIG_LEGEND = ["C0 no index", "C1 FK only", "C2 single-col",
                 "C3 composite", "C4 covering"]


# --------------------------------------------------------------------------
# Times New Roman advance widths per 1000 units/em (standard AFM metrics).
# The SVG uses real proportional text, so legend and label layout have to be
# computed from real string widths rather than a character count.
# --------------------------------------------------------------------------
_ADV: dict[str, int] = {
    " ": 250, "!": 333, '"': 408, "#": 500, "$": 500, "%": 833, "&": 778,
    "'": 333, "(": 333, ")": 333, "*": 500, "+": 564, ",": 250, "-": 333,
    ".": 250, "/": 278, "0": 500, "1": 500, "2": 500, "3": 500, "4": 500,
    "5": 500, "6": 500, "7": 500, "8": 500, "9": 500, ":": 278, ";": 278,
    "<": 564, "=": 564, ">": 564, "?": 444, "@": 921, "[": 333, "\\": 278,
    "]": 333, "^": 469, "_": 500, "`": 333, "a": 444, "b": 500, "c": 444,
    "d": 500, "e": 444, "f": 333, "g": 500, "h": 500, "i": 278, "j": 278,
    "k": 500, "l": 278, "m": 778, "n": 500, "o": 500, "p": 500, "q": 500,
    "r": 333, "s": 389, "t": 278, "u": 500, "v": 500, "w": 722, "x": 500,
    "y": 500, "z": 444, "{": 480, "|": 200, "}": 480, "~": 541,
    "A": 722, "B": 667, "C": 667, "D": 722, "E": 611, "F": 556, "G": 722,
    "H": 722, "I": 333, "J": 389, "K": 722, "L": 611, "M": 889, "N": 722,
    "O": 722, "P": 556, "Q": 722, "R": 667, "S": 556, "T": 611, "U": 722,
    "V": 722, "W": 944, "X": 722, "Y": 722, "Z": 611,
}


def text_w(s: str, size: float) -> float:
    """Rendered width of s at font-size `size`, in user units."""
    return sum(_ADV.get(ch, 500) for ch in s) / 1000.0 * size


def esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def n_dec(v: float, dp: int = 2) -> str:
    """Thousands separator and decimal mark follow the English paper."""
    return f"{v:,.{dp}f}"


def axis_fmt(v: float) -> str:
    if v >= 1000:
        return n_dec(v, 0)
    if v >= 1:
        return n_dec(v, 0) if abs(v - round(v)) < 1e-9 else n_dec(v, 1)
    return n_dec(v, 3).rstrip("0")


def value_label(v: float) -> str:
    return n_dec(v, 0) if v >= 10_000 else n_dec(v, 2)


# --------------------------------------------------------------------------
# data
# --------------------------------------------------------------------------
def load() -> tuple[dict[tuple[str, str], float], set[tuple[str, str]]]:
    with open(RESULTS) as fh:
        blob = json.load(fh)
    med: dict[tuple[str, str], float] = {}
    cens: set[tuple[str, str]] = set()
    for rec in blob["results"]:
        key = (rec["phase"], rec["label"])
        err = str(rec.get("error") or "")
        if (rec.get("censored") or rec.get("error") == "timeout"
                or "max_statement_time" in err):
            cens.add(key)
            continue
        if rec.get("median_ms") is None:
            continue
        med[key] = float(rec["median_ms"])
    return med, cens


def cell(med, cens, cfg, q) -> float | None:
    if (cfg, q) in cens:
        return CENSOR_LIMIT_MS
    return med.get((cfg, q))


# --------------------------------------------------------------------------
# SVG helpers
# --------------------------------------------------------------------------
def _text(x, y, s, *, size=13, fill=BLACK, anchor="start", weight="normal",
          transform=None) -> str:
    tr = f' transform="{transform}"' if transform else ""
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{FONT}" '
            f'font-size="{size}" fill="{fill}" text-anchor="{anchor}" '
            f'font-weight="{weight}"{tr}>{esc(s)}</text>')


def _log_ticks(lo: float, hi: float) -> list[float]:
    return [10.0 ** d for d in range(int(math.floor(math.log10(lo))),
                                     int(math.ceil(math.log10(hi))) + 1)]


def grouped_bar_svg(
    path: str,
    groups: list[str],
    series: list[str],
    values: list[list[float | None]],
    *,
    title: str = "",
    ylabel: str = "",
    xlabel: str = "",
    log_y: bool = True,
    width_in: float = 6.5,
    plot_h_in: float = 2.3,
    y_min: float | None = None,
    censored: list[list[bool]] | None = None,
    value_labels: bool = False,
) -> None:
    """
    Write a grouped bar chart as SVG.

    values[series_index][group_index]; None draws no bar. A cell flagged in
    `censored` is hatched and annotated, because its value is a lower bound
    rather than a measurement.

    X labels are rotated when the slot is narrower than the widest label. The
    rotation uses text-anchor="end": after rotate(-45) the glyph run would
    otherwise travel up-and-right from the anchor and cut into the bars.
    """
    scale = 100.0                       # user units per inch inside the viewBox
    W = width_in * scale
    pad_l, pad_r, pad_t = 62, 18, 78

    lines_of = [g.split("\n") for g in groups]
    n_lines = max(len(v) for v in lines_of)
    label_size = 10.5 if len(groups) <= 8 else 9.5
    step = label_size + 1.6
    plot_w = W - pad_l - pad_r
    slot0 = plot_w / len(groups)
    widest = max(text_w(l, label_size)
                 for v in lines_of for l in v)

    COS = SIN = math.cos(math.radians(45))
    rotate = widest > slot0 - 1.5

    if rotate:
        # anchor at the tick, block hanging down-left; vertical reach is the
        # per-line stacking plus the longest line's own diagonal drop
        label_h = ((n_lines - 1) * step + widest) * SIN + label_size * COS
    else:
        label_h = (n_lines - 1) * step + label_size

    # Bottom stack: gap, label block, axis title, legend row. The plot keeps a
    # fixed height and the canvas grows, so dense labels never squeeze the bars.
    tail = 8 + label_h + 12 + 11 + 20
    plot_h = plot_h_in * scale
    out_h = pad_t + plot_h + tail

    plot_x, plot_y = pad_l, pad_t
    flat = [v for row in values for v in row if v is not None and v > 0]

    if log_y:
        lo = y_min if y_min else min(flat) * 0.7
        hi = max(flat) * 1.35
        lo = 10 ** math.floor(math.log10(lo))
        hi = 10 ** math.ceil(math.log10(hi))
        llo, hhi = math.log10(lo), math.log10(hi)
        ticks = _log_ticks(lo, hi)

        def ypix(v: float) -> float:
            return plot_y + plot_h * (1 - (math.log10(max(v, lo)) - llo)
                                      / (hhi - llo))
    else:
        lo, hi = 0.0, max(flat) * 1.15
        ticks = [lo + (hi - lo) * i / 5 for i in range(6)]

        def ypix(v: float) -> float:
            return plot_y + plot_h * (1 - (v - lo) / (hi - lo))

    o: list[str] = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" version="1.1" '
        f'width="{width_in}in" height="{out_h / scale:.2f}in" '
        f'viewBox="0 0 {W:.0f} {out_h:.0f}">',
        '<defs>',
        '<pattern id="censored" width="6" height="6" '
        'patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        f'<rect width="6" height="6" fill="{CENSORED}"/>'
        '<line x1="0" y1="0" x2="0" y2="6" stroke="#FFFFFF" '
        'stroke-width="2.4"/></pattern>',
        '</defs>',
        f'<rect width="{W:.0f}" height="{out_h:.0f}" fill="#FFFFFF"/>',
    ]

    if title:
        t_size = 15.0
        while t_size > 10.5 and text_w(title, t_size) > W - 24:
            t_size -= 0.5
        o.append(_text(W / 2, 30, title, size=t_size, anchor="middle",
                       weight="bold"))

    for tv in ticks:
        y = round(ypix(tv), 1)
        if plot_y - 1 <= y <= plot_y + plot_h + 1:
            o.append(f'<line x1="{plot_x}" y1="{y}" x2="{plot_x + plot_w}" '
                     f'y2="{y}" stroke="{LGREY}" stroke-width="1" '
                     f'stroke-dasharray="4 3"/>')
            o.append(_text(plot_x - 7, y + 3.6, axis_fmt(tv), size=11,
                           anchor="end"))

    o.append(f'<line x1="{plot_x}" y1="{plot_y}" x2="{plot_x}" '
             f'y2="{plot_y + plot_h}" stroke="{BLACK}" stroke-width="1.4"/>')
    o.append(f'<line x1="{plot_x}" y1="{plot_y + plot_h}" '
             f'x2="{plot_x + plot_w}" y2="{plot_y + plot_h}" '
             f'stroke="{BLACK}" stroke-width="1.4"/>')

    n_ser = len(series)
    slot = plot_w / len(groups)
    inner = slot * 0.80
    bar_w = inner / n_ser
    cens_cells: set[tuple[int, int]] = set()
    if censored:
        for si, row in enumerate(censored):
            for gi, flag in enumerate(row):
                if flag:
                    cens_cells.add((si, gi))

    axis_y = plot_y + plot_h
    for gi, g in enumerate(groups):
        gx = plot_x + slot * gi
        for si in range(n_ser):
            v = values[si][gi]
            if v is None or v <= 0:
                continue
            x = gx + (slot - inner) / 2 + si * bar_w
            top = min(ypix(v), axis_y)
            fill = "url(#censored)" if (si, gi) in cens_cells \
                else PALETTE[si % len(PALETTE)]
            o.append(f'<rect x="{x + 0.8:.1f}" y="{top:.1f}" '
                     f'width="{max(bar_w - 1.6, 0.6):.1f}" '
                     f'height="{max(axis_y - top, 0.6):.1f}" fill="{fill}"/>')
            if (si, gi) in cens_cells:
                o.append(_text(x + bar_w / 2, top - 4, ">= limit", size=8,
                               fill="#555555", anchor="middle"))
            elif value_labels and text_w(value_label(v), 8) <= bar_w:
                # annotate only where the number fits over its own bar
                o.append(_text(x + bar_w / 2, top - 3.5, value_label(v),
                               size=8, anchor="middle"))

        # x label: anchor at the tick, block extending away from the plot
        lines = lines_of[gi]
        if rotate:
            ax = gx + slot / 2 + label_size * 0.55
            ay = axis_y + label_size * 0.95
            for li, line in enumerate(lines):
                lx = ax + li * step * COS
                ly = ay + li * step * SIN
                o.append(_text(lx, ly, line, size=label_size, anchor="end",
                               transform=f"rotate(-45 {lx:.1f} {ly:.1f})"))
        else:
            base = axis_y + label_size + 3
            for li, line in enumerate(lines):
                o.append(_text(gx + slot / 2, base + li * step, line,
                               size=label_size, anchor="middle"))

    if ylabel:
        cx, cy = plot_x - 40, plot_y + plot_h / 2
        o.append(_text(cx, cy, ylabel, size=11, anchor="middle",
                       transform=f"rotate(-90 {cx:.1f} {cy:.1f})"))
    if xlabel:
        o.append(_text(plot_x + plot_w / 2, axis_y + label_h + 22, xlabel,
                       size=11, anchor="middle"))

    legend_size = 11
    widths = [16 + text_w(n, legend_size) + 18 for n in series]
    lx = plot_x + (plot_w - sum(widths)) / 2
    ly = out_h - 11
    for si, name in enumerate(series):
        o.append(f'<rect x="{lx:.1f}" y="{ly - 9:.1f}" width="11" height="11" '
                 f'fill="{PALETTE[si % len(PALETTE)]}"/>')
        o.append(_text(lx + 15, ly, name, size=legend_size))
        lx += widths[si]

    o.append('</svg>')
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(o) + "\n")


def series_for(med, cens, queries, configs) -> tuple[list, list]:
    vals, mask = [], []
    for cfg in configs:
        vals.append([cell(med, cens, cfg, q) for q in queries])
        mask.append([(cfg, q) in cens for q in queries])
    return vals, mask


def main() -> int:
    os.makedirs(OUTDIR, exist_ok=True)
    med, cens = load()
    groups = [SHORT[q] for q in QUERY_ORDER]

    # ---- Figure 1 --------------------------------------------------------
    v1, m1 = series_for(med, cens, QUERY_ORDER, CONFIG_ORDER)
    grouped_bar_svg(
        os.path.join(OUTDIR, "fig1_execution_time.svg"),
        groups, CONFIG_LEGEND, v1,
        title="Median server-side execution time by workload and index configuration",
        ylabel="Execution time (ms, log scale)", xlabel="Query workload",
        log_y=True, width_in=6.5, plot_h_in=2.3, censored=m1)

    # ---- Figure 2, both conventions --------------------------------------
    ratio = []
    for cfg in CONFIG_ORDER[1:]:
        row = []
        for q in QUERY_ORDER:
            base, cur = cell(med, cens, "C0_zero", q), cell(med, cens, cfg, q)
            row.append(round(cur / base, 3) if base and cur else None)
        ratio.append(row)
    m2 = [[(cfg, q) in cens for q in QUERY_ORDER] for cfg in CONFIG_ORDER[1:]]

    grouped_bar_svg(
        os.path.join(OUTDIR, "fig2_speedup_ratio.svg"),
        groups, CONFIG_LEGEND[1:], ratio,
        title="Execution-time speedup relative to the unindexed baseline (C0)",
        ylabel="Ratio to C0 (x, log scale)", xlabel="Query workload",
        log_y=True, width_in=6.5, plot_h_in=2.3, censored=m2)

    inv = [[(1 / v if v else None) for v in row] for row in ratio]
    grouped_bar_svg(
        os.path.join(OUTDIR, "fig2_speedup_faster_is_1.svg"),
        groups, CONFIG_LEGEND[1:], inv,
        title="Execution-time speedup relative to the unindexed baseline (C0)",
        ylabel="Speedup (x, log scale; above 1 is faster)",
        xlabel="Query workload",
        log_y=True, width_in=6.5, plot_h_in=2.3, censored=m2)

    # ---- Figure 3 --------------------------------------------------------
    fam3 = ["W4.1 JOIN", "W4.2 IN", "W4.3 EXISTS",
            "W5.1 LEFT JOIN", "W5.2 NOT IN", "W5.3 NOT EXISTS"]
    v3, m3 = series_for(med, cens, fam3, CONFIG_ORDER)
    grouped_bar_svg(
        os.path.join(OUTDIR, "fig3_join_vs_subquery.svg"),
        [SHORT[k] for k in fam3], CONFIG_LEGEND, v3,
        title="Semi-join and anti-join formulation compared under identical index configurations",
        ylabel="Execution time (ms, log scale)", xlabel="Query formulation",
        log_y=True, width_in=6.5, plot_h_in=2.4, censored=m3)

    # ---- Figure 4 --------------------------------------------------------
    fam4 = ["W2.1 non-SARG month", "W2.2 SARG month",
            "W2.3 non-SARG year", "W2.4 SARG year"]
    v4, m4 = series_for(med, cens, fam4, CONFIG_ORDER)
    grouped_bar_svg(
        os.path.join(OUTDIR, "fig4_sargability.svg"),
        [SHORT[k] for k in fam4], CONFIG_LEGEND, v4,
        title="Predicate form at two levels of selectivity: selective month versus non-selective year",
        ylabel="Execution time (ms, log scale)", xlabel="Query workload",
        log_y=True, width_in=6.5, plot_h_in=2.4, censored=m4, value_labels=True)

    for f in sorted(os.listdir(OUTDIR)):
        p = os.path.join(OUTDIR, f)
        print(f"wrote {p}  ({os.path.getsize(p)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())