# LID brand files

Source files for LID's logo. Eleventy builds only `site/src/`, so nothing in this folder is published to the site.

## The logo

- **`logo/lid-wordmark.svg`** is the Nodes wordmark. The letters L, I, and D sit in rounded tiles, and each tile points to the next one, like a linked list. The I is a slab I, with the top and bottom bars it has in most coding fonts. The letters are holes in the tiles, so deleting the rect with the id `ground` makes the wordmark transparent.
- **`logo/lid-icon.svg`** is the square icon, for favicons, stickers, and other small or square uses. It's the Nodes L with the solid Nodes pointer cut through it. The pointer starts flush with the L's left edge and sits 40% of the way down the letter. The icon keeps its rounded square, because the dark letter and pointer would disappear on a dark browser tab without it.

Both files use palette A. Palette A is the logo's palette; the site's own colors are chosen separately.

| Palette | Background | Letters and pointers |
|---|---|---|
| A | `#FF6B3D` | `#1A0F0A` |
| B | `#DFF7F2` | `#0B7A6B` |
| C | `#1C1917` | `#FDE68A` |
| D | `#FCE7F3` | `#BE185D` |
| E | `#ECFCCB` | `#3F6212` |
| F | `#2E1065` | `#C4B5FD` |
| G | `#E5E7EB` | `#1F2937` |

## How the shapes are drawn

- Every mark is drawn from shapes and strokes, with no font, so no font license applies.
- The three Nodes letters share one height, one top line, and one bottom line. Each letter sits halfway between where its outer edges would center it and where its weight would center it, because an L centered by its weight alone looks pushed to the right.
- A pointer that cuts through a letter is built from pieces that never overlap. The letter is clipped above and below the pointer, and the pointer is drawn only where it crosses empty space. Drawing the pointer in ink and laying a background-colored copy over it leaves a thin line in some browsers.
- A bar through a lowercase l, or a pointer that sticks out to the left of an L's stem, makes the letter read as a t.

## Explorations

Sketches from the search for the logo, kept for reference and for uses like stickers.

The rounds ran in this order.

- **`explorations/abstract-marks/`** has the first round: ten square marks, each drawn from one idea in LID. They are Dome (a pot lid built from the letters), Jar (a canning-jar lid stamped with the full name), Eyelid (inspection), Slot (L and D with the I as the gap), Interlock (an L threaded through a D), One Line, Interchange (five lines bending into an L-shaped arrow), Through-Line (a thread sewn through five layers), Latent (many lines narrowing into one), and Root Path (a pixel design tree).
- **`explorations/first-wordmarks/`** has the first round of wordmarks, which put the word first: Lifted, Tittle, Underrun, Nest, One Line, Five Lines, Ramp, Scribe, Bitmap, and Vinculum.
- **`explorations/linking-wordmarks/`** has the round that made linking the main idea: Linked List, Chain, Hinged, One Line, Transit, Stitched, Dovetail, Arcs, Hyperlink, Five-Line Arrow, Cut-Through, and Spine.
- **`explorations/round-3-wordmarks/`** has the third round of wordmarks, each starting from something developers already know: Nodes (its first draft), Pointer Tails, Snake, Markdown (with its short form, `[lid]`), Wiki Link, Link Dot, Trace, Soft Cut, Deref, and Git Graph.
- **`explorations/nodes/`** has Nodes with a plain I and with a slab I. The `guides-` files show the first draft and the two corrected versions, with pink lines at each tile's center and at the top and bottom of the letters.
- **`explorations/favicons/`** has square icon sketches. `pointer-square-l.svg` is the chosen icon. `pointer-round-l.svg` puts the pointer through Soft Cut's round L, and `pointer-node-l.svg` puts it through an L inside a small Nodes tile. The other four are plain letter icons for Nodes and Soft Cut.
- **`explorations/flush-cut/`** has Flush Cut, a full wordmark in the chosen icon's style: the Nodes letters without tiles, with the pointer cut through all three and its head past the D. The files vary the letter spacing (18, 10, and 5) and the length of the arrow past the D (20%, 45%, and 70% of the letter height). `spacing-10-arrow-45.svg` was the most balanced.

## Scripts

Each script needs Python 3 and writes its SVG files into the matching folder in `explorations/`.

- **`scripts/abstract_marks.py`** redraws `abstract-marks/`.
- **`scripts/first_wordmarks.py`** redraws `first-wordmarks/`.
- **`scripts/linking_wordmarks.py`** redraws `linking-wordmarks/`.
- **`scripts/favicons.py`** redraws `favicons/`. Its `pointer_square_l()` function draws the chosen icon in any colors.
- **`scripts/flush_cut.py`** redraws `flush-cut/`. Its `flush_cut()` function draws Flush Cut at any spacing, arrow length, and colors.

```
python3 site/brand/scripts/abstract_marks.py
```

The third round, the Nodes drawings, and the two logo files are kept as SVG files only.
