#!/usr/bin/env python3
"""Square favicon sketches for Nodes (slab I) and Soft Cut, on a 64-unit grid."""
import pathlib

OUT = pathlib.Path(__file__).parent.parent / "explorations" / "favicons"
OUT.mkdir(exist_ok=True)


def n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def rounded(points, r):
    out = []
    count = len(points)
    for i, (x, y) in enumerate(points):
        px, py = points[i - 1]
        qx, qy = points[(i + 1) % count]
        d1 = ((px - x) ** 2 + (py - y) ** 2) ** 0.5
        d2 = ((qx - x) ** 2 + (qy - y) ** 2) ** 0.5
        k = min(r, d1 / 2, d2 / 2)
        ax, ay = x + (px - x) * k / d1, y + (py - y) * k / d1
        bx, by = x + (qx - x) * k / d2, y + (qy - y) * k / d2
        out.append(f"{'M' if i == 0 else 'L'}{n(ax)} {n(ay)}Q{n(x)} {n(y)} {n(bx)} {n(by)}")
    return "".join(out) + "Z"


def svg(body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64">\n{body}\n</svg>\n'


TOP, BOTTOM = 12, 52  # 40-unit cap height, centered


# --- Nodes: one rounded node with a letter in it. The letter is filled, not a hole,
# so the icon looks the same on light and dark browser tabs.
def nodes_i(ink, ground):
    c, half, stem, bar = 32, 15, 6.5, 10
    t, b = TOP, BOTTOM
    i = rounded(
        [
            (c - half, t), (c + half, t), (c + half, t + bar), (c + stem, t + bar),
            (c + stem, b - bar), (c + half, b - bar), (c + half, b), (c - half, b),
            (c - half, b - bar), (c - stem, b - bar), (c - stem, t + bar), (c - half, t + bar),
        ],
        1.5,
    )
    return svg(f'  <rect width="64" height="64" rx="14" fill="{ink}"/>\n  <path d="{i}" fill="{ground}"/>')


def nodes_l(ink, ground):
    stem, bar, width = 13, 11, 29
    x = 32 - 12.33  # Halfway between the L's box center (14.5) and its center of mass (10.17).
    t, b = TOP, BOTTOM
    l = rounded([(x, t), (x + stem, t), (x + stem, b - bar), (x + width, b - bar), (x + width, b), (x, b)], 1.5)
    return svg(f'  <rect width="64" height="64" rx="14" fill="{ink}"/>\n  <path d="{l}" fill="{ground}"/>')


# --- Soft Cut: one rounded letter with the arrow running through it and out the right side.
def soft(letter_path, stroke, arrow, ink, ground):
    style = f'fill="none" stroke-width="{stroke}" stroke-linecap="round" stroke-linejoin="round"'
    arrow_style = 'fill="none" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"'
    return svg(
        f'  <defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">'
        f'<path d="{letter_path}" stroke="#FFFFFF" {style}/></mask></defs>\n'
        f'  <rect width="64" height="64" rx="14" fill="{ground}"/>\n'
        f'  <path d="{letter_path}" stroke="{ink}" {style}/>\n'
        f'  <path d="{arrow}" stroke="{ink}" {arrow_style}/>\n'
        f'  <path d="{arrow}" stroke="{ground}" {arrow_style} mask="url(#m)"/>'
    )


def soft_l(ink, ground):
    # The arrow sits a little above center so its head clears the L's foot.
    return soft("M17 18.5V45.5H40", 13, "M5 28H57M50 21.5L57 28L50 34.5", ink, ground)


def soft_d(ink, ground):
    s = 40 / 150  # The logo's D is 150 units tall; this one is 40.
    x0, y0 = 7, TOP
    sx = lambda v: n(x0 + (v - 255) * s)
    sy = lambda v: n(y0 + (v - 45) * s)
    d = f"M{sx(274)} {sy(64)}H{sx(316)}A{n(56 * s)} {n(56 * s)} 0 0 1 {sx(316)} {sy(176)}H{sx(274)}Z"
    return soft(d, n(38 * s), "M4 32H57M50 25L57 32L50 39", ink, ground)


# --- The Nodes pointer (a solid shaft and a right-angled head) run through an L.
def pointer(x0, head_base, py, shaft=7, head=22):
    tip = head_base + head / 2  # A right-angled tip, as on the Nodes pointer.
    return rounded(
        [(x0, py - shaft / 2), (head_base, py - shaft / 2), (head_base, py - head / 2), (tip, py),
         (head_base, py + head / 2), (head_base, py + shaft / 2), (x0, py + shaft / 2)],
        1.5,
    )


def cut_through(letter, letter_attrs, arrow, ink, ground):
    """The arrow is solid where it crosses the background and cut out where it crosses the letter."""
    return svg(
        f'  <defs><mask id="m" maskUnits="userSpaceOnUse" x="0" y="0" width="64" height="64">'
        f'<path d="{letter}" {letter_attrs.format(c="#FFFFFF")}/></mask></defs>\n'
        f'  <rect width="64" height="64" rx="14" fill="{ground}"/>\n'
        f'  <path d="{letter}" {letter_attrs.format(c=ink)}/>\n'
        f'  <path d="{arrow}" fill="{ink}"/>\n'
        f'  <path d="{arrow}" fill="{ground}" mask="url(#m)"/>'
    )


def pointer_round_l(ink, ground):
    # Soft Cut's round L. The pointer starts at the stem's left edge, because a stub to the
    # left of the stem would make a crossbar and the L would read as a t. The foot stops
    # short so the head sits clear to its right.
    attrs = 'fill="none" stroke="{c}" stroke-width="13" stroke-linecap="round" stroke-linejoin="round"'
    return cut_through("M15 18.5V45.5H36", attrs, pointer(8.5, 45, 28), ink, ground)


def pointer_square_l(ink, ground):
    # The Nodes L: flat edges, small rounded corners. Built from pieces that never overlap, as in
    # Flush Cut: the L is clipped above and below the pointer's band, and the pointer is drawn
    # only to the right of the L's stem, so no edge is drawn twice.
    l = rounded([(10, 12), (23, 12), (23, 41), (38, 41), (38, 52), (10, 52)], 2)
    py, shaft, head_base, head = 28, 7, 44, 22
    y1, y2 = py - shaft / 2, py + shaft / 2
    head_path = rounded([(head_base, py - head / 2), (head_base + head / 2, py), (head_base, py + head / 2)], 1.5)
    return svg(
        f'  <defs><clipPath id="fv"><rect width="64" height="{n(y1)}"/><rect y="{n(y2)}" width="64" height="{n(64 - y2)}"/></clipPath></defs>\n'
        f'  <rect width="64" height="64" rx="14" fill="{ground}"/>\n'
        f'  <path d="{l}" fill="{ink}" clip-path="url(#fv)"/>\n'
        f'  <path d="M23 {n(y1)}H{head_base + 1}V{n(y2)}H23Z" fill="{ink}"/>\n'
        f'  <path d="{head_path}" fill="{ink}"/>'
    )


def pointer_node_l(ink, ground):
    # A small node tile; the pointer crosses its L and leaves the tile to the right.
    l = rounded([(13, 20), (21, 20), (21, 39), (31, 39), (31, 45), (13, 45)], 1)
    return svg(
        f'  <rect width="64" height="64" rx="14" fill="{ground}"/>\n'
        f'  <rect x="5" y="13" width="38" height="38" rx="9" fill="{ink}"/>\n'
        f'  <path d="{l}" fill="{ground}"/>\n'
        f'  <path d="{pointer(9, 48, 31, shaft=6, head=20)}" fill="{ink}"/>'
    )


ICONS = {
    "nodes-i": nodes_i,
    "nodes-l": nodes_l,
    "soft-l": soft_l,
    "soft-d": soft_d,
    "pointer-round-l": pointer_round_l,
    "pointer-square-l": pointer_square_l,
    "pointer-node-l": pointer_node_l,
}

if __name__ == "__main__":
    nodes_a = ("#1A0F0A", "#FF6B3D")
    soft_a = ("#3A1F4D", "#FFE27A")
    for name, fn in ICONS.items():
        colors = soft_a if name.startswith("soft") or name == "pointer-round-l" else nodes_a
        (OUT / f"{name}.svg").write_text(fn(*colors))
    print("wrote", len(ICONS), "favicon sketches")
