// Candidate logos for the temporary Logo Ideas page. In each palette, `ground` is the
// tile's background, and the next color is the main one shown on the palette switch.
// @spec MKT-SITE-086, MKT-SITE-087, MKT-SITE-088, MKT-SITE-094, MKT-SITE-097, MKT-SITE-098

const main = [
  {
    slug: "nodes-plain",
    name: "Nodes, plain I",
    idea: "Each letter is a node that points to the next one, like a linked list.",
    palettes: [
      { ground: "#FFD60A", ink: "#111111" },
      { ground: "#E9EDFF", ink: "#1E2BD6" },
      { ground: "#0F1B17", ink: "#7CF2B4" },
      { ground: "#FFE4DB", ink: "#C9321B" },
      { ground: "#F1E7FF", ink: "#6D28D9" },
      { ground: "#1B1033", ink: "#FF8AD8" },
      { ground: "#FFFFFF", ink: "#111111" },
    ],
  },
  {
    slug: "nodes-slab",
    name: "Nodes, slab I",
    idea: "The same nodes, with the I drawn the way coding fonts draw it.",
    palettes: [
      { ground: "#FF6B3D", ink: "#1A0F0A" },
      { ground: "#DFF7F2", ink: "#0B7A6B" },
      { ground: "#1C1917", ink: "#FDE68A" },
      { ground: "#FCE7F3", ink: "#BE185D" },
      { ground: "#ECFCCB", ink: "#3F6212" },
      { ground: "#2E1065", ink: "#C4B5FD" },
      { ground: "#E5E7EB", ink: "#1F2937" },
    ],
  },
  {
    slug: "markdown",
    name: "Markdown",
    idea: "The word is a Markdown link whose target is intent. Small uses would shorten it to <code>[lid]</code>.",
    palettes: [
      { ground: "#241B2F", word: "#FFFFFF", punct: "#9A88C4", target: "#6FE3D2" },
      { ground: "#F4F5FB", word: "#1A1C2E", punct: "#7A7F99", target: "#2B50E8" },
      { ground: "#0C1F17", word: "#D8F7E6", punct: "#5FA582", target: "#5DF0A0" },
      { ground: "#FFF1C9", word: "#3A1F0D", punct: "#A86F12", target: "#C8400B" },
      { ground: "#FFF0F6", word: "#3B0A24", punct: "#A85C81", target: "#D6246E" },
      { ground: "#1A1A1A", word: "#F5F5F5", punct: "#8A8A8A", target: "#FFD60A" },
      { ground: "#002B36", word: "#EEE8D5", punct: "#839496", target: "#2AA198" },
    ],
  },
  {
    slug: "wiki-link",
    name: "Wiki Link",
    idea: "The word sits in the double brackets that wikis and note-taking apps use for a link.",
    palettes: [
      { ground: "#F1ECFF", word: "#23104F", bracket: "#7C4DFF" },
      { ground: "#16161D", word: "#F5F5F7", bracket: "#9A9AAE" },
      { ground: "#DDF6F1", word: "#07332D", bracket: "#0B8577" },
      { ground: "#2B0B2E", word: "#FFF0F7", bracket: "#FF5CAA" },
      { ground: "#FFF4DB", word: "#3A2A05", bracket: "#B0711A" },
      { ground: "#0F2A1F", word: "#E8FFF3", bracket: "#34D399" },
      { ground: "#FFFFFF", word: "#111111", bracket: "#2563EB" },
    ],
  },
];

const more = [
  {
    slug: "pointer-tails",
    name: "Pointer Tails",
    idea: "In coding fonts, l and i often have small tails. Here each tail points to the next letter.",
    palettes: [
      { ground: "#BDE7FF", ink: "#0E2A47", accent: "#E8451F" },
      { ground: "#F2F2EC", ink: "#1C1C1C", accent: "#D6006F" },
      { ground: "#12122A", ink: "#F2F2FF", accent: "#FFC53D" },
    ],
  },
  {
    slug: "link-dot",
    name: "Link Dot",
    idea: "The dot on the i is the chain-link icon that editors use for a link.",
    palettes: [
      { ground: "#EEF3FF", ink: "#14122B", accent: "#1F5FFF" },
      { ground: "#141414", ink: "#F6F6F6", accent: "#4CC9F0" },
      { ground: "#FFF0D9", ink: "#2B1A0E", accent: "#D94E08" },
    ],
  },
  {
    slug: "deref",
    name: "Deref",
    idea: "<code>l-&gt;i-&gt;d</code> is real C code. It follows a pointer from l to i, and another from i to d.",
    palettes: [
      { ground: "#E9F8EC", word: "#15301F", arrow: "#0E8A43" },
      { ground: "#0F1720", word: "#E6EDF3", arrow: "#58A6FF" },
      { ground: "#FFEAF2", word: "#3A0B24", arrow: "#CF1F63" },
    ],
  },
  {
    slug: "snake",
    name: "Snake",
    idea: "The old phone game spells the word in one unbroken path, and the food is the dot on the i.",
    palettes: [
      { ground: "#C7F0D8", body: "#2F3D2B" },
      { ground: "#9BBC0F", body: "#0F380F" },
      { ground: "#1A1200", body: "#FFB000" },
    ],
  },
  {
    slug: "soft-cut",
    name: "Soft Cut",
    idea: "One arrow runs through all three letters and links them.",
    palettes: [
      { ground: "#FFE27A", ink: "#3A1F4D" },
      { ground: "#E8F0FF", ink: "#1437E0" },
      { ground: "#1C1330", ink: "#FFD9F0" },
    ],
  },
  {
    slug: "git-graph",
    name: "Git Graph",
    idea: "The letters grow from one main branch, like a commit graph.",
    palettes: [
      { ground: "#F6F7FB", main: "#3B4252", l: "#2F6BFF", i: "#D62D73", d: "#0B8A5F", node: "#FFFFFF" },
      { ground: "#0D1117", main: "#8B949E", l: "#58A6FF", i: "#F778BA", d: "#3FB950", node: "#0D1117" },
      { ground: "#FFF6E6", main: "#5C4033", l: "#C8400B", i: "#A3128F", d: "#237A37", node: "#FFF6E6" },
    ],
  },
];

const LETTERS = "abcdefgh";

function decorate(logo) {
  return {
    ...logo,
    palettes: logo.palettes.map((colors, index) => {
      const [ground, primary] = Object.values(colors);
      const letter = LETTERS[index];
      return {
        letter,
        upper: letter.toUpperCase(),
        chip: `linear-gradient(90deg, ${ground} 50%, ${primary} 50%)`,
        colors,
      };
    }),
  };
}

function declarations(colors) {
  return Object.entries(colors)
    .map(([role, value]) => `--logo-${role}:${value}`)
    .join(";");
}

// Palette A is the plain rule, so a browser without :has() still draws every logo correctly.
// @spec MKT-SITE-089, MKT-SITE-094
function paletteCss(logo) {
  return logo.palettes
    .map(({ letter, colors }, index) =>
      index === 0
        ? `#logo-${logo.slug}{${declarations(colors)}}`
        : `#logo-${logo.slug}:has(input[value="${letter}"]:checked){${declarations(colors)}}`
    )
    .join("\n");
}

const decoratedMain = main.map(decorate);
const decoratedMore = more.map(decorate);

export default {
  main: decoratedMain,
  more: decoratedMore,
  css: [...decoratedMain, ...decoratedMore].map(paletteCss).join("\n"),
};
