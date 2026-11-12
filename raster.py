"""
Minimal dependency-free raster/PNG toolkit.

The execution environment has no imaging library available (no Pillow, no
matplotlib, no ImageMagick), so figures for the paper are rendered here from
first principles: an RGB canvas, rectangle/line primitives, and a 5x7 bitmap
font, serialised as a PNG via zlib.

Deliberately small: it supports only what the paper's figures need
(grouped bar charts with a log or linear value axis).
"""
from __future__ import annotations

import struct
import zlib

# --------------------------------------------------------------------------
# 5x7 bitmap font. Each glyph is 5 columns; bit 0 of a column is the top row.
# --------------------------------------------------------------------------
FONT: dict[str, tuple[int, int, int, int, int]] = {
    " ": (0x00, 0x00, 0x00, 0x00, 0x00), "!": (0x00, 0x00, 0x5F, 0x00, 0x00),
    '"': (0x00, 0x07, 0x00, 0x07, 0x00), "#": (0x14, 0x7F, 0x14, 0x7F, 0x14),
    "$": (0x24, 0x2A, 0x7F, 0x2A, 0x12), "%": (0x23, 0x13, 0x08, 0x64, 0x62),
    "&": (0x36, 0x49, 0x55, 0x22, 0x50), "'": (0x00, 0x05, 0x03, 0x00, 0x00),
    "(": (0x00, 0x1C, 0x22, 0x41, 0x00), ")": (0x00, 0x41, 0x22, 0x1C, 0x00),
    "*": (0x14, 0x08, 0x3E, 0x08, 0x14), "+": (0x08, 0x08, 0x3E, 0x08, 0x08),
    ",": (0x00, 0x50, 0x30, 0x00, 0x00), "-": (0x08, 0x08, 0x08, 0x08, 0x08),
    ".": (0x00, 0x60, 0x60, 0x00, 0x00), "/": (0x20, 0x10, 0x08, 0x04, 0x02),
    "0": (0x3E, 0x51, 0x49, 0x45, 0x3E), "1": (0x00, 0x42, 0x7F, 0x40, 0x00),
    "2": (0x42, 0x61, 0x51, 0x49, 0x46), "3": (0x21, 0x41, 0x45, 0x4B, 0x31),
    "4": (0x18, 0x14, 0x12, 0x7F, 0x10), "5": (0x27, 0x45, 0x45, 0x45, 0x39),
    "6": (0x3C, 0x4A, 0x49, 0x49, 0x30), "7": (0x01, 0x71, 0x09, 0x05, 0x03),
    "8": (0x36, 0x49, 0x49, 0x49, 0x36), "9": (0x06, 0x49, 0x49, 0x29, 0x1E),
    ":": (0x00, 0x36, 0x36, 0x00, 0x00), ";": (0x00, 0x56, 0x36, 0x00, 0x00),
    "<": (0x08, 0x14, 0x22, 0x41, 0x00), "=": (0x14, 0x14, 0x14, 0x14, 0x14),
    ">": (0x00, 0x41, 0x22, 0x14, 0x08), "?": (0x02, 0x01, 0x51, 0x09, 0x06),
    "@": (0x32, 0x49, 0x79, 0x41, 0x3E), "A": (0x7E, 0x11, 0x11, 0x11, 0x7E),
    "B": (0x7F, 0x49, 0x49, 0x49, 0x36), "C": (0x3E, 0x41, 0x41, 0x41, 0x22),
    "D": (0x7F, 0x41, 0x41, 0x22, 0x1C), "E": (0x7F, 0x49, 0x49, 0x49, 0x41),
    "F": (0x7F, 0x09, 0x09, 0x01, 0x01), "G": (0x3E, 0x41, 0x41, 0x51, 0x32),
    "H": (0x7F, 0x08, 0x08, 0x08, 0x7F), "I": (0x00, 0x41, 0x7F, 0x41, 0x00),
    "J": (0x20, 0x40, 0x41, 0x3F, 0x01), "K": (0x7F, 0x08, 0x14, 0x22, 0x41),
    "L": (0x7F, 0x40, 0x40, 0x40, 0x40), "M": (0x7F, 0x02, 0x04, 0x02, 0x7F),
    "N": (0x7F, 0x04, 0x08, 0x10, 0x7F), "O": (0x3E, 0x41, 0x41, 0x41, 0x3E),
    "P": (0x7F, 0x09, 0x09, 0x09, 0x06), "Q": (0x3E, 0x41, 0x51, 0x21, 0x5E),
    "R": (0x7F, 0x09, 0x19, 0x29, 0x46), "S": (0x46, 0x49, 0x49, 0x49, 0x31),
    "T": (0x01, 0x01, 0x7F, 0x01, 0x01), "U": (0x3F, 0x40, 0x40, 0x40, 0x3F),
    "V": (0x1F, 0x20, 0x40, 0x20, 0x1F), "W": (0x7F, 0x20, 0x18, 0x20, 0x7F),
    "X": (0x63, 0x14, 0x08, 0x14, 0x63), "Y": (0x03, 0x04, 0x78, 0x04, 0x03),
    "Z": (0x61, 0x51, 0x49, 0x45, 0x43), "[": (0x00, 0x00, 0x7F, 0x41, 0x41),
    "\\": (0x02, 0x04, 0x08, 0x10, 0x20), "]": (0x41, 0x41, 0x7F, 0x00, 0x00),
    "^": (0x04, 0x02, 0x01, 0x02, 0x04), "_": (0x40, 0x40, 0x40, 0x40, 0x40),
    "`": (0x00, 0x01, 0x02, 0x04, 0x00), "a": (0x20, 0x54, 0x54, 0x54, 0x78),
    "b": (0x7F, 0x48, 0x44, 0x44, 0x38), "c": (0x38, 0x44, 0x44, 0x44, 0x20),
    "d": (0x38, 0x44, 0x44, 0x48, 0x7F), "e": (0x38, 0x54, 0x54, 0x54, 0x18),
    "f": (0x08, 0x7E, 0x09, 0x01, 0x02), "g": (0x08, 0x14, 0x54, 0x54, 0x3C),
    "h": (0x7F, 0x08, 0x04, 0x04, 0x78), "i": (0x00, 0x44, 0x7D, 0x40, 0x00),
    "j": (0x20, 0x40, 0x44, 0x3D, 0x00), "k": (0x00, 0x7F, 0x10, 0x28, 0x44),
    "l": (0x00, 0x41, 0x7F, 0x40, 0x00), "m": (0x7C, 0x04, 0x78, 0x04, 0x78),
    "n": (0x7C, 0x08, 0x04, 0x04, 0x78), "o": (0x38, 0x44, 0x44, 0x44, 0x38),
    "p": (0x7C, 0x14, 0x14, 0x14, 0x08), "q": (0x08, 0x14, 0x14, 0x18, 0x7C),
    "r": (0x7C, 0x08, 0x04, 0x04, 0x08), "s": (0x48, 0x54, 0x54, 0x54, 0x20),
    "t": (0x04, 0x3F, 0x44, 0x40, 0x20), "u": (0x3C, 0x40, 0x40, 0x20, 0x7C),
    "v": (0x1C, 0x20, 0x40, 0x20, 0x1C), "w": (0x3C, 0x40, 0x30, 0x40, 0x3C),
    "x": (0x44, 0x28, 0x10, 0x28, 0x44), "y": (0x0C, 0x50, 0x50, 0x50, 0x3C),
    "z": (0x44, 0x64, 0x54, 0x4C, 0x44), "{": (0x00, 0x08, 0x36, 0x41, 0x00),
    "|": (0x00, 0x00, 0x7F, 0x00, 0x00), "}": (0x00, 0x41, 0x36, 0x08, 0x00),
    "~": (0x08, 0x08, 0x2A, 0x1C, 0x08),
}

GLYPH_W, GLYPH_H = 5, 7


class Canvas:
    """RGB raster with the handful of primitives the figures need."""

    def __init__(self, width: int, height: int, bg: tuple[int, int, int] = (255, 255, 255)):
        self.w = width
        self.h = height
        self.px = bytearray(bg * (width * height))

    # -- primitives --------------------------------------------------------
    def set_px(self, x: int, y: int, colour: tuple[int, int, int]) -> None:
        if 0 <= x < self.w and 0 <= y < self.h:
            i = (y * self.w + x) * 3
            self.px[i:i + 3] = bytes(colour)

    def rect(self, x: int, y: int, w: int, h: int, colour: tuple[int, int, int]) -> None:
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(self.w, x + w), min(self.h, y + h)
        if x1 <= x0 or y1 <= y0:
            return
        row = bytes(colour) * (x1 - x0)
        for yy in range(y0, y1):
            i = (yy * self.w + x0) * 3
            self.px[i:i + len(row)] = row

    def hline(self, x: int, y: int, w: int, colour: tuple[int, int, int], thick: int = 1) -> None:
        self.rect(x, y, w, thick, colour)

    def vline(self, x: int, y: int, h: int, colour: tuple[int, int, int], thick: int = 1) -> None:
        self.rect(x, y, thick, h, colour)

    def dashed_hline(self, x: int, y: int, w: int, colour: tuple[int, int, int],
                     dash: int = 6, thick: int = 1) -> None:
        for i in range(0, w, dash * 2):
            self.rect(x + i, y, min(dash, w - i), thick, colour)

    # -- text --------------------------------------------------------------
    @staticmethod
    def text_width(s: str, scale: int = 1, tracking: int = 1) -> int:
        if not s:
            return 0
        return len(s) * (GLYPH_W * scale + tracking) - tracking

    def text(self, x: int, y: int, s: str, colour: tuple[int, int, int] = (0, 0, 0),
             scale: int = 1, tracking: int = 1) -> int:
        """Draw `s` with its top-left at (x, y). Returns the advance width."""
        cx = x
        for ch in s:
            glyph = FONT.get(ch) or FONT.get(ch.upper()) or FONT[" "]
            for col in range(GLYPH_W):
                bits = glyph[col]
                for row in range(GLYPH_H):
                    if bits & (1 << row):
                        self.rect(cx + col * scale, y + row * scale, scale, scale, colour)
            cx += GLYPH_W * scale + tracking
        return cx - x

    def text_centred(self, cx: int, y: int, s: str, colour=(0, 0, 0),
                     scale: int = 1, tracking: int = 1) -> None:
        self.text(cx - self.text_width(s, scale, tracking) // 2, y, s, colour, scale, tracking)

    def text_right(self, rx: int, y: int, s: str, colour=(0, 0, 0),
                   scale: int = 1, tracking: int = 1) -> None:
        self.text(rx - self.text_width(s, scale, tracking), y, s, colour, scale, tracking)

    # -- output ------------------------------------------------------------
    def save_png(self, path: str) -> None:
        raw = bytearray()
        stride = self.w * 3
        for y in range(self.h):
            raw.append(0)  # filter type 0 (None)
            raw += self.px[y * stride:(y + 1) * stride]

        def chunk(tag: bytes, data: bytes) -> bytes:
            return (struct.pack(">I", len(data)) + tag + data
                    + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF))

        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">IIBBBBB", self.w, self.h, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(bytes(raw), 9))
               + chunk(b"IEND", b""))
        with open(path, "wb") as fh:
            fh.write(png)


# --------------------------------------------------------------------------
# Grouped bar chart
# --------------------------------------------------------------------------
# Colour-blind-safe qualitative palette (Okabe-Ito), darkened for print.
PALETTE = [
    (0x00, 0x00, 0x00),   # black
    (0xD5, 0x5E, 0x00),   # vermillion
    (0x00, 0x72, 0xB2),   # blue
    (0x00, 0x8A, 0x3E),   # green
    (0x7B, 0x4E, 0xA8),   # purple
]
GREY = (0x66, 0x66, 0x66)
LGREY = (0xD9, 0xD9, 0xD9)
CENSORED_COLOUR = (0x99, 0x99, 0x99)
BLACK = (0x00, 0x00, 0x00)


def grouped_bar_chart(
    path: str,
    groups: list[str],
    series: list[str],
    values: list[list[float | None]],
    *,
    title: str = "",
    ylabel: str = "",
    xlabel: str = "",
    log_y: bool = True,
    width: int = 2200,
    height: int = 1050,
    value_fmt: str = "{:.0f}",
    value_labels: bool = False,
    y_min: float | None = None,
    censored: list[list[bool]] | None = None,
) -> None:
    """
    Render a grouped bar chart.

    groups  : x-axis category labels; "\\n" starts a new label line
    series  : legend entries (one per bar cluster)
    values  : values[series_index][group_index]; None skips that bar
    censored: parallel mask; a True cell is drawn as a lower bound in grey
    """
    pad_l, pad_r, pad_t, pad_b = 150, 40, 130, 250
    plot_x, plot_y = pad_l, pad_t
    plot_w = width - pad_l - pad_r
    plot_h = height - pad_t - pad_b

    c = Canvas(width, height)
    c.text_centred(width // 2, 34, title, BLACK, scale=3)

    flat = [v for row in values for v in row if v is not None and v > 0]
    censored_vals = set()
    if censored:
        for si, row in enumerate(censored):
            for gi, flag in enumerate(row):
                if flag and values[si][gi]:
                    censored_vals.add((si, gi))
    if log_y:
        lo = y_min if y_min else min(flat) * 0.7
        hi = max(flat) * 1.35
        import math
        lo = 10 ** math.floor(math.log10(lo))
        hi = 10 ** math.ceil(math.log10(hi))
        decades = list(range(int(round(math.log10(lo))), int(round(math.log10(hi))) + 1))
        ticks = [(10 ** d, f"1e{d}" if d != 0 else "1") for d in decades]

        def ypix(v: float) -> float:
            import math
            return plot_y + plot_h * (1 - (math.log10(max(v, lo)) - math.log10(lo))
                                      / (math.log10(hi) - math.log10(lo)))
    else:
        lo, hi = 0.0, max(flat) * 1.15
        ticks = [(t, value_fmt.format(t)) for t in _nice_ticks(0, hi, 6)]

        def ypix(v: float) -> float:
            return plot_y + plot_h * (1 - (v - lo) / (hi - lo))

    # gridlines + y tick labels
    for tv, tl in ticks:
        y = int(round(ypix(tv)))
        if plot_y - 1 <= y <= plot_y + plot_h + 1:
            c.dashed_hline(plot_x, y, plot_w, LGREY, dash=5)
            c.text_right(plot_x - 14, y - 7, tl, BLACK, scale=2)

    # axes
    c.vline(plot_x, plot_y, plot_h + 1, BLACK, thick=3)
    c.hline(plot_x, plot_y + plot_h, plot_w, BLACK, thick=3)

    n_ser = len(series)
    slot = plot_w / len(groups)
    inner = slot * 0.82
    bar_w = inner / n_ser

    for gi, g in enumerate(groups):
        gx = plot_x + slot * gi
        for si in range(n_ser):
            v = values[si][gi]
            if v is None or v <= 0:
                continue
            x = int(gx + (slot - inner) / 2 + si * bar_w)
            y = int(round(ypix(v)))
            top = min(y, plot_y + plot_h)
            colour = CENSORED_COLOUR if (si, gi) in censored_vals \
                else PALETTE[si % len(PALETTE)]
            c.rect(x + 2, top, int(bar_w) - 4, plot_y + plot_h - top, colour)
            if (si, gi) in censored_vals:
                # lower bound only: mark the bar so it is not read as a point value
                c.text_centred(x + int(bar_w) // 2, top - 24, ">= limit",
                               CENSORED_COLOUR, scale=1)
            elif value_labels:
                c.text_centred(x + int(bar_w) // 2, top - 24, value_fmt.format(v),
                               BLACK, scale=1)
        # group label, possibly wrapped over two lines
        for li, line in enumerate(g.split("\n")):
            c.text_centred(int(gx + slot // 2),
                           plot_y + plot_h + 18 + li * 20, line, BLACK, scale=2)

    if ylabel:
        _vertical_label(c, plot_x - 108, plot_y + plot_h // 2, ylabel)
    if xlabel:
        c.text_centred(width // 2, plot_y + plot_h + 62, xlabel, BLACK, scale=2)

    # legend
    lx = plot_x
    ly = height - 46
    for si, name in enumerate(series):
        c.rect(lx, ly, 26, 20, PALETTE[si % len(PALETTE)])
        c.text(lx + 34, ly + 4, name, BLACK, scale=2)
        lx += 34 + Canvas.text_width(name, 2) + 46

    c.save_png(path)


def _nice_ticks(lo: float, hi: float, count: int) -> list[float]:
    import math
    span = hi - lo
    if span <= 0:
        return [lo]
    raw = span / count
    mag = 10 ** math.floor(math.log10(raw))
    for mult in (1, 2, 2.5, 5, 10):
        step = mult * mag
        if span / step <= count:
            break
    start = math.ceil(lo / step) * step
    out, v = [], start
    while v <= hi + 1e-9:
        out.append(round(v, 10))
        v += step
    return out


def _vertical_label(c: Canvas, cx: int, cy: int, s: str) -> None:
    """Draw a rotated (bottom-to-top) axis label by rendering per character."""
    total = len(s) * (GLYPH_H + 1) - 1
    y = cy + total // 2
    for ch in s:
        glyph = FONT.get(ch) or FONT.get(ch.upper()) or FONT[" "]
        # render the glyph rotated: rows become columns
        for col in range(GLYPH_W):
            for row in range(GLYPH_H):
                if glyph[col] & (1 << row):
                    c.rect(cx + row * 2, y + col * 2, 2, 2, BLACK)
        y += GLYPH_H + 1