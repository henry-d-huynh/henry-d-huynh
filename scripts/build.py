"""Builds the profile README's artwork in assets/, in the look of henners.io:
ink and colour panels, Bricolage display type, hard ink shadows, stickers,
and motion (CSS keyframes inside each SVG, which GitHub plays).

An SVG shown as an image can't load fonts, so every word is converted to
outlines here from the site's own fonts (scripts/fonts, SIL OFL). The logos
and the X mark are copies from the henners-io-v2 repo (scripts/logos).

Run: pip install fonttools && python3 scripts/build.py
"""

import math
import re
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "scripts" / "fonts"
LOGOS = ROOT / "scripts" / "logos"
OUT = ROOT / "assets"

INK = "#15121b"
PAPER = "#f4f0e8"
PAPER2 = "#fffcf6"
ORANGE = "#ff7a1a"
MAGENTA = "#e438e4"
BLUE = "#2f6bff"
YELLOW = "#ffd23f"
CYAN = "#19a8e6"
PINK = "#ff3d8f"
VIOLET = "#5b2ee8"
GREEN = "#3ee07a"
WHITE = "#ffffff"


# ---------------------------------------------------------------------------
# text as outlines
# ---------------------------------------------------------------------------


class Face:
    """One font, able to lay a line of text out as SVG path data."""

    def __init__(self, file):
        font = TTFont(FONTS / file)
        self.glyph_set = font.getGlyphSet()
        self.cmap = font.getBestCmap()
        self.advances = font["hmtx"]
        self.units = font["head"].unitsPerEm

    def glyphs(self, text, size, x, y, tracking=0.0):
        """[(char, path data, left x, advance)] for `text` on baseline y.
        `tracking` is in ems, like CSS letter-spacing."""
        scale = size / self.units
        cursor = x
        laid = []
        for char in text:
            name = self.cmap.get(ord(char), ".notdef")
            advance = self.advances[name][0] * scale
            pen = SVGPathPen(self.glyph_set)
            self.glyph_set[name].draw(TransformPen(pen, (scale, 0, 0, -scale, cursor, y)))
            laid.append((char, pen.getCommands(), cursor, advance))
            cursor += advance + tracking * size
        return laid

    def width(self, text, size, tracking=0.0):
        laid = self.glyphs(text, size, 0, 0, tracking)
        return laid[-1][2] + laid[-1][3] if laid else 0


DISPLAY = Face("bricolage-condensed-800.ttf")
BODY = Face("space-grotesk-500.ttf")
BOLD = Face("space-grotesk-700.ttf")
MONO = Face("jetbrains-mono-600.ttf")


def text(face, string, size, x, y, fill, tracking=0.0, anchor="start", extra=""):
    """A line of text as one <path>. `anchor` is start, middle or end."""
    if anchor != "start":
        width = face.width(string, size, tracking)
        x -= width / 2 if anchor == "middle" else width
    data = "".join(d for _, d, _, _ in face.glyphs(string, size, x, y, tracking))
    return f'<path d="{data}" fill="{fill}" {extra}/>'


def letters(face, string, size, x, y, fill, tracking=0.0, css="drop", delay=0.0, step=0.06, colours=None):
    """Each glyph as its own <path> so it can animate on its own beat."""
    parts = []
    for index, (char, data, _, _) in enumerate(face.glyphs(string, size, x, y, tracking)):
        if not data:
            continue
        colour = (colours or {}).get(index, fill)
        parts.append(
            f'<path class="{css}" style="animation-delay:{delay + index * step:.2f}s" d="{data}" fill="{colour}"/>'
        )
    return "".join(parts)


# ---------------------------------------------------------------------------
# shared pieces
# ---------------------------------------------------------------------------

# Motion every SVG shares. transform-box: fill-box makes each piece turn and
# scale around its own centre. Reduced motion shows the finished frame.
BASE_CSS = """
.drop { animation: drop 0.9s cubic-bezier(0.3, 1.5, 0.5, 1) both; transform-box: fill-box; transform-origin: 50% 100%; }
.pop { animation: pop 0.7s cubic-bezier(0.3, 1.6, 0.5, 1) both; transform-box: fill-box; transform-origin: 50% 50%; }
.rise { animation: rise 0.8s cubic-bezier(0.22, 1, 0.36, 1) both; }
.bob { animation: bob 5s ease-in-out infinite; transform-box: fill-box; transform-origin: 50% 50%; }
.spin { animation: spin 22s linear infinite; transform-box: fill-box; transform-origin: 50% 50%; }
@keyframes drop { from { transform: translateY(-60px) rotate(-10deg) scale(0.9); opacity: 0; } to { transform: none; opacity: 1; } }
@keyframes pop { from { transform: scale(0) rotate(-25deg); opacity: 0; } to { transform: none; opacity: 1; } }
@keyframes rise { from { transform: translateY(30px); opacity: 0; } to { transform: none; opacity: 1; } }
@keyframes bob { 0%, 100% { transform: translateY(0) rotate(0deg); } 50% { transform: translateY(-10px) rotate(6deg); } }
@keyframes spin { to { transform: rotate(360deg); } }
@media (prefers-reduced-motion: reduce) { * { animation: none !important; } }
/* GitHub's dark theme: ink shadows would vanish, so they turn paper, the way
   the site's ink sections do it */
@media (prefers-color-scheme: dark) { .shadow { fill: #f4f0e8; } .edge { stroke-opacity: 0.25; } }
"""


def svg(width, height, body, css="", label=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{label}">'
        f"<title>{label}</title><style>{BASE_CSS}{css}</style>{body}</svg>\n"
    )


def nested(file, x, y, width, height):
    """Another SVG file placed as a nested <svg> (its viewBox kept)."""
    source = (LOGOS / file).read_text()
    view_box = re.search(r'viewBox="([^"]+)"', source).group(1)
    inner = re.sub(r"^<svg[^>]*>|</svg>\s*$", "", source.strip())
    return f'<svg x="{x}" y="{y}" width="{width}" height="{height}" viewBox="{view_box}">{inner}</svg>'


def star(cx, cy, size, fill, css=""):
    points = []
    for index in range(12):
        radius = size * (0.42 if index % 2 else 1)
        angle = math.pi / 6 * index - math.pi / 2
        points.append(f"{cx + radius * math.cos(angle):.1f},{cy + radius * math.sin(angle):.1f}")
    return f'<polygon class="{css}" points="{" ".join(points)}" fill="{fill}" stroke="{INK}" stroke-width="5" stroke-linejoin="round"/>'


def pill(x, y, w, h, fill, label, colour=INK, face=BOLD, size=20, shadow=INK, css="", delay=0.0):
    return (
        f'<g class="{css}" style="animation-delay:{delay:.2f}s">'
        f'<rect class="{"shadow" if shadow == INK else ""}" x="{x + 5}" y="{y + 5}" width="{w}" height="{h}" rx="{h / 2}" fill="{shadow}"/>'
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{h / 2}" fill="{fill}" stroke="{INK}" stroke-width="3"/>'
        + text(face, label, size, x + w / 2, y + h / 2 + size * 0.36, colour, anchor="middle")
        + "</g>"
    )


def progress_bar(width, radius):
    """The site's scroll-progress gradient along the top, clipped to the card."""
    return (
        '<defs><linearGradient id="brand" x1="0" x2="1">'
        f'<stop offset="0" stop-color="{ORANGE}"/><stop offset="0.5" stop-color="{MAGENTA}"/>'
        f'<stop offset="1" stop-color="{BLUE}"/></linearGradient>'
        f'<clipPath id="card"><rect width="{width}" height="2000" rx="{radius}"/></clipPath></defs>'
        f'<rect width="{width}" height="8" fill="url(#brand)" clip-path="url(#card)"/>'
    )


# The X mark (henners.io's icon): its bars snap a quarter turn every few
# seconds, magenta a beat behind yellow, so they scissor and land as an X.
MARK_CSS = """
.mark-back, .mark-front { animation: snap 6s cubic-bezier(0.3, 1.8, 0.5, 1) infinite; transform-box: view-box; transform-origin: 30px 30px; }
.mark-front { animation-delay: 0.08s; }
@keyframes snap { 0%, 40% { transform: rotate(0deg); } 50%, 90% { transform: rotate(90deg); } 100% { transform: rotate(180deg); } }
"""


# ---------------------------------------------------------------------------
# the pieces
# ---------------------------------------------------------------------------


def hero():
    w, h, r = 1200, 470, 28
    name = "Henners."
    body = [
        f'<rect class="edge" x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{r}" fill="{INK}" stroke="{PAPER}" stroke-opacity="0" stroke-width="2"/>',
        progress_bar(w, r),
        # stickers
        f'<g class="pop" style="animation-delay:0.9s"><g class="bob">{star(716, 96, 40, MAGENTA)}</g></g>',
        f'<g class="pop" style="animation-delay:1.05s"><g class="bob" style="animation-delay:-1.5s">'
        f'<circle cx="1140" cy="72" r="30" fill="{ORANGE}" stroke="{INK}" stroke-width="5"/>'
        f'<circle cx="1140" cy="72" r="40" fill="none" stroke="{ORANGE}" stroke-width="3"/></g></g>',
        f'<g class="pop" style="animation-delay:1.2s"><g class="bob" style="animation-delay:-3s">'
        f'<path d="M738 430c12-20 23-20 30 0s19 20 28 0 21-20 28 0" fill="none" stroke="{BLUE}" stroke-width="10" stroke-linecap="round"/></g></g>',
        # pill
        f'<g class="rise" style="animation-delay:0.05s">'
        f'<rect x="56" y="48" width="420" height="46" rx="23" fill="{PAPER}" fill-opacity="0.08" stroke="{PAPER}" stroke-opacity="0.3" stroke-width="2"/>'
        f'<circle cx="82" cy="71" r="7" fill="{GREEN}"/>'
        + text(BOLD, "Full-stack developer, Melbourne VIC", 20, 100, 78, PAPER)
        + "</g>",
        # headline
        f'<g class="rise" style="animation-delay:0.1s">' + text(DISPLAY, "Hi, I'm", 66, 54, 176, YELLOW, -0.02) + "</g>",
        letters(DISPLAY, name, 196, 48, 340, PAPER, -0.035, delay=0.25, step=0.065, colours={len(name) - 1: MAGENTA}),
        # lines
        f'<g class="rise" style="animation-delay:0.85s">'
        + text(BODY, "I design, build and ship products end to end,", 25, 56, 394, PAPER, extra='fill-opacity="0.85"')
        + text(BODY, "from the database schema to the last pixel.", 25, 56, 428, PAPER, extra='fill-opacity="0.85"')
        + "</g>",
    ]
    # the X badge with its orbiting phrase
    cx, cy, ring = 1004, 262, 104
    orbit = "DESIGN IT • BUILD IT • SHIP IT • REPEAT • "
    size = 17
    radius = ring + 54
    pitch = 2 * math.pi * radius / len(orbit)
    glyph_parts = []
    for index, char in enumerate(orbit):
        if char == " ":
            continue
        angle = -90 + 360 * index / len(orbit)
        advance = MONO.width(char, size)
        data = "".join(d for _, d, _, _ in MONO.glyphs(char, size, -advance / 2, -radius + size * 0.36))
        glyph_parts.append(f'<path d="{data}" fill="{PAPER}" transform="rotate({angle + 90:.2f})"/>')
    body.append(
        f'<g class="pop" style="animation-delay:0.6s"><g transform="translate({cx} {cy})">'
        f'<g class="spin">{"".join(glyph_parts)}</g></g>'
        f'<circle cx="{cx}" cy="{cy}" r="{ring + 12}" fill="{MAGENTA}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{ring + 4}" fill="{INK}"/>'
        f'<circle cx="{cx}" cy="{cy}" r="{ring}" fill="{PAPER}"/>'
        + nested("favicon.svg", cx - 82, cy - 82, 164, 164)
        + "</g>"
    )
    return svg(w, h, "".join(body), MARK_CSS, "Hi, I'm Henners: full-stack developer in Melbourne. I design, build and ship products end to end.")


def project_card(number, fill, colour, status, summary, logo, angle, delay, label, ground=""):
    """One project as a tilted brand-colour card with a hard shadow.
    `ground` is extra layers painted over the fill, inside the outline."""
    w, h = 400, 316
    cw, ch = 340, 252
    x, y = 26, 26
    lines = summary.split("\n")
    inner = [
        f'<rect class="shadow" x="{x + 10}" y="{y + 10}" width="{cw}" height="{ch}" rx="24" fill="{INK}"/>',
        f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="24" fill="{fill}"/>',
        ground(x, y, cw, ch) if ground else "",
        f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="24" fill="none" stroke="{INK}" stroke-width="4"/>',
        text(DISPLAY, number, 38, x + 22, y + 54, colour),
    ]
    status_width = MONO.width(status, 12.5, 0.08) + 26
    inner.append(
        f'<rect x="{x + 78}" y="{y + 26}" width="{status_width:.1f}" height="30" rx="15" fill="none" stroke="{colour}" stroke-width="2.5"/>'
        + text(MONO, status, 12.5, x + 91, y + 46, colour, 0.08)
    )
    inner.append(logo(x + 22, y + 78))
    for index, line in enumerate(lines):
        inner.append(text(BOLD, line, 17.5, x + 24, y + 158 + index * 24, colour))
    inner.append(pill(x + 22, y + ch - 56, 132, 36, INK, "Explore →", PAPER2, BOLD, 15, shadow=INK))
    body = (
        f'<g class="pop" style="animation-delay:{delay:.2f}s">'
        f'<g transform="rotate({angle} {w / 2} {h / 2})">{"".join(inner)}</g></g>'
    )
    return svg(w, h, body, "", label)


YAY_MINT = "#2fe39a"
YAY_SKY = "#4d7cff"
YAY_ROSE = "#ff5c8a"
YAY_BUTTER = "#ffd84d"
RECEIPT = "M28 10H92V96L84 106L76 96L68 106L60 96L52 106L44 96L36 106L28 96Z"


def yaysheet_ground(x, y, w, h):
    """yaysheet's paper with a mint, sky and rose glow in three corners."""
    glows = [("mint", YAY_MINT, 0.45, 0, 0, 0.45), ("sky", YAY_SKY, 0.4, 1, 0.3, 0.45), ("rose", YAY_ROSE, 0.4, 0.6, 1.1, 0.5)]
    defs = "".join(
        f'<radialGradient id="glow-{name}" gradientUnits="userSpaceOnUse" cx="{x + w * cx:.1f}" cy="{y + h * cy:.1f}" r="{math.hypot(w, h) * r:.1f}">'
        f'<stop offset="0" stop-color="{colour}" stop-opacity="{alpha}"/><stop offset="1" stop-color="{colour}" stop-opacity="0"/></radialGradient>'
        for name, colour, alpha, cx, cy, r in glows
    )
    return f"<defs>{defs}</defs>" + "".join(
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="24" fill="url(#glow-{name})"/>' for name, *_ in glows
    )


def yaysheet_logo(x, y):
    """yaysheet's logo, as on henners.io: the stamped receipt, then the
    stacked wordmark with "yay" in the gradient over an ink outline and a
    hard rose shadow."""
    mark = (
        f'<g transform="translate({x - 4} {y - 14}) scale(0.52)">'
        f'<path d="{RECEIPT}" transform="translate(7 7)" fill="{YAY_ROSE}"/>'
        f'<path d="{RECEIPT}" fill="#fffdf8" stroke="{INK}" stroke-width="6" stroke-linejoin="round"/>'
        f'<rect x="38" y="22" width="30" height="6" rx="3" fill="{INK}"/>'
        f'<rect x="38" y="34" width="44" height="6" rx="3" fill="#77738a"/>'
        f'<line x1="38" y1="50" x2="82" y2="50" stroke="{INK}" stroke-width="2.5" stroke-dasharray="4 3"/>'
        f'<g transform="rotate(-14 60 72)">'
        f'<rect x="12" y="56" width="96" height="34" rx="8" fill="{YAY_BUTTER}" stroke="{INK}" stroke-width="5"/>'
        f'<rect x="17" y="61" width="86" height="24" rx="5" fill="none" stroke="{INK}" stroke-width="2"/>'
        + text(DISPLAY, "YAY!", 24, 60, 81, INK, 0.04, "middle")
        + "</g></g>"
    )
    wx, size = x + 68, 40
    yay_y = y + 26
    gradient = (
        f'<defs><linearGradient id="yay" gradientUnits="userSpaceOnUse" x1="{wx}" y1="0" x2="{wx + DISPLAY.width("yay", size, -0.035)}" y2="0">'
        f'<stop offset="0" stop-color="{YAY_MINT}"/><stop offset="0.55" stop-color="{YAY_SKY}"/><stop offset="1" stop-color="{YAY_ROSE}"/></linearGradient></defs>'
    )
    word = (
        text(DISPLAY, "yay", size, wx + 2, yay_y + 2, YAY_ROSE, -0.035, extra=f'stroke="{YAY_ROSE}" stroke-width="4" stroke-linejoin="round"')
        + text(DISPLAY, "yay", size, wx, yay_y, INK, -0.035, extra=f'stroke="{INK}" stroke-width="4" stroke-linejoin="round"')
        + text(DISPLAY, "yay", size, wx, yay_y, "url(#yay)", -0.035)
        + text(DISPLAY, "sheet", 27, wx, yay_y + 26, INK, -0.035)
    )
    return gradient + mark + word


def projects():
    cards = {
        "headsup": project_card(
            "01", PINK, WHITE, "OPEN BETA, AU",
            "Invite pages sent by text, with\nevery RSVP tracked per guest.",
            lambda x, y: nested("headsup-lockup-horizontal-reversed-on-pink.svg", x - 4, y - 6, 200, 58),
            -3, 0.1, "HeadsUp: invite pages sent by text, with every RSVP tracked per guest. Open beta in Australia.",
        ),
        "yeslane": project_card(
            "02", VIOLET, WHITE, "COMING SOON",
            "A white-label client portal\nfor small marketing agencies.",
            lambda x, y: nested("yeslane-logo-white.svg", x - 2, y - 14, 168, 79),
            2, 0.25, "Yeslane: a white-label client portal for small marketing agencies. Coming soon.",
        ),
        "yaysheet": project_card(
            "03", PAPER, INK, "COMING SOON",
            "Interactive quotes clients pick\nfrom, ask about and accept.",
            yaysheet_logo,
            3, 0.4, "yaysheet: interactive quotes clients pick from, ask about and accept in a tap. Coming soon.",
            ground=yaysheet_ground,
        ),
        "scaffy": project_card(
            "04", CYAN, INK, "OPEN SOURCE, MIT",
            "A serverless headless CMS you\nself-host on your own AWS.",
            lambda x, y: text(DISPLAY, "Scaffy CMS", 54, x, y + 46, INK, -0.02),
            -2, 0.55, "Scaffy CMS: an open-source serverless headless CMS you self-host on AWS. Paused.",
        ),
    }
    return cards


def steps():
    w, h = 1200, 230
    beats = [
        ("01", "Sketch it.", "Problem first, then a plan.", PAPER2, INK, -2),
        ("02", "Build it.", "TypeScript end to end, on AWS.", BLUE, PAPER2, 1.5),
        ("03", "Ship it.", "Real people, then the write-up.", MAGENTA, PAPER2, -1.5),
    ]
    cw, ch, gap = 360, 168, 30
    body = []
    for index, (number, title, line, fill, colour, angle) in enumerate(beats):
        x = 6 + index * (cw + gap)
        y = 22
        group = [
            f'<rect class="shadow" x="{x + 9}" y="{y + 9}" width="{cw}" height="{ch}" rx="22" fill="{INK}"/>',
            f'<rect x="{x}" y="{y}" width="{cw}" height="{ch}" rx="22" fill="{fill}" stroke="{INK}" stroke-width="4"/>',
            f'<rect x="{x + 22}" y="{y + 22}" width="50" height="30" rx="15" fill="none" stroke="{colour}" stroke-width="2.5"/>',
            text(MONO, number, 15, x + 47, y + 42, colour, anchor="middle"),
            text(DISPLAY, title, 64, x + 20, y + 118, colour, -0.03),
            text(BODY, line, 18, x + 22, y + 150, colour),
        ]
        body.append(
            f'<g class="pop" style="animation-delay:{0.15 + index * 0.2:.2f}s">'
            f'<g transform="rotate({angle} {x + cw / 2} {y + ch / 2})">{"".join(group)}</g></g>'
        )
    # the stamp slams onto the last card
    sx, sy = 1004, 6
    stamp = (
        f'<rect class="shadow" x="{sx + 5}" y="{sy + 5}" width="170" height="52" rx="12" fill="{INK}"/>'
        f'<rect x="{sx}" y="{sy}" width="170" height="52" rx="12" fill="{YELLOW}" stroke="{INK}" stroke-width="4"/>'
        + text(DISPLAY, "SHIPPED!", 36, sx + 85, sy + 39, INK, anchor="middle")
    )
    body.append(f'<g class="slam"><g transform="rotate(8 {sx + 85} {sy + 26})">{stamp}</g></g>')
    css = """
.slam { animation: slam 0.5s cubic-bezier(0.3, 1.8, 0.5, 1) 1.1s both; transform-box: fill-box; transform-origin: 50% 50%; }
@keyframes slam { from { transform: scale(3) rotate(-30deg); opacity: 0; } to { transform: none; opacity: 1; } }
"""
    return svg(w, h, "".join(body), css, "How I work: 01 Sketch it, problem first. 02 Build it, TypeScript end to end on AWS. 03 Ship it.")


def stack():
    tools = [
        ("TypeScript", BLUE, WHITE), ("React", YELLOW, INK), ("Astro", MAGENTA, WHITE),
        ("Vite", PAPER2, INK), ("Node.js", ORANGE, INK), ("AWS Lambda", ORANGE, INK),
        ("DynamoDB", BLUE, WHITE), ("AWS CDK", YELLOW, INK), ("Cognito", PAPER2, INK),
        ("CloudFront + S3", MAGENTA, WHITE), ("Stripe", VIOLET, WHITE), ("Zod", CYAN, INK),
        ("Vitest", YELLOW, INK), ("GSAP", PAPER2, INK),
    ]
    w = 1200
    size, h, pad, gap = 19, 50, 24, 16
    rows, row, x = [], [], 0
    for label, fill, colour in tools:
        width = MONO.width(label, size) + pad * 2
        if row and x + width > w - 20:
            rows.append((row, x - gap))
            row, x = [], 0
        row.append((label, fill, colour, width, x))
        x += width + gap
    rows.append((row, x - gap))
    body, index = [], 0
    for row_index, (row, row_width) in enumerate(rows):
        offset = (w - row_width) / 2
        y = 14 + row_index * (h + 22)
        for label, fill, colour, width, x in row:
            body.append(pill(offset + x, y, width, h, fill, label, colour, MONO, size, css="pop", delay=0.05 * index))
            index += 1
    height = 14 + len(rows) * (h + 22)
    return svg(w, height, "".join(body), "", "Stack: " + ", ".join(t[0] for t in tools))


def outro():
    w, h, r = 1200, 360, 28
    line = "Let's make something fun."
    words = line.split(" ")
    size = 92
    total = DISPLAY.width(line, size, -0.03)
    x = (w - total) / 2
    parts, cursor = [], x
    for index, word in enumerate(words):
        parts.append(
            f'<g class="drop" style="animation-delay:{0.7 + index * 0.1:.2f}s">'
            + text(DISPLAY, word, size, cursor, 196, INK, -0.03)
            + "</g>"
        )
        cursor += DISPLAY.width(word + " ", size, -0.03)
    body = [
        f'<clipPath id="bloom"><circle class="bloom" cx="{w / 2}" cy="{h / 2}" r="{w * 0.7}"/></clipPath>',
        f'<rect width="{w}" height="{h}" rx="{r}" fill="{INK}"/>',
        f'<g clip-path="url(#bloom)"><rect width="{w}" height="{h}" rx="{r}" fill="{ORANGE}"/></g>',
        f'<g class="pop" style="animation-delay:0.5s">' + nested("favicon.svg", w / 2 - 46, 30, 84, 84) + "</g>",
        "".join(parts),
        pill(w / 2 - 175, 242, 350, 58, INK, "Say hello at henners.io →", PAPER2, BOLD, 21, shadow=PAPER2, css="rise", delay=1.2),
    ]
    css = """
.bloom { animation: bloom 1s cubic-bezier(0.22, 1, 0.36, 1) 0.1s both; transform-box: fill-box; transform-origin: 50% 50%; }
@keyframes bloom { from { transform: scale(0.06); } to { transform: none; } }
"""
    return svg(w, h, "".join(body), MARK_CSS + css, "Let's make something fun. Say hello at henners.io.")


def main():
    OUT.mkdir(exist_ok=True)
    files = {"hero.svg": hero(), "steps.svg": steps(), "stack.svg": stack(), "outro.svg": outro()}
    for project, card in projects().items():
        files[f"project-{project}.svg"] = card
    for name, content in files.items():
        (OUT / name).write_text(content)
        print(f"assets/{name}  {len(content) / 1024:.1f} KB")


if __name__ == "__main__":
    main()
