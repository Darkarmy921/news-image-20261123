#!/usr/bin/env python3
"""Render one 1024x1024 front page summing up Monday 23 November 2026.

Stdlib only. Text comes from glyph bitmaps baked into fontdata.py, so the
program needs no font files and no network at render time. The PNG is
written by hand with zlib level 9 and filter 0 on every row: same input
bytes, same output bytes, every run.

Usage: MAKEFUN_OUTPUT_DIR=out python3 main.py   (writes out/entry.png)
"""
import base64
import binascii
import hashlib
import os
import struct
import sys
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from fontdata import FONTS  # noqa: E402

W, H = 1024, 1024
PAPER = (247, 243, 234)
INK = (20, 20, 20)
GREY = (138, 131, 120)
RED = (163, 18, 18)
BLUE = (28, 77, 143)
NAVY = (35, 56, 118)
GREEN = (30, 107, 58)
ORANGE = (178, 90, 16)
TEAL = (15, 107, 107)

TITLE = "THE WORLD IN A DAY"
DATELINE = "MONDAY, 23 NOVEMBER 2026 \u2014 44 STORIES FROM 7 REGIONS"
SUBHEAD = "THE WORLD'S NEWS IN ONE IMAGE"

# Stories: (headline, deck). Decks are one verified factual sentence.
# All 44 trace to real reports dated 22-23 Nov 2026; see RESEARCH.md.
LEADS = [
    ("LEAD", "COP31 ends with no deal — a first since 2000",
     "After 44 hours of overtime, the Antalya summit closed with no deal; "
     "Reuters says Saudi officials led the fossil-fuel resistance."),
    ("THE MIDTERMS", "Democrats clinch 258 House seats, most since 1992",
     "Chuck Hubbard beat Rep. Virginia Foxx by 330 votes in North Carolina, "
     "giving Democrats at least 258 seats in the House."),
]

REGIONS = [
    ("NORTH AMERICA", BLUE, [
        ("Trump: Iran strikes could resume after New Year",
         "Trump told Fox he would resume major Iran strikes after the New "
         "Year if talks fail."),
        "Delta outage delays 1,435 flights as Thanksgiving travel begins",
        "Spy chief Clayton to double as acting US cyber director",
        "Bessent warns Fed against overtightening",
        "US probes Nvidia-linked Alice Huang, Singapore firm",
        "Kim Jong Un ghosted Trump, WSJ reports",
    ]),
    ("SOUTH AMERICA", GREEN, [
        ("Brazil's lower house votes on Lula's fiscal bill",
         "The Chamber votes Monday on Lula's fiscal bill, already approved "
         "by the Senate."),
        "Severe storms lash Brazil and Argentina on Monday",
        "Venezuela government-opposition talks due to conclude",
        "Milei's Senate stalls plan to suspend 2027 primaries",
        "MLB chief meets Venezuela's acting president",
        "Peru aftershocks continue after Friday's M6.7 quake",
    ]),
    ("EUROPE", NAVY, [
        ("NATO meets Monday over Russian missiles in Poland",
         "NATO meets in Brussels over Russian missiles that flew into Polish "
         "airspace Friday."),
        "France rejects EU budget plan over farmer incomes",
        "Brussels hit by transport strike and mass protest",
        "Burnham to hail 'landmark' EU deal to MPs",
        "NHS launches world's largest AI breast screening trial",
        "Manchester arena evacuated after tear gas scare",
    ]),
    ("MIDDLE EAST", RED, [
        ("Netanyahu-Eisenkot coalition talks end with no deal",
         "Likud and Yashar met four hours in Herzliya and parted with no "
         "deal on a government."),
        "Houthis claim strikes on Saudi refinery, radar site",
        "Eisenkot calls settler arson 'Jewish terrorism'",
        "Six killed, 33 wounded in Gaza in 24 hours",
        "Senior cops: Israel's police force 'falling apart'",
        "Saudi hand seen behind failed COP31 climate deal",
    ]),
    ("AFRICA", ORANGE, [
        ("Kenya, DR Congo agree to restore full diplomatic ties",
         "Ruto and Tshisekedi agreed at Oyo to restore full diplomatic ties "
         "after three years."),
        "Tinubu gives N250m to Bayelsa boat victims' families",
        "Zimbabwe preacher Uebert Angel arrested over sex claims",
        "WHO chief pleads for peace in Ebola-hit DR Congo",
        "Mashaba set to return as Johannesburg mayor",
        "35 Fulani killed in revenge attacks in Nigeria",
    ]),
    ("ASIA-PACIFIC", TEAL, [
        ("Nepal PM meets Modi in New Delhi on first state visit",
         "Shah meets Modi on energy, trade, railways, hydropower."),
        "China demands US drop telecom curbs on its carriers",
        "South Korea's education minister quits over exam chaos",
        "Australia's jobless rate to top 5%, treasurer warns",
        "Shuri Castle reopens seven years after the 2019 fire",
        "Seoul readies market fund as KOSPI tumbles",
    ]),
]

BAND = [
    "Samsung AI smart glasses launch 10 December",
    "Votee AI and AI Singapore build SEA language models",
    "Anthropic shares slide after record $81.3bn IPO",
    "Liverpool thrash Manchester United 4-0 at Anfield",
    "Pant's 128 powers India to record 720 in Wellington",
    "Verstappen wins chaotic Las Vegas Grand Prix",
]

SOURCES_LINE = (
    "SOURCES: REUTERS \u2022 BBC \u2022 AP \u2022 CNN \u2022 IANS \u2022 YONHAP "
    "\u2022 NIKKEI \u2022 ESPN \u2022 CAPITAL FM \u2022 PUNCH \u2022 AFP "
    "\u2022 THE NEWS"
)
FOOTER_RIGHT = "RENDERED 23 NOV 2026 \u2014 NO NETWORK"


def text_width(font_name, text):
    font = FONTS[font_name]
    total = 0.0
    for ch in text:
        g = font["glyphs"].get(ch)
        if g is None:
            g = font["glyphs"].get("?")
            if g is None:
                continue
        total += g[4]
    return total


class Canvas:
    def __init__(self):
        self.px = bytearray(PAPER * (W * H))

    def _set(self, x, y, color):
        if 0 <= x < W and 0 <= y < H:
            i = (y * W + x) * 3
            self.px[i], self.px[i + 1], self.px[i + 2] = color

    def rect(self, x, y, w, h, color):
        x0, y0 = max(0, x), max(0, y)
        x1, y1 = min(W, x + w), min(H, y + h)
        for yy in range(y0, y1):
            base = (yy * W + x0) * 3
            for xx in range(x0, x1):
                i = base + (xx - x0) * 3
                self.px[i], self.px[i + 1], self.px[i + 2] = color

    def hline(self, x, y, w, color, thick=1):
        self.rect(x, y, w, thick, color)

    def vline(self, x, y, h, color, thick=1):
        self.rect(x, y, thick, h, color)

    def text_width(self, font_name, text):
        return text_width(font_name, text)

    def draw_text(self, font_name, x, y, text, color):
        font = FONTS[font_name]
        ascent = font["ascent"]
        cx = float(x)
        top = y
        for ch in text:
            g = font["glyphs"].get(ch)
            if g is None:
                ch = "?"
                g = font["glyphs"].get(ch)
                if g is None:
                    continue
            gw, gh, dx, dy, adv, bitmap = g
            if bitmap:
                raw = base64.b64decode(bitmap)
                row_bytes = (gw + 7) // 8
                for row in range(gh):
                    bits = raw[row * row_bytes:(row + 1) * row_bytes]
                    for col in range(gw):
                        if bits[col // 8] >> (7 - col % 8) & 1:
                            self._set(int(cx) + dx + col, top + dy + row, color)
            cx += adv
        return cx


def wrap(font_name, text, max_width):
    """Greedy word wrap. Returns lines (list of str), each <= max_width."""
    words = text.split(" ")
    lines, cur = [], ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if text_width(font_name, trial) <= max_width or not cur:
            cur = trial
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def fit_lines(font_name, text, max_width, max_lines):
    """Wrap and truncate with an ellipsis if it cannot fit in max_lines."""
    lines = wrap(font_name, text, max_width)
    if len(lines) <= max_lines:
        return lines
    lines = lines[:max_lines]
    while lines and text_width(font_name, lines[-1] + "\u2026") > max_width:
        lines[-1] = lines[-1][:-1]
    lines[-1] = lines[-1] + "\u2026"
    return lines


def draw_para(cv, font_name, x, y, text, max_width, max_lines, color, leading=None):
    font = FONTS[font_name]
    leading = leading if leading is not None else font["size"] + 3
    lines = fit_lines(font_name, text, max_width, max_lines)
    for i, line in enumerate(lines):
        cv.draw_text(font_name, x, y + i * leading, line, color)
    return y + len(lines) * leading


def png_bytes(cv):
    def chunk(tag, data):
        out = struct.pack(">I", len(data)) + tag + data
        out += struct.pack(">I", binascii.crc32(tag + data) & 0xFFFFFFFF)
        return out

    header = struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0)
    raw = bytearray()
    for y in range(H):
        raw.append(0)
        raw += cv.px[y * W * 3:(y + 1) * W * 3]
    comp = zlib.compress(bytes(raw), 9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", header)
        + chunk(b"IDAT", comp)
        + chunk(b"IEND", b"")
    )


def render():
    cv = Canvas()
    mx = 28  # side margin
    # --- Masthead ---
    cv.hline(mx, 24, W - 2 * mx, INK, 1)
    tw = cv.text_width("serif_bold_54", TITLE)
    cv.draw_text("serif_bold_54", int((W - tw) / 2), 36, TITLE, INK)
    tw = cv.text_width("sans_bold_16", DATELINE)
    cv.draw_text("sans_bold_16", int((W - tw) / 2), 100, DATELINE, INK)
    cv.hline(mx, 124, W - 2 * mx, INK, 3)
    cv.hline(mx, 130, W - 2 * mx, INK, 1)

    # --- Lead strip: two boxes ---
    ly, lh = 142, 120
    bw = (W - 2 * mx - 8) // 2
    for i, (kicker, head, deck) in enumerate(LEADS):
        bx = mx + i * (bw + 8)
        cv.rect(bx, ly, bw, lh, PAPER)
        cv.hline(bx, ly, bw, INK, 1)
        cv.hline(bx, ly + lh - 1, bw, INK, 1)
        cv.vline(bx, ly, lh, INK, 1)
        cv.vline(bx + bw - 1, ly, lh, INK, 1)
        cv.draw_text("sans_bold_14", bx + 12, ly + 10, kicker, RED)
        draw_para(cv, "serif_bold_22", bx + 12, ly + 32, head, bw - 24, 2, INK, 25)
        draw_para(cv, "sans_14", bx + 12, ly + 86, deck, bw - 24, 2, INK, 16)

    # --- Region grid: 3 cols x 2 rows ---
    col_w = (W - 2 * mx - 2 * 13) // 3
    row_h, row_y = 286, 274
    for idx, (name, color, stories) in enumerate(REGIONS):
        col, row = idx % 3, idx // 3
        bx = mx + col * (col_w + 13)
        by = row_y + row * (row_h + 12)
        cv.rect(bx, by, col_w, 26, color)
        cv.draw_text("sans_bold_15", bx + 10, by + 5, name, (255, 255, 255))
        lead_head, lead_deck = stories[0]
        y = by + 36
        y = draw_para(cv, "sans_bold_15", bx + 4, y, lead_head, col_w - 8, 2, INK, 18)
        y = draw_para(cv, "sans_13", bx + 4, y + 2, lead_deck, col_w - 8, 2, INK, 15)
        y += 6
        cv.hline(bx + 4, y, col_w - 8, GREY, 1)
        y += 8
        for short in stories[1:]:
            y = draw_para(cv, "sans_13", bx + 12, y, "\u2022  " + short, col_w - 16, 2, INK, 15)
            y += 2

    # --- Band: tech, science & sport ---
    band_y, band_h = 870, 106
    cv.rect(mx, band_y, W - 2 * mx, band_h, INK)
    cv.draw_text("sans_bold_14", mx + 12, band_y + 10, "TECH, SCIENCE & SPORT", (255, 90, 90))
    half = (W - 2 * mx - 24) // 2
    for i, item in enumerate(BAND):
        col = i // 3
        row = i % 3
        x = mx + 12 + col * (half + 12)
        y = band_y + 36 + row * 22
        draw_para(cv, "sans_13", x, y, "\u2022  " + item, half, 1, (255, 255, 255), 16)

    # --- Footer ---
    cv.draw_text("sans_11", mx, 992, SOURCES_LINE, GREY)
    tw = cv.text_width("sans_11", FOOTER_RIGHT)
    cv.draw_text("sans_11", W - mx - int(tw), 992, FOOTER_RIGHT, GREY)
    return cv


def main():
    out_dir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(out_dir, exist_ok=True)
    data = png_bytes(render())
    path = os.path.join(out_dir, "entry.png")
    with open(path, "wb") as f:
        f.write(data)
    print(f"wrote {path} ({len(data)} bytes) sha256={hashlib.sha256(data).hexdigest()}")


if __name__ == "__main__":
    main()
