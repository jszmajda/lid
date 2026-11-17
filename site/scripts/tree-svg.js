// Draws a showcase project's intent tree as an inline SVG, and names a project's size.
// The tree is the tree file's shape: { children: [ { name?, children? | specs?, built? } ] }.
// @spec ONB-SHOWCASE-034

const DOT_ROWS = 16; // the tallest column's limit, in rows of dots
const PER_ROW = 3; // dots per row under a leaf
const MIN_LEAF = 12; // the narrowest a leaf's slot may get before the drawing scrolls
const WIDTH = 760;
const PAD = 24;

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const plural = (n, word) => `${n.toLocaleString("en-US")} ${word}${n === 1 ? "" : "s"}`;

// @spec ONB-SHOWCASE-049
export function sizeName(total) {
  if (total < 100) return "Small";
  if (total < 500) return "Medium";
  if (total < 1000) return "Large";
  return "Very large";
}

// The smallest of 1, 2, 5, 10, 20, 50, 100, … that keeps the tallest column within DOT_ROWS rows.
// @spec ONB-SHOWCASE-036
export function specsPerDot(maxSpecs, perRow = PER_ROW) {
  for (let scale = 1; ; scale *= 10) {
    for (const step of [1, 2, 5]) {
      const perDot = step * scale;
      if (Math.ceil(Math.ceil(maxSpecs / perDot) / perRow) <= DOT_ROWS) return perDot;
    }
  }
}

const isLeaf = (n) => !n.children;
const hasCounts = (n) => n.specs !== undefined;
const leavesOf = (n) => (isLeaf(n) ? [n] : n.children.flatMap(leavesOf));

// @spec ONB-SHOWCASE-035, ONB-SHOWCASE-037, ONB-SHOWCASE-038, ONB-SHOWCASE-039, ONB-SHOWCASE-040,
//       ONB-SHOWCASE-041, ONB-SHOWCASE-042, ONB-SHOWCASE-045, ONB-SHOWCASE-048, ONB-SHOWCASE-091
export function drawTree(tree) {
  const root = { children: tree.children };
  const leaves = leavesOf(root);
  const counted = leaves.every(hasCounts);
  const total = counted ? leaves.reduce((a, l) => a + l.specs, 0) : null;
  const open = counted ? leaves.reduce((a, l) => a + l.specs - l.built, 0) : null;
  const perDot = counted ? specsPerDot(Math.max(1, ...leaves.map((l) => l.specs))) : 1;

  let depth = 0;
  const place = (n, d) => {
    n._d = d;
    depth = Math.max(depth, d);
    if (n.children) n.children.forEach((c) => place(c, d + 1));
  };
  place(root, 0);

  const colW = Math.max(MIN_LEAF, (WIDTH - PAD * 2) / leaves.length);
  const width = Math.max(WIDTH, PAD * 2 + colW * leaves.length);
  const scrolls = width > WIDTH;
  leaves.forEach((l, i) => (l._x = PAD + colW * (i + 0.5)));
  const centre = (n) => {
    if (n.children) {
      n.children.forEach(centre);
      n._x = (n.children[0]._x + n.children[n.children.length - 1]._x) / 2;
    }
  };
  centre(root);

  const top = 16, levelH = 64, nodeH = 18;
  const leafW = Math.max(6, Math.min(54, colW * 0.62));
  const step = Math.max(3, Math.min(11, (colW * 0.8) / PER_ROW));
  const dotR = step * 0.37;
  const y = (n) => top + n._d * levelH;
  let deepest = top + 30;
  let edges = "";
  let nodes = "";

  const draw = (n) => {
    const root_ = n._d === 0;
    const leaf = isLeaf(n) && !root_;
    const span = n.children ? n.children[n.children.length - 1]._x - n.children[0]._x : 0;
    const nw = root_ ? 96 : leaf ? leafW : Math.min(64, span + leafW);
    const nh = root_ ? 30 : nodeH;
    for (const c of n.children || []) {
      const y0 = y(n) + nh, y1 = y(c), ym = (y0 + y1) / 2;
      edges += `<path class="t-edge" d="M${n._x.toFixed(1)} ${y0} C ${n._x.toFixed(1)} ${ym}, ${c._x.toFixed(1)} ${ym}, ${c._x.toFixed(1)} ${y1}"/>`;
      draw(c);
    }
    let body = `<rect class="${root_ ? "t-hld" : leaf ? "t-lld" : "t-sub"}" x="${(n._x - nw / 2).toFixed(1)}" y="${y(n)}" width="${nw.toFixed(1)}" height="${nh}" rx="${root_ ? 9 : 6}"/>`;
    if (root_) body += `<text class="t-label" x="${n._x.toFixed(1)}" y="${y(n) + 20}" text-anchor="middle">HLD</text>`;
    let bottom = y(n) + nh;
    if (leaf && counted) {
      const dots = Math.ceil(n.specs / perDot);
      const openSpecs = n.specs - n.built;
      const hollow = openSpecs > 0 ? Math.min(dots, Math.max(1, Math.floor(openSpecs / perDot + 0.5))) : 0;
      for (let d = 0; d < dots; d++) {
        const row = Math.floor(d / PER_ROW), k = d % PER_ROW;
        const inRow = Math.min(PER_ROW, dots - row * PER_ROW);
        const cx = n._x - ((inRow - 1) * step) / 2 + k * step;
        const cy = y(n) + nodeH + 10 + row * step;
        bottom = Math.max(bottom, cy + dotR);
        body += `<circle class="${d < dots - hollow ? "t-dot" : "t-gap"}" cx="${cx.toFixed(1)}" cy="${cy.toFixed(1)}" r="${dotR.toFixed(2)}"/>`;
      }
    }
    deepest = Math.max(deepest, bottom);
    const cls = root_ ? "t-root" : leaf ? "t-leaf" : "t-subnode";
    if (!root_ && n.name) {
      const note = !leaf
        ? `sub-HLD, ${plural(leavesOf(n).length, "design doc")} below`
        : !hasCounts(n)
          ? "design doc"
          : n.built === n.specs
            ? `${plural(n.specs, "spec")}, all built`
            : `${plural(n.specs, "spec")}, ${n.built.toLocaleString("en-US")} built`;
      nodes += `<g class="${cls} t-node" tabindex="0" data-name="${esc(n.name)}" data-note="${esc(note)}"><title>${esc(n.name)}: ${esc(note)}</title>${body}</g>`;
    } else {
      nodes += `<g class="${cls}">${body}</g>`;
    }
  };
  draw(root);

  const height = Math.ceil(deepest + 14);
  const docs = leaves.length;
  const label = `Intent tree: ${plural(docs, "design doc")}, ${plural(depth, "level")} deep${counted ? `, ${plural(total, "spec")}` : ""}`;
  const named = leaves.some((l) => l.name) || nodesNamed(root);
  const svg = `<svg class="tree-svg${scrolls ? " t-wide" : ""}" viewBox="0 0 ${width} ${height}"${scrolls ? ` style="min-width:${width}px"` : ""} role="img" aria-label="${esc(label)}">${edges}${nodes}</svg>`;
  return { svg, perDot, total, open, docs, depth, counted, named, scrolls };
}

function nodesNamed(n) {
  return (n.children || []).some((c) => c.name || nodesNamed(c));
}
