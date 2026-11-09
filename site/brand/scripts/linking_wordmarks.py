#!/usr/bin/env python3
"""Draws the LID wordmarks whose main idea is linking.

Letters are drawn from shapes and strokes, so no file depends on a font or a font license.
Each file starts with <rect id="ground">: delete that rect for a transparent wordmark,
except where a mark paints over-and-under gaps in the ground color (Chain).
"""
import math
import pathlib

OUT = pathlib.Path(__file__).parent.parent / "explorations" / "linking-wordmarks"


def svg(title, ground, body, box="0 0 480 240"):
    x, y, w, h = box.split()
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}" role="img" aria-label="{title}">\n'
        f"  <title>{title}</title>\n"
        f'  <rect id="ground" x="{x}" y="{y}" width="{w}" height="{h}" fill="{ground}"/>\n'
        f"{body}\n"
        f"</svg>\n"
    )


# --- 01 Linked List: each letter is a node, and each node points to the next. D points to null.
def linked_list():
    ink, cell, ground = "#111111", "#FFFFFF", "#FFD60A"
    w, h, y, split = 124, 110, 65, 84
    xs = [32, 178, 324]
    mid = y + h / 2
    top, bottom = 89, 151
    letters = [
        lambda c: f"M{c - 16} {top}V{bottom}H{c + 18}",
        lambda c: f"M{c} {top}V{bottom}",
        lambda c: f"M{c - 20} {top}H{c - 4}A24 31 0 0 1 {c - 4} {bottom}H{c - 20}Z",
    ]
    nodes, pointers = [], []
    for n, x in enumerate(xs):
        c = x + split / 2
        nodes.append(
            f'    <g id="node-{"lid"[n]}">\n'
            f'      <rect x="{x}" y="{y}" width="{w}" height="{h}" fill="{cell}" stroke="{ink}" stroke-width="7"/>\n'
            f'      <path d="M{x + split} {y}V{y + h}" fill="none" stroke="{ink}" stroke-width="7"/>\n'
            f'      <path d="{letters[n](c)}" fill="none" stroke="{ink}" stroke-width="12"/>\n'
            f"    </g>"
        )
        dot = x + split + (w - split) / 2
        if n < 2:
            tip = xs[n + 1] - 3.5
            pointers.append(
                f'    <circle cx="{dot}" cy="{mid}" r="7" fill="{ink}"/>\n'
                f'    <path d="M{dot} {mid}H{tip - 10}" fill="none" stroke="{ink}" stroke-width="6"/>\n'
                f'    <path d="M{tip - 13} {mid - 10}L{tip} {mid}L{tip - 13} {mid + 10}Z" fill="{ink}"/>'
            )
        else:
            pointers.append(
                f'    <path id="null" d="M{x + split} {y + h}L{x + w} {y}" fill="none" stroke="{ink}" stroke-width="7"/>'
            )
    body = f"""  <g id="nodes">
{chr(10).join(nodes)}
  </g>
  <g id="pointers">
{chr(10).join(pointers)}
  </g>"""
    return svg("LID wordmark: three linked-list nodes, one letter each", ground, body)


# --- 02 Chain: the lowercase word as interlocked links, passing over and under each other.
def chain():
    ink, pale, ground = "#171717", "#FFF3E0", "#FF7A1A"
    sw = 12

    def stadium(x0, x1, top, bottom):
        r = (x1 - x0) / 2
        d = f"M{x0} {top + r}A{r} {r} 0 0 1 {x1} {top + r}V{bottom - r}A{r} {r} 0 0 1 {x0} {bottom - r}Z"
        cx = (x0 + x1) / 2
        p = []
        for n in range(121):
            a = math.pi + math.pi * n / 120
            p.append((cx + r * math.cos(a), top + r + r * math.sin(a)))
        for n in range(121):
            a = math.pi * n / 120
            p.append((cx + r * math.cos(a), bottom - r + r * math.sin(a)))
        return d, p

    def ring(cx, cy, r):
        d = f"M{cx - r} {cy}A{r} {r} 0 1 1 {cx + r} {cy}A{r} {r} 0 1 1 {cx - r} {cy}Z"
        return d, [(cx + r * math.cos(2 * math.pi * n / 300), cy + r * math.sin(2 * math.pi * n / 300)) for n in range(300)]

    def crossings(a, b):
        found = []
        for i in range(len(a)):
            p1, p2 = a[i], a[(i + 1) % len(a)]
            for j in range(len(b)):
                q1, q2 = b[j], b[(j + 1) % len(b)]
                den = (p2[0] - p1[0]) * (q2[1] - q1[1]) - (p2[1] - p1[1]) * (q2[0] - q1[0])
                if abs(den) < 1e-9:
                    continue
                t = ((q1[0] - p1[0]) * (q2[1] - q1[1]) - (q1[1] - p1[1]) * (q2[0] - q1[0])) / den
                u = ((q1[0] - p1[0]) * (p2[1] - p1[1]) - (q1[1] - p1[1]) * (p2[0] - p1[0])) / den
                if 0 <= t < 1 and 0 <= u < 1:
                    found.append((p1[0] + t * (p2[0] - p1[0]), p1[1] + t * (p2[1] - p1[1])))
        return sorted(found, key=lambda c: c[1])

    links = [
        ("l", ink, stadium(58, 116, 30, 202)),
        ("i", pale, stadium(94, 152, 92, 202)),
        ("d-bowl", ink, ring(185, 147, 55)),
        ("d-stem", ink, stadium(218, 276, 30, 202)),
    ]
    base = "\n".join(f'      <path id="{n}" d="{g[0]}" stroke="{c}"/>' for n, c, g in links)
    defs, over = [], []
    count = 0
    for k in range(3):
        name_a, col_a, geo_a = links[k]
        name_b, col_b, geo_b = links[k + 1]
        points = crossings(geo_a[1], geo_b[1])
        # Upper crossing: the left link passes in front. Lower crossing: the right link does.
        for (x, y), (d, col) in zip(points, ((geo_a[0], col_a), (geo_b[0], col_b))):
            x, y = round(x, 1), round(y, 1)
            defs.append(
                f'    <clipPath id="chain-gap-{count}"><circle cx="{x}" cy="{y}" r="14"/></clipPath>\n'
                f'    <clipPath id="chain-top-{count}"><circle cx="{x}" cy="{y}" r="16"/></clipPath>'
            )
            over.append(
                f'      <g clip-path="url(#chain-gap-{count})"><path d="{d}" stroke="{ground}" stroke-width="{sw + 9}"/></g>\n'
                f'      <g clip-path="url(#chain-top-{count})"><path d="{d}" stroke="{col}" stroke-width="{sw}"/></g>'
            )
            count += 1
    body = f"""  <defs>
{chr(10).join(defs)}
  </defs>
  <g id="word" transform="translate(240 120) scale(1.14) translate(-167 -116)">
    <g id="links" fill="none" stroke-width="{sw}">
{base}
    </g>
    <g id="crossings" fill="none">
{chr(10).join(over)}
    </g>
    <circle id="tittle" cx="137" cy="62" r="11" fill="{pale}"/>
  </g>"""
    return svg("lid wordmark: the word as interlocked chain links", ground, body)


# --- 03 Hinged: the top of the word opens like a lid, and a hinge keeps it attached to the body.
def hinged():
    ink, pin, ground = "#FFF8F0", "#2A0F0A", "#E23D28"
    body = f"""  <g id="word" transform="translate(10 15)">
    <g id="lid-of-the-word" fill="{ink}" transform="rotate(-8 64 112)">
      <rect id="l-top" x="70" y="58" width="46" height="54"/>
      <rect id="i-top" x="196" y="58" width="46" height="54"/>
      <path id="d-top" d="M262 58H330A80 71 0 0 1 407.7 112H359.8A38 31 0 0 0 328 98H308V112H262Z"/>
    </g>
    <g id="body-of-the-word" fill="{ink}">
      <path id="l-bottom" d="M70 112H116V160H176V200H70Z"/>
      <rect id="i-bottom" x="196" y="112" width="46" height="88"/>
      <path id="d-bottom" d="M262 112H308V160H328A38 31 0 0 0 359.8 112H407.7A80 71 0 0 1 330 200H262Z"/>
    </g>
    <g id="hinge">
      <circle cx="64" cy="112" r="15" fill="{pin}"/>
      <circle cx="64" cy="112" r="4.5" fill="{ink}"/>
    </g>
  </g>"""
    return svg("LID wordmark: capitals whose top is hinged open like a lid", ground, body)


# --- 04 One Line: the word written in one stroke without lifting the pen.
def oneline():
    ink, dot, ground = "#2A1BE0", "#FF4D2E", "#F4F4FF"
    path = (
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
    body = f"""  <g id="word" transform="translate(89 -14) scale(1.26)">
    <path id="lid-stroke" d="{path}" fill="none" stroke="{ink}" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/>
    <circle id="tittle" cx="117" cy="86" r="8" fill="{dot}"/>
  </g>"""
    return svg("lid wordmark: the word written in one continuous line", ground, body)


# --- 05 Transit: each letter is a rail line, and interchange stations link the lines.
def transit():
    red, blue, green, ink, station, ground = "#DC241F", "#0B2FB8", "#00843D", "#111111", "#FFFFFF", "#F4F5F0"
    body = f"""  <g id="lines" fill="none" stroke-width="26">
    <path id="l-line" d="M92 46V152A24 24 0 0 0 116 176H176" stroke="{red}"/>
    <path id="i-line" d="M232 46V176" stroke="{blue}"/>
    <path id="d-line" d="M300 46H330A65 65 0 0 1 330 176H300Z" stroke="{green}" stroke-linejoin="round"/>
  </g>
  <g id="interchange-links" fill="{ink}">
    <rect x="176" y="170" width="56" height="12"/>
    <rect x="232" y="40" width="68" height="12"/>
  </g>
  <g id="stations" fill="{station}" stroke="{ink}" stroke-width="7">
    <circle id="terminus" cx="92" cy="46" r="18"/>
    <circle id="l-to-i" cx="176" cy="176" r="18"/>
    <circle id="i-from-l" cx="232" cy="176" r="18"/>
    <circle id="i-to-d" cx="232" cy="46" r="18"/>
    <circle id="d-from-i" cx="300" cy="46" r="18"/>
    <circle id="stop" cx="395" cy="111" r="18"/>
  </g>"""
    return svg("LID wordmark: each letter a rail line, joined by interchange stations", ground, body)


# --- 06 Stitched: the capitals are pieces of cloth, and a thread sews the seams between them.
def stitched():
    cloth, thread, ground = "#EEF2FB", "#FF6A1F", "#27407A"

    def zigzag(left, right, top, bottom, step):
        y, side, d = top, 0, []
        while y <= bottom + 0.01:
            d.append(f"{'M' if not d else 'L'}{left if side == 0 else right} {y}")
            side, y = 1 - side, y + step
        return "".join(d)

    seam_id = zigzag(234, 270, 66, 192, 18)
    seam_li = zigzag(168, 204, 164, 196, 16)
    body = f"""  <g id="word" fill="{cloth}">
    <path id="l" d="M70 58H116V160H176V200H70Z"/>
    <rect id="i" x="196" y="58" width="46" height="142"/>
    <path id="d" fill-rule="evenodd" d="M262 58H330A80 71 0 0 1 330 200H262ZM308 98V160H328A38 31 0 0 0 328 98Z"/>
  </g>
  <g id="seams" fill="none" stroke="{thread}" stroke-width="6.5" stroke-linecap="round" stroke-linejoin="round">
    <path id="seam-l-i" d="{seam_li}"/>
    <path id="seam-i-d" d="{seam_id}"/>
  </g>"""
    return svg("LID wordmark: capitals sewn together along their seams", ground, body)


# --- 07 Dovetail: the letters are joined the way a woodworker joins a drawer, with no glue.
def dovetail():
    light, dark, ground = "#E2B57A", "#A85A30", "#163A2C"
    body = f"""  <g id="word" transform="translate(22 0)">
    <path id="l" d="M60 44H108V140H164V157L190 147V189L164 179V196H60Z" fill="{light}"/>
    <path id="i" d="M168 44H216V81L242 71V113L216 103V196H168V182L193 192V144L168 154Z" fill="{dark}"/>
    <path id="d" fill-rule="evenodd" fill="{light}" d="M220 44H300A76 76 0 0 1 300 196H220V106L245 116V68L220 78ZM272 88V152H296A32 32 0 0 0 296 88Z"/>
  </g>"""
    return svg("LID wordmark: capitals joined with woodworking dovetails", ground, body)


# --- 08 Arcs: reference arcs run forward over the word and back under it, so the word is walkable both ways.
def arcs():
    ink, back, ground = "#0D3B36", "#D8432B", "#BFF3DE"

    def down(x, y):
        return f"M{x - 8} {y - 12}H{x + 8}L{x} {y + 2}Z"

    def up(x, y):
        return f"M{x - 8} {y + 12}H{x + 8}L{x} {y - 2}Z"

    body = f"""  <g id="word" fill="{ink}">
    <path id="l" d="M96 78H114V144H158V162H96Z"/>
    <rect id="i" x="214" y="78" width="18" height="84"/>
    <path id="d" fill-rule="evenodd" d="M296 78H342A47 42 0 0 1 342 162H296ZM314 96V144H340A27 24 0 0 0 340 96Z"/>
  </g>
  <g id="forward" fill="none" stroke="{ink}" stroke-width="6">
    <path d="M105 66C105 18 211 18 211 58"/>
    <path d="M235 66C235 18 332 18 332 58"/>
  </g>
  <g fill="{ink}">
    <path d="{down(211, 70)}"/>
    <path d="{down(332, 70)}"/>
  </g>
  <g id="backward" fill="none" stroke="{back}" stroke-width="6">
    <path d="M332 174C332 222 235 222 235 182"/>
    <path d="M211 174C211 222 127 222 127 182"/>
  </g>
  <g fill="{back}">
    <path d="{up(235, 170)}"/>
    <path d="{up(127, 170)}"/>
  </g>"""
    return svg("LID wordmark: arcs linking the letters forward above and backward below", ground, body)


# --- 09 Hyperlink: the web's oldest picture of a link. Default blue, default underline, old serif.
def hyperlink():
    blue, ground = "#0000EE", "#FFFFFF"
    body = f"""  <g id="word" fill="{blue}" transform="translate(-28.65 -36.6) scale(1.35)">
    <path id="l" d="M100 54L126 44V152Q126 160 137 161V166H98V161Q109 160 109 152V66Q109 58 100 58Z"/>
    <path id="i" d="M154 104L180 94V152Q180 160 191 161V166H152V161Q163 160 163 152V116Q163 108 154 108Z"/>
    <circle id="tittle" cx="171" cy="70" r="11"/>
    <path id="d-bowl" fill-rule="evenodd" d="M238 94C258 94 276 110 276 131C276 152 258 168 238 168C216 168 200 152 200 131C200 110 216 94 238 94ZM243 101C229 101 220 114 220 131C220 148 229 161 243 161C257 161 268 148 268 131C268 114 257 101 243 101Z"/>
    <path id="d-stem" d="M261 54L287 44V148Q287 158 299 155L300 159L271 168V66Q271 58 261 58Z"/>
    <rect id="underline" x="92" y="179" width="214" height="6"/>
  </g>"""
    return svg("lid wordmark: the word styled as a classic blue underlined link", ground, body)


# --- 10 Five-Line Arrow: the L is five stripes that run under the rest of the word and end as an arrow.
def fivelinearrow():
    colours = ["#FFC63D", "#FF9A2E", "#F4632B", "#E0344F", "#B22A85"]  # inner to outer
    letter, ground = "#FFF1DE", "#23110F"
    cx, cy, step, sw, r0 = 98, 158, 12, 8.5, 10
    radii = [r0 + n * step for n in range(5)]
    mid = cy + radii[2]
    half = (radii[4] - radii[0]) / 2 + sw / 2
    tip = 456
    shoulder = tip - half
    clip = f"M0 0H{shoulder}V{mid - half}L{tip} {mid}L{shoulder} {mid + half}V240H0Z"
    lines = "\n".join(
        f'    <path d="M{cx - r} 24V{cy}A{r} {r} 0 0 0 {cx} {cy + r}H480" stroke="{c}"/>' for r, c in zip(radii, colours)
    )
    body = f"""  <defs><clipPath id="arrow-tip"><path d="{clip}"/></clipPath></defs>
  <g id="l-five-lines" fill="none" stroke-width="{sw}" clip-path="url(#arrow-tip)">
{lines}
  </g>
  <g id="id" fill="{letter}">
    <rect id="i" x="116" y="24" width="32" height="124"/>
    <path id="d" fill-rule="evenodd" d="M172 24H234A62 62 0 0 1 234 148H172ZM204 54V118H232A32 32 0 0 0 232 54Z"/>
  </g>"""
    return svg("LID wordmark: a five-line L runs under the word and ends as an arrow", ground, body)


# Shared heavy capitals for the arrow marks. One even-odd path means the arrow is solid
# outside the letters and cut out inside them, using a single color.
LID_CAPS = (
    "M70 58H116V160H176V200H70Z"
    "M196 58H242V200H196Z"
    "M262 58H330A80 71 0 0 1 330 200H262Z"
    "M308 98V160H328A38 31 0 0 0 328 98Z"
)


# --- 11 Cut-Through: a level arrow runs straight through all three letters.
def cut_through():
    ink, ground = "#FFFFFF", "#5A16D6"
    arrow = "M22 120H420V94L468 129L420 164V138H22Z"
    body = f"""  <path id="word-and-arrow" fill="{ink}" fill-rule="evenodd" d="{LID_CAPS}{arrow}"/>"""
    return svg("LID wordmark: a level arrow cuts straight through the letters", ground, body)


# --- 12 Spine: the I is the arrow, running straight down through the word from intent to code.
def spine():
    ink, arrow, ground = "#F2F4FF", "#FF4B33", "#10131F"
    body = f"""  <g id="word" fill="{ink}">
    <path id="l" d="M78 62H124V144H184V182H78Z"/>
    <path id="d" fill-rule="evenodd" d="M268 62H336A76 60 0 0 1 336 182H268ZM314 100V144H334A36 22 0 0 0 334 100Z"/>
  </g>
  <path id="i-arrow" d="M203 14H249V186H272L226 232L180 186H203Z" fill="{arrow}"/>"""
    return svg("LID wordmark: the I is an arrow running down through the word", ground, body)


MARKS = [
    ("01-linked-list", linked_list),
    ("02-chain", chain),
    ("03-hinged", hinged),
    ("04-one-line", oneline),
    ("05-transit", transit),
    ("06-stitched", stitched),
    ("07-dovetail", dovetail),
    ("08-arcs", arcs),
    ("09-hyperlink", hyperlink),
    ("10-five-line-arrow", fivelinearrow),
    ("11-cut-through", cut_through),
    ("12-spine", spine),
]

if __name__ == "__main__":
    OUT.mkdir(parents=True, exist_ok=True)
    for name, fn in MARKS:
        (OUT / f"{name}.svg").write_text(fn())
    print("wrote", len(MARKS), "wordmarks to", OUT)
