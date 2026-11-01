#!/usr/bin/env python3
"""Draws the first round of LID logo sketches: ten abstract marks, each from one idea in LID.

Every mark is drawn from shapes and strokes, so no file depends on a font.
Each file starts with <rect id="ground">: delete that rect for a transparent mark.
"""
import math
import pathlib

OUT = pathlib.Path(__file__).parent.parent / "explorations" / "abstract-marks"


def svg(slug, title, ground, body, box="0 0 240 240", extra=""):
    x, y, w, h = box.split()
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}" role="img" aria-label="{title}"{extra}>\n'
        f"  <title>{title}</title>\n"
        f'  <rect id="ground" x="{x}" y="{y}" width="{w}" height="{h}" fill="{ground}"/>\n'
        f"{body}\n"
        f"</svg>\n"
    )


def f(n):
    """Trim float noise so the files stay readable."""
    return f"{n:.2f}".rstrip("0").rstrip(".")


# --- 01 Dome: a pot lid built from the letters. D on its back, i as the knob, l as the rim.
def dome():
    lid, knob, ground = "#FFF7EC", "#2A0F0A", "#E23D28"
    body = f"""  <g id="lifted-lid" transform="rotate(-13 120 128)">
    <path id="d-dome" d="M34 150A86 62 0 0 1 206 150Z" fill="{lid}"/>
    <g id="i-knob" fill="{knob}">
      <rect x="111" y="72" width="18" height="17"/>
      <circle cx="120" cy="54" r="12"/>
    </g>
    <rect id="l-rim" x="20" y="158" width="200" height="17" rx="8.5" fill="{knob}"/>
  </g>"""
    return svg("dome", "LID: a lifted pot lid built from the letters l, i, d", ground, body)


# --- Monoline capitals in a unit box (height 1), so the jar lid carries no font.
LETTERS = {
    "L": (0.56, "M0 0V1H.56"),
    "I": (0.0, "M0 0V1"),
    "N": (0.70, "M0 1V0L.7 1V0"),
    "K": (0.64, "M0 0V1M.62 0L0 .6M.2 .42L.64 1"),
    "E": (0.56, "M.56 0H0V1H.56M0 .5H.46"),
    "D": (0.70, "M0 0V1H.2A.5 .5 0 0 0 .2 0Z"),
    "T": (0.62, "M0 0H.62M.31 0V1"),
    "V": (0.70, "M0 0L.35 1L.7 0"),
    "O": (0.86, "M.43 0A.43 .5 0 1 1 .43 1A.43 .5 0 1 1 .43 0Z"),
    "P": (0.58, "M0 1V0H.3A.28 .27 0 0 1 .3 .54H0"),
    "M": (0.86, "M0 1V0L.43 .72L.86 0V1"),
}


def arc_text(text, radius, height, stroke, tracking, cx=120, cy=120, top=True):
    """Lay monoline capitals along an arc. Top arcs read clockwise, bottom arcs read left to right."""
    advances = []
    for i, ch in enumerate(text):
        if ch == " ":
            advances.append(height * 0.62)
        else:
            nxt = text[i + 1] if i + 1 < len(text) else ""
            kern = {"L": -3.5 if nxt == "O" else -1, "T": -1.5}.get(ch, 0)
            advances.append(LETTERS[ch][0] * height + tracking + kern)
    total = sum(advances)
    # Arc length is measured at the letters' middle so spacing looks even.
    mid_r = radius + height / 2
    out = []
    run = -total / 2
    for ch, adv in zip(text, advances):
        if ch != " ":
            w = LETTERS[ch][0] * height
            centre = run + w / 2
            angle = math.degrees(centre / mid_r)
            if top:
                t = f"rotate({f(angle)} {cx} {cy}) translate({f(cx - w / 2)} {f(cy - radius - height)}) scale({height})"
            else:
                t = f"rotate({f(-angle)} {cx} {cy}) translate({f(cx - w / 2)} {f(cy + radius)}) scale({height})"
            out.append(f'    <path d="{LETTERS[ch][1]}" transform="{t}"/>')
        run += adv
    sw = f(stroke / height)
    return (
        f'  <g id="{text.lower().replace(" ", "-")}" fill="none" stroke-width="{sw}" stroke-linecap="square" stroke-linejoin="miter">\n'
        + "\n".join(out)
        + "\n  </g>"
    )


# --- 02 Jar: a canning-jar lid from above. Pale aqua glass-blue, stamped text around the rim.
def jar():
    band, disc, pale, ground = "#0B5A66", "#2FA6B0", "#EFFFFC", "#0A2E36"
    top = arc_text("LINKED INTENT", 72, 15, 2.6, 5.5).replace("<g ", f'<g stroke="{pale}" ')
    bottom = arc_text("DEVELOPMENT", 72, 15, 2.6, 5.5, top=False).replace("<g ", f'<g stroke="{pale}" ')
    h = 40
    sw = f(8.5 / h)
    centre = []
    x = 120 - (0.56 * h + 16 + 0 + 16 + 0.70 * h) / 2
    for ch, w in (("L", 0.56), ("I", 0.0), ("D", 0.70)):
        centre.append(f'    <path d="{LETTERS[ch][1]}" transform="translate({f(x)} {120 - h / 2}) scale({h})"/>')
        x += w * h + 16
    body = f"""  <circle id="knurled-edge" cx="120" cy="120" r="108" fill="none" stroke="{band}" stroke-width="10" stroke-dasharray="4 3.03"/>
  <circle id="screw-band" cx="120" cy="120" r="103" fill="{band}"/>
  <circle id="lid-disc" cx="120" cy="120" r="97" fill="{disc}"/>
  <circle id="seal-ring" cx="120" cy="120" r="63" fill="none" stroke="{pale}" stroke-width="2.6"/>
{top}
{bottom}
  <circle cx="33" cy="120" r="3.4" fill="{pale}"/>
  <circle cx="207" cy="120" r="3.4" fill="{pale}"/>
  <g id="lid-centre" fill="none" stroke="{pale}" stroke-width="{sw}" stroke-linecap="square" stroke-linejoin="miter">
{chr(10).join(centre)}
  </g>"""
    return svg("jar", "LID: canning jar lid seen from above", ground, body)


# --- 03 Eyelid: a heavy-lidded inspector. Every phase gets looked at.
def eyelid():
    lid, eye, ground = "#2B0B4A", "#FFFFFF", "#FF5E8E"
    r = 90
    edge = 106
    dx = math.sqrt(r**2 - (edge - 120) ** 2)
    body = f"""  <circle id="eye" cx="120" cy="120" r="{r}" fill="{eye}"/>
  <circle id="pupil" cx="120" cy="134" r="40" fill="{lid}"/>
  <circle id="glint" cx="136" cy="124" r="8" fill="{eye}"/>
  <path id="lid" d="M{f(120 - dx)} {edge}A{r} {r} 0 0 1 {f(120 + dx)} {edge}Z" fill="{lid}"/>
  <circle id="outline" cx="120" cy="120" r="{r}" fill="none" stroke="{lid}" stroke-width="12"/>"""
    return svg("eyelid", "LID: a heavy-lidded eye", ground, body)


# --- 04 Slot: L and D locked into one block. The I is the space they leave between them.
def slot():
    ink, ground = "#111111", "#FFD60A"
    body = f"""  <path id="l" d="M30 34H72V166H112V206H30Z" fill="{ink}"/>
  <path id="d" d="M118 34H124A86 86 0 0 1 124 206H118Z" fill="{ink}"/>"""
    return svg("slot", "LID: L and D in one block, with the I as the gap between them", ground, body)


# --- 05 Interlock: L threads through D, over the stem and under the bowl.
def interlock():
    l_col, d_col, ground = "#0B5B3E", "#F47FA8", "#FBF4F6"
    sw = 26
    gap = 12
    d_path = "M88 62H110A62 62 0 0 1 110 186H88Z"
    l_path = "M46 26V146H226"
    # The bowl crosses on top of the L. These two short arcs redraw that one crossing.
    bowl_gap = "M171.97 126A62 62 0 0 1 143.77 176"
    bowl_top = "M171.7 118A62 62 0 0 1 135.2 180.6"
    body = f"""  <path id="d" d="{d_path}" fill="none" stroke="{d_col}" stroke-width="{sw}"/>
  <path id="l-gap" d="{l_path}" fill="none" stroke="{ground}" stroke-width="{sw + gap}"/>
  <path id="l" d="{l_path}" fill="none" stroke="{l_col}" stroke-width="{sw}"/>
  <path id="bowl-gap" d="{bowl_gap}" fill="none" stroke="{ground}" stroke-width="{sw + gap}"/>
  <path id="bowl-over-l" d="{bowl_top}" fill="none" stroke="{d_col}" stroke-width="{sw}"/>"""
    return svg("interlock", "LID: an L threaded through a D", ground, body)


# --- 06 One Line: the word written without lifting the pen.
ONE_LINE_PATH = (
    "M18 164"
    "C42 158 82 112 88 74"
    "C92 48 70 40 62 66"
    "C54 92 50 132 58 154"
    "C66 176 88 166 100 146"
    "C106 136 110 124 112 114"
    "C108 134 104 154 114 164"
    "C122 172 134 160 141 132"
    "C145 118 156 110 166 110"
    "C172 110 178 112 181 116"
    "C178 112 172 110 166 110"
    "C156 110 145 118 141 132"
    "C137 148 146 168 162 167"
    "C176 166 186 150 189 128"
    "C192 104 197 72 200 44"
    "C197 72 192 104 189 128"
    "C186 150 184 170 198 170"
    "C208 170 216 162 224 152"
)


def oneline():
    ink, dot, ground = "#2A1BE0", "#FF4D2E", "#F3F2FF"
    body = f"""  <path id="lid-stroke" d="{ONE_LINE_PATH}" fill="none" stroke="{ink}" stroke-width="11" stroke-linecap="round" stroke-linejoin="round"/>
  <circle id="tittle" cx="117" cy="86" r="8.5" fill="{dot}"/>"""
    return svg("one-line", "LID: the word lid written in one continuous line", ground, body)


# --- 07 Interchange: five parallel lines bend into an L and end as an arrow. HLD, LLD, EARS, tests, code.
def interchange():
    colours = ["#FFC63D", "#FF9A2E", "#F4632B", "#E0344F", "#B22A85"]
    ground = "#23110F"
    cx, cy = 128, 104
    step, sw, r0 = 18, 13, 20
    radii = [r0 + i * step for i in range(5)]
    mid = cy + radii[2]
    half = (radii[4] - radii[0]) / 2 + sw / 2
    tip = 228
    shoulder = tip - half
    clip = f"M0 0H{f(shoulder)}V{f(mid - half)}L{tip} {f(mid)}L{f(shoulder)} {f(mid + half)}V240H0Z"
    lines = []
    for r, c in zip(radii, colours):
        lines.append(
            f'    <path d="M{cx - r} 22V{cy}A{r} {r} 0 0 0 {cx} {cy + r}H240" stroke="{c}"/>'
        )
    body = f"""  <defs><clipPath id="interchange-tip"><path d="{clip}"/></clipPath></defs>
  <g id="five-lines" fill="none" stroke-width="{sw}" clip-path="url(#interchange-tip)">
{chr(10).join(lines)}
  </g>"""
    return svg("interchange", "LID: five parallel lines bending into an L-shaped arrow", ground, body)


# --- 08 Through-line: one thread stitched through five layers, narrowing as it goes.
def throughline():
    band, thread, ground = "#EDF1FF", "#FF4B33", "#16235C"
    tops = [30, 66, 102, 138, 174]
    h = 20
    widths = [184, 156, 128, 100, 72]
    amp = 25
    pitch = 36
    y0 = tops[0] + h / 2
    start = y0 - pitch / 2
    # Sine through the centre of every band, drawn as smooth half-wave beziers.
    y = start
    d = [f"M{f(120 + amp)} {f(start)}"]
    k = 0.3642  # bezier handle length for a half-sine, as a fraction of the half-wave
    cur = amp
    for i in range(5):
        nxt = -cur
        y2 = y + pitch
        d.append(
            f"C{f(120 + cur)} {f(y + pitch * k)} {f(120 + nxt)} {f(y2 - pitch * k)} {f(120 + nxt)} {f(y2)}"
        )
        cur = nxt
        y = y2
    thread_path = "".join(d)
    bands = "\n".join(
        f'    <rect x="{f(120 - w / 2)}" y="{t}" width="{w}" height="{h}"/>' for t, w in zip(tops, widths)
    )
    over = "".join(f'<rect x="0" y="{t - 1}" width="240" height="{h + 2}"/>' for t in (tops[0], tops[2], tops[4]))
    body = f"""  <defs><clipPath id="through-over">{over}</clipPath></defs>
  <path id="thread-behind" d="{thread_path}" fill="none" stroke="{thread}" stroke-width="10"/>
  <g id="five-layers" fill="{band}">
{bands}
  </g>
  <path id="thread-in-front" d="{thread_path}" fill="none" stroke="{thread}" stroke-width="10" clip-path="url(#through-over)"/>
  <path id="needle" d="M{f(120 - amp - 5)} {f(y)}H{f(120 - amp + 5)}L{f(120 - amp)} {f(y + 26)}Z" fill="{thread}"/>"""
    return svg("through-line", "LID: one thread stitched through five narrowing layers", ground, body)


# --- 09 Latent: every program the agent could write narrows into the one you meant.
def latent():
    line, chosen, ground = "#0D3B36", "#0D3B36", "#9DF2D4"
    n = 13
    left, right, top, join, end = 26, 214, 24, 158, 216
    paths = []
    for i in range(n):
        x = left + (right - left) * i / (n - 1)
        paths.append(f'    <path d="M{f(x)} {top}C{f(x)} 96 120 104 120 {join}"/>')
    body = f"""  <g id="possible-programs" fill="none" stroke="{line}" stroke-width="2.6" stroke-linecap="round">
{chr(10).join(paths)}
  </g>
  <path id="the-one-you-meant" d="M120 {join - 26}V{end}" fill="none" stroke="{chosen}" stroke-width="9" stroke-linecap="round"/>"""
    return svg("latent", "LID: many lines narrowing into one", ground, body)


# --- 10 Root Path: the design tree as a 1980s bitmap icon. The lit route is what a spec ID spells out.
def rootpath():
    bg, dim, lit = "#352879", "#8C7FE0", "#FFE14D"
    art = [
        ".................",
        ".......LLL.......",
        ".......LLL.......",
        "........L........",
        "....LLLLLdddd....",
        "....L.......d....",
        "...LLL.....ddd...",
        "...LLL.....ddd...",
        "....L.......d....",
        "..ddLLL...ddddd..",
        "..d...L...d...d..",
        ".ddd.LLL.ddd.ddd.",
        ".ddd.LLL.ddd.ddd.",
    ]
    # Centre the 17-wide art on a 17x17 grid.
    pad_top = (17 - len(art)) // 2
    runs = {"L": [], "d": []}
    for row, line in enumerate(art):
        col = 0
        while col < len(line):
            ch = line[col]
            if ch in runs:
                start = col
                while col < len(line) and line[col] == ch:
                    col += 1
                runs[ch].append(f"M{start} {row + pad_top}h{col - start}v1h-{col - start}z")
            else:
                col += 1
    body = f"""  <path id="other-branches" d="{''.join(runs['d'])}" fill="{dim}"/>
  <path id="root-to-leaf" d="{''.join(runs['L'])}" fill="{lit}"/>"""
    return svg("root-path", "LID: a pixel design tree with one lit path", bg, body, box="0 0 17 17", extra=' shape-rendering="crispEdges"')


MARKS = [
    ("01-dome", dome),
    ("02-jar", jar),
    ("03-eyelid", eyelid),
    ("04-slot", slot),
    ("05-interlock", interlock),
    ("06-one-line", oneline),
    ("07-interchange", interchange),
    ("08-through-line", throughline),
    ("09-latent", latent),
    ("10-root-path", rootpath),
]

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in MARKS:
        (OUT / f"{name}.svg").write_text(fn())
    print("wrote", len(MARKS), "marks to", OUT)
