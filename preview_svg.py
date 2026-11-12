#!/usr/bin/env python3
"""
Rasterise the subset of SVG that svg_figures.py emits, for visual checking.

There is no SVG renderer available here (no cairosvg, no rsvg, no browser), so
this walks the generated file and replays its primitives onto raster.Canvas.
It is a proofing tool, not a converter: text uses the 5x7 bitmap font and is
therefore rendered wider than the Times metrics the SVG declares. Overlap
checks stay conservative, which is what matters when proofing a layout.

Output is a PNG preview only. The deliverable for the paper is the SVG.
"""
from __future__ import annotations

import os
import math
import re
import sys
import xml.etree.ElementTree as ET

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import raster  # noqa: E402

SVG = "http://www.w3.org/2000/svg"
K = 3                      # preview pixels per SVG user unit
NAMED = {"#000000": (0, 0, 0), "#666666": (0x66, 0x66, 0x66),
         "#D9D9D9": (0xD9, 0xD9, 0xD9), "#999999": (0x99, 0x99, 0x99),
         "#D55E00": (0xD5, 0x5E, 0x00), "#0072B2": (0x00, 0x72, 0xB2),
         "#008A3E": (0x00, 0x8A, 0x3E), "#7B4EA8": (0x7B, 0x4E, 0xA8),
         "#555555": (0x55, 0x55, 0x55), "#FFFFFF": (255, 255, 255)}


def colour(v: str | None):
    if v is None or v in ("none",):
        return None
    if v.startswith("url("):
        return (0xC8, 0xC8, 0xC8)      # censored hatch, approximated flat
    return NAMED.get(v, (0, 0, 0))


def main() -> int:
    src, dst = sys.argv[1], sys.argv[2]
    tree = ET.parse(src)
    root = tree.getroot()
    vb = [float(v) for v in root.get("viewBox").split()]
    W, H = int(vb[2] * K), int(vb[3] * K)
    c = raster.Canvas(W, H)

    for el in root.iter():
        tag = el.tag.split("}")[-1]
        if tag == "rect":
            fill = colour(el.get("fill"))
            if fill is None:
                continue
            x = float(el.get("x", 0)) * K
            y = float(el.get("y", 0)) * K
            w = float(el.get("width", 0)) * K
            h = float(el.get("height", 0)) * K
            if w >= 1 and h >= 1:
                c.rect(int(round(x)), int(round(y)), int(round(w)),
                       int(round(h)), fill)
        elif tag == "line":
            col = colour(el.get("stroke")) or (0, 0, 0)
            x1, y1 = float(el.get("x1")) * K, float(el.get("y1")) * K
            x2, y2 = float(el.get("x2")) * K, float(el.get("y2")) * K
            th = max(1, int(round(float(el.get("stroke-width", 1)) * K)))
            if el.get("stroke-dasharray"):
                step, on = 7 * K, 4 * K
                n = int(abs(x2 - x1))
                for t in range(0, n, step):
                    c.hline(int(x1 + t), int(y1), min(on, n - t), col)
            elif abs(x2 - x1) < 1:
                c.vline(int(x1), int(y1), int(abs(y2 - y1)), col, thick=th)
            else:
                c.hline(int(x1), int(y1), int(abs(x2 - x1)), col, thick=th)
        elif tag == "text":
            txt = (el.text or "").strip()
            if not txt:
                continue
            size = float(el.get("font-size", 12))
            scale = max(1, int(round(size * K / 7)))
            w = c.text_width(txt, scale)
            anchor = el.get("text-anchor", "start")
            x = float(el.get("x")) * K
            y = float(el.get("y")) * K
            col = colour(el.get("fill")) or (0, 0, 0)
            tr = el.get("transform") or ""
            if "rotate(-90" in tr:
                # vertical axis label: draw bottom-up along the y axis
                m = re.search(r"rotate\(-90 ([\d.]+) ([\d.]+)\)", tr)
                cx, cy = float(m.group(1)) * K, float(m.group(2)) * K
                step = 7 * scale
                for i, ch in enumerate(txt):
                    if ch == " ":
                        continue
                    px = int(cx - (i + 1) * step)
                    py = int(cy - 3 * scale)
                    col_i = raster.FONT.get(ch)
                    if col_i is None:
                        continue
                    for gx in range(len(col_i)):
                        bits = col_i[gx]
                        for gy in range(7):
                            if bits & (1 << gy):
                                c.set_px(px + gx * scale, py + gy * scale, col)
                continue
            if tr.startswith("rotate(-45"):
                m = re.search(r"rotate\(-45 ([\d.]+) ([\d.]+)\)", tr)
                ox, oy = float(m.group(1)) * K, float(m.group(2)) * K
                px0, py0 = float(el.get("x")) * K, float(el.get("y")) * K
                adv = 6 * scale
                # anchor=end puts the glyph run to the LEFT of the anchor
                anch = el.get("text-anchor", "start")
                run0 = -w if anch == "end" else 0.0
                for i, ch in enumerate(txt):
                    col_i = raster.FONT.get(ch)
                    if col_i is None:
                        continue
                    for gx in range(len(col_i)):
                        bits = col_i[gx]
                        for gy in range(7):
                            if not bits & (1 << gy):
                                continue
                            ux = (px0 - ox) + run0 + i * adv + gx * scale
                            uy = (py0 - oy) + gy * scale
                            ca = math.cos(math.radians(-45))
                            sa = math.sin(math.radians(-45))
                            fx = int(round(ox + ux * ca - uy * sa))
                            fy = int(round(oy + ux * sa + uy * ca))
                            c.set_px(fx, fy, col)
                continue
            if anchor == "middle":
                x -= w / 2
            elif anchor == "end":
                x -= w
            top = int(y - 6 * scale)
            c.text(int(x), top, txt, col, scale=scale)

    c.save_png(dst)
    print(f"{os.path.basename(src)} -> {dst}  ({W}x{H})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())