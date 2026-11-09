#!/usr/bin/env python3
"""Flush Cut: the Nodes letters without their tiles, with the Nodes pointer cut through them.

Built from pieces that never overlap, so no edge is drawn twice:
  - each letter is clipped to the area above and below the pointer's band;
  - the pointer is drawn only where it crosses empty space, with its ends following the
    letters' edges (straight for L, I and the D's stem, curved inside and outside the D's bowl).
The pointer starts flush with the L's left edge and sits 40% of the way down the letters.
With no background-colored layer, the mark works on any background once the ground is removed.
"""
import math
import pathlib


def n(v):
    return f"{v:.2f}".rstrip("0").rstrip(".")


def rounded(points, radii):
    if not isinstance(radii, (list, tuple)):
        radii = [radii] * len(points)
    out = []
    count = len(points)
    for i, (x, y) in enumerate(points):
        px, py = points[i - 1]
        qx, qy = points[(i + 1) % count]
        r = radii[i]
        if r == 0:
            out.append(f"{'M' if i == 0 else 'L'}{n(x)} {n(y)}")
            continue
        d1 = ((px - x) ** 2 + (py - y) ** 2) ** 0.5
        d2 = ((qx - x) ** 2 + (qy - y) ** 2) ** 0.5
        k = min(r, d1 / 2, d2 / 2)
        ax, ay = x + (px - x) * k / d1, y + (py - y) * k / d1
        bx, by = x + (qx - x) * k / d2, y + (qy - y) * k / d2
        out.append(f"{'M' if i == 0 else 'L'}{n(ax)} {n(ay)}Q{n(x)} {n(y)} {n(bx)} {n(by)}")
    return "".join(out) + "Z"


def flush_cut(ink, ground, gap=18, tail=0.2, cap=112, width=480, height=240, uid="fc"):
    """`gap` is the space between letters in Nodes units (cap height 70); `tail` is the shaft
    between the D and the arrowhead, as a fraction of the cap height."""
    k = cap / 70
    stem, bar, r = 21 * k, 18 * k, 3 * k
    head = 0.56 * cap
    shaft = 0.175 * cap

    # Horizontal layout, then center the whole drawing from the L's left edge to the arrow's tip.
    x_i = 47 * k + gap * k
    x_d = x_i + 48 * k + gap * k
    head_base = x_d + 60 * k + tail * cap
    total = head_base + head / 2
    x0 = (width - total) / 2
    top = (height - cap) / 2
    b = top + cap
    x_i, x_d, head_base = x0 + x_i, x0 + x_d, x0 + head_base

    # Letters.
    l = rounded([(x0, top), (x0 + stem, top), (x0 + stem, b - bar), (x0 + 47 * k, b - bar), (x0 + 47 * k, b), (x0, b)], r)
    c, half, hs = x_i + 24 * k, 24 * k, stem / 2
    i = rounded(
        [(c - half, top), (c + half, top), (c + half, top + bar), (c + hs, top + bar),
         (c + hs, b - bar), (c + half, b - bar), (c + half, b), (c - half, b),
         (c - half, b - bar), (c - hs, b - bar), (c - hs, top + bar), (c - half, top + bar)],
        r,
    )
    cx, cy = x_d + 26 * k, top + cap / 2
    rx, ry = 34 * k, cap / 2
    irx, iry = 12 * k, (cap - 2 * bar) / 2
    it, ib, ir = top + bar, b - bar, 2 * k
    d = (
        f"M{n(x_d + r)} {n(top)}H{n(cx)}A{n(rx)} {n(ry)} 0 0 1 {n(cx)} {n(b)}H{n(x_d + r)}"
        f"Q{n(x_d)} {n(b)} {n(x_d)} {n(b - r)}V{n(top + r)}Q{n(x_d)} {n(top)} {n(x_d + r)} {n(top)}Z"
        f"M{n(x_d + stem + ir)} {n(it)}H{n(cx)}A{n(irx)} {n(iry)} 0 0 1 {n(cx)} {n(ib)}H{n(x_d + stem + ir)}"
        f"Q{n(x_d + stem)} {n(ib)} {n(x_d + stem)} {n(ib - ir)}V{n(it + ir)}Q{n(x_d + stem)} {n(it)} {n(x_d + stem + ir)} {n(it)}Z"
    )

    # The pointer's band.
    py = top + 0.4 * cap
    y1, y2 = py - shaft / 2, py + shaft / 2
    out_x = lambda y: cx + rx * math.sqrt(1 - ((y - cy) / ry) ** 2)
    in_x = lambda y: cx + irx * math.sqrt(1 - ((y - cy) / iry) ** 2)

    segments = [
        # L's stem to I's stem.
        f"M{n(x0 + stem)} {n(y1)}H{n(c - hs)}V{n(y2)}H{n(x0 + stem)}Z",
        # I's stem to D's stem.
        f"M{n(c + hs)} {n(y1)}H{n(x_d)}V{n(y2)}H{n(c + hs)}Z",
        # Inside the D: from its stem to the inner curve of the bowl.
        f"M{n(x_d + stem)} {n(y1)}H{n(in_x(y1))}A{n(irx)} {n(iry)} 0 0 1 {n(in_x(y2))} {n(y2)}H{n(x_d + stem)}Z",
        # Out of the D: from the outer curve of the bowl into the arrowhead.
        f"M{n(out_x(y1))} {n(y1)}H{n(head_base + 1)}V{n(y2)}H{n(out_x(y2))}A{n(rx)} {n(ry)} 0 0 0 {n(out_x(y1))} {n(y1)}Z",
    ]
    arrowhead = rounded([(head_base, py - head / 2), (head_base + head / 2, py), (head_base, py + head / 2)], [2 * k, 2 * k, 2 * k])

    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}">\n'
        f'  <defs><clipPath id="{uid}-letters"><rect x="0" y="0" width="{width}" height="{n(y1)}"/>'
        f'<rect x="0" y="{n(y2)}" width="{width}" height="{n(height - y2)}"/></clipPath></defs>\n'
        f'  <rect id="ground" width="{width}" height="{height}" fill="{ground}"/>\n'
        f'  <path fill="{ink}" fill-rule="evenodd" clip-path="url(#{uid}-letters)" d="{l}{i}{d}"/>\n'
        f'  <path fill="{ink}" d="{"".join(segments)}"/>\n'
        f'  <path fill="{ink}" d="{arrowhead}"/>\n'
        f"</svg>\n"
    )


if __name__ == "__main__":
    # Writes the spacing and arrow-length grid explored for Flush Cut, in Nodes palette A.
    out = pathlib.Path(__file__).parent.parent / "explorations" / "flush-cut"
    out.mkdir(parents=True, exist_ok=True)
    for gap in (18, 10, 5):
        for tail in (0.2, 0.45, 0.7):
            name = f"spacing-{gap}-arrow-{int(tail * 100)}"
            (out / f"{name}.svg").write_text(flush_cut("#1A0F0A", "#FF6B3D", gap, tail, uid=name))
    print("wrote 9 Flush Cut variants to", out)
