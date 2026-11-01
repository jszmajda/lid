#!/usr/bin/env python3
"""Draws the first round of LID wordmark sketches.

Letters are drawn from shapes and strokes, so no file depends on a font or a font license.
Each file starts with <rect id="ground">: delete that rect for a transparent wordmark.
"""
import pathlib

OUT = pathlib.Path(__file__).parent.parent / "explorations" / "first-wordmarks"


def svg(title, ground, body, box="0 0 480 240", extra=""):
    x, y, w, h = box.split()
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}" role="img" aria-label="{title}"{extra}>\n'
        f"  <title>{title}</title>\n"
        f'  <rect id="ground" x="{x}" y="{y}" width="{w}" height="{h}" fill="{ground}"/>\n'
        f"{body}\n"
        f"</svg>\n"
    )


def pts(points):
    return " ".join(f"{round(x, 2)},{round(y, 2)}" for x, y in points)


# --- 01 Lifted: heavy capitals sliced once, with the top of the word lifted off like a lid.
def lifted():
    ink, ground = "#FFF8F0", "#E23D28"
    body = f"""  <g id="word" transform="translate(0 12)" fill="{ink}">
    <g id="lid-of-the-word" transform="translate(0 -7) rotate(-4.5 70 112)">
      <rect id="l-top" x="70" y="58" width="46" height="54"/>
      <rect id="i-top" x="196" y="58" width="46" height="54"/>
      <path id="d-top" d="M262 58H330A80 71 0 0 1 407.7 112H359.8A38 31 0 0 0 328 98H308V112H262Z"/>
    </g>
    <g id="body-of-the-word">
      <path id="l-bottom" d="M70 112H116V160H176V200H70Z"/>
      <rect id="i-bottom" x="196" y="112" width="46" height="88"/>
      <path id="d-bottom" d="M262 112H308V160H328A38 31 0 0 0 359.8 112H407.7A80 71 0 0 1 330 200H262Z"/>
    </g>
  </g>"""
    return svg("LID wordmark: capitals with the top of the word lifted off", ground, body)


# --- 02 Tittle: chunky lowercase. The dot on the i is a tiny pot lid, tipped open.
def tittle():
    ink, lid, ground = "#2A0F0A", "#E23D28", "#FFE3D3"
    body = f"""  <g id="word" fill="none" stroke="{ink}" stroke-width="38" stroke-linecap="round">
    <path id="l" d="M130 44V186"/>
    <path id="i" d="M202 104V186"/>
    <circle id="d-bowl" cx="310" cy="145" r="41"/>
    <path id="d-stem" d="M351 44V186"/>
  </g>
  <g id="tittle-lid" transform="translate(204 58) rotate(-15)" fill="{lid}">
    <circle cx="0" cy="-23" r="6.5"/>
    <path d="M-29 4A29 25 0 0 1 29 4Z"/>
    <rect x="-36" y="8" width="72" height="8" rx="4"/>
  </g>"""
    return svg("lid wordmark: lowercase, with a tiny pot lid as the dot on the i", ground, body)


# --- 03 Underrun: the foot of the L runs under the word and ends as the arrow of intent.
def underrun():
    ink, ground = "#F5F7FF", "#1437E0"
    body = f"""  <g id="word" fill="{ink}">
    <path id="l-and-arrow" d="M52 28H84V165H392V136L444 181L392 226V197H52Z"/>
    <rect id="i" x="136" y="28" width="32" height="118"/>
    <path id="d" fill-rule="evenodd" d="M202 28H264A70 59 0 0 1 264 146H202ZM234 56V118H262A38 31 0 0 0 262 56Z"/>
  </g>"""
    return svg("LID wordmark: the foot of the L runs under the word as an arrow", ground, body)


# --- 04 Nest: a tight block. The I stands on the foot of the L, and the D closes the block.
def nest():
    ink, intent, ground = "#111111", "#E0201B", "#FFD60A"
    body = f"""  <g id="word" fill="{ink}">
    <path id="l" d="M112 34H164V154H216V206H112Z"/>
    <rect id="i" x="170" y="34" width="46" height="114" fill="{intent}"/>
    <path id="d" d="M222 34H282A86 86 0 0 1 282 206H222Z"/>
  </g>"""
    return svg("LID wordmark: a tight block with the I standing on the foot of the L", ground, body)


# --- 05 One Line: the word written in one stroke without lifting the pen.
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
    ink, dot, ground = "#2A1BE0", "#FF4D2E", "#F4F4FF"
    body = f"""  <g id="word" transform="translate(89 -14) scale(1.26)">
    <path id="lid-stroke" d="{ONE_LINE_PATH}" fill="none" stroke="{ink}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
    <circle id="tittle" cx="117" cy="86" r="8" fill="{dot}"/>
  </g>"""
    return svg("lid wordmark: the word written in one continuous line", ground, body)


# --- 06 Five Lines: each letter is drawn with five parallel lines, one per level of the arrow.
def fivelines():
    colours = ["#FFC63D", "#FF9A2E", "#F4632B", "#E0344F", "#B22A85"]  # inner to outer
    ground = "#23110F"
    step, sw = 10, 7
    l_lines, i_lines, d_lines = [], [], []
    for n, c in enumerate(colours):
        r = 8 + n * step
        x = 128 - r
        l_lines.append(f'    <path d="M{x} 40V152A{r} {r} 0 0 0 128 {152 + r}H178" stroke="{c}"/>')
        # The I runs right to left so its colors line up with the L beside it.
        i_lines.append(f'    <path d="M{238 - n * step} 40V200" stroke="{c}"/>')
        inset = (4 - n) * step
        rad = 80 - inset
        d_lines.append(
            f'    <path d="M{258 + inset} {40 + inset}H320A{rad} {rad} 0 0 1 320 {200 - inset}H{258 + inset}Z" stroke="{c}"/>'
        )
    body = f"""  <g id="word" transform="translate(-4 0)" fill="none" stroke-width="{sw}">
  <g id="l">
{chr(10).join(l_lines)}
  </g>
  <g id="i">
{chr(10).join(i_lines)}
  </g>
  <g id="d">
{chr(10).join(d_lines)}
  </g>
  </g>"""
    return svg("LID wordmark: each letter drawn with five parallel lines", ground, body)


# --- 07 Ramp: the word gets heavier from left to right, as intent firms up on its way to code.
def ramp():
    ink, ground = "#0D3B36", "#BFF3DE"
    body = f"""  <g id="word" fill="{ink}">
    <path id="l-hairline" d="M72 44H81V187H150V196H72Z"/>
    <rect id="i-medium" x="176" y="44" width="30" height="152"/>
    <path id="d-black" fill-rule="evenodd" d="M240 44H326A78 76 0 0 1 326 196H240ZM306 74V166H322A24 46 0 0 0 322 74Z"/>
  </g>"""
    return svg("LID wordmark: letters growing from hairline to black", ground, body)


# --- 08 Scribe: blackletter lowercase, with the dot on the i in manuscript red.
def scribe():
    ink, rubric, ground = "#17120E", "#C8281B", "#EFE9DC"
    w = 36
    ascender, xheight, base = 26, 86, 214

    def stem(x, top, forked=False):
        if forked:
            head = [(x, top + 10), (x + w * 0.42, top + 17), (x + w, top)]
        else:
            head = [(x, top + w * 0.45), (x + w * 0.5, top), (x + w, top + w * 0.45)]
        foot = [(x + w, base - w * 0.45), (x + w * 0.5, base), (x, base - w * 0.45)]
        return pts(head + foot)

    l_x, i_x, d_l, d_r = 118, 182, 246, 322
    hair = 3.4
    body = f"""  <g id="word" fill="{ink}">
    <polygon id="l" points="{stem(l_x, ascender, forked=True)}"/>
    <polygon id="i" points="{stem(i_x, xheight)}"/>
    <g id="d">
      <polygon points="{stem(d_l, xheight)}"/>
      <polygon points="{stem(d_r, ascender, forked=True)}"/>
      <polygon points="{pts([(d_l + w * 0.5, xheight), (d_r + 2, xheight - 15), (d_r + 2, xheight + 7), (d_l + w, xheight + w * 0.45)])}"/>
      <polygon points="{pts([(d_l + w * 0.5, base), (d_r + 2, base - 15), (d_r + 2, base - 37), (d_l + w, base - w * 0.45)])}"/>
    </g>
  </g>
  <g id="joins" fill="none" stroke="{ink}" stroke-width="{hair}">
    <path d="M{l_x + w * 0.5} {base}L{i_x + 2} {base - 34}"/>
    <path d="M{i_x + w * 0.5} {base}L{d_l + 2} {base - 34}"/>
  </g>
  <polygon id="tittle" points="{pts([(i_x + w * 0.5, 34), (i_x + w * 0.5 + 16, 52), (i_x + w * 0.5, 70), (i_x + w * 0.5 - 16, 52)])}" fill="{rubric}"/>"""
    return svg("lid wordmark: blackletter lowercase with a red dot on the i", ground, body)


# --- 09 Bitmap: terminal lettering on a pixel grid, with the cursor waiting after the word.
def bitmap():
    bg, text, cursor = "#352879", "#D6D0FF", "#FFE14D"
    l = ["###.", ".##.", ".##.", ".##.", ".##.", ".##.", "####"]
    i = [".##.", "....", "###.", ".##.", ".##.", ".##.", "####"]
    d = ["....##", "....##", ".#####", "##..##", "##..##", "##..##", ".#####"]
    c = ["....", "....", "CCCC", "CCCC", "CCCC", "CCCC", "CCCC"]
    art = [l[n] + "." + i[n] + "." + d[n] + ".." + c[n] for n in range(7)]
    left, top = 2, 3
    runs = {"#": [], "C": []}
    for row, line in enumerate(art):
        col = 0
        while col < len(line):
            ch = line[col]
            if ch in runs:
                start = col
                while col < len(line) and line[col] == ch:
                    col += 1
                runs[ch].append(f"M{start + left} {row + top}h{col - start}v1h-{col - start}z")
            else:
                col += 1
    body = f"""  <path id="word" d="{''.join(runs['#'])}" fill="{text}"/>
  <path id="cursor" d="{''.join(runs['C'])}" fill="{cursor}"/>"""
    return svg(
        "lid wordmark: pixel lettering with a block cursor",
        bg,
        body,
        box="0 0 26 13",
        extra=' shape-rendering="crispEdges"',
    )


# --- 10 Vinculum: carved Roman capitals. L, I and D are all Roman numerals, and the bar over them is the lid.
def vinculum():
    ink, ground = "#1C1A18", "#CFCBC2"
    body = f"""  <g id="word" fill="{ink}">
    <path id="vinculum" d="M84 54Q240 34 396 54Q240 46 84 54Z"/>
    <path id="l" d="M84 78H136V80Q124 82 124 94V186Q124 192 132 192H156Q176 192 188 164L192 165L184 202H84V200Q98 198 98 186V94Q98 82 84 80Z"/>
    <path id="i" d="M208 78H260V80Q247 82 247 94V186Q247 198 260 200V202H208V200Q221 198 221 186V94Q221 82 208 80Z"/>
    <path id="d" fill-rule="evenodd" d="M280 78H334C372 78 398 104 398 140C398 176 370 202 334 202H280V200Q293 198 293 186V94Q293 82 280 80ZM319 88V182Q319 192 334 192C358 192 372 170 372 140C372 110 358 88 334 88Z"/>
  </g>"""
    return svg("LID wordmark: Roman capitals with a bar over the word", ground, body)


MARKS = [
    ("01-lifted", lifted),
    ("02-tittle", tittle),
    ("03-underrun", underrun),
    ("04-nest", nest),
    ("05-one-line", oneline),
    ("06-five-lines", fivelines),
    ("07-ramp", ramp),
    ("08-scribe", scribe),
    ("09-bitmap", bitmap),
    ("10-vinculum", vinculum),
]

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in MARKS:
        (OUT / f"{name}.svg").write_text(fn())
    print("wrote", len(MARKS), "wordmarks to", OUT)
