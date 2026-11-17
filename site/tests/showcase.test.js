// Checks the examples showcase: entry validation, the tree drawing, and the built pages.
// Run from the repository root:
//   node --test site/tests/showcase.test.js
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, readdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { after, before, describe, it } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { loadEntries, parseTreeYaml } from "../scripts/entries.js";
import { drawTree, sizeName, specsPerDot } from "../scripts/tree-svg.js";

const siteDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoDir = join(siteDir, "..");
const PNG = Buffer.from("89504e470d0a1a0a0000000d4948445200000001000000010806000000" + "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082", "hex");
const roots = [];
after(() => roots.forEach((r) => rmSync(r, { recursive: true, force: true })));

// Writes one entry folder into a fresh examples directory and returns that directory.
function examplesWith(entries) {
  const root = mkdtempSync(join(tmpdir(), "showcase-"));
  roots.push(root);
  for (const [slug, files] of Object.entries(entries)) {
    mkdirSync(join(root, slug), { recursive: true });
    for (const [name, content] of Object.entries(files)) writeFileSync(join(root, slug, name), content);
  }
  return root;
}
const front = (fields, body = "A brief.") => `---\n${fields}\n---\n${body}\n`;
const BASE = 'project: Demo\nowner: Sam\ntagline: A demo.\ndate: 2026-01-02\nopen_source: true\npictures:\n  - file: shot.png\n    alt: "A screenshot"';
const valid = (extra = "", files = {}) => ({ "index.md": front(BASE + (extra ? "\n" + extra : "")), "shot.png": PNG, ...files });
const fails = (entries, pattern) => assert.throws(() => loadEntries(examplesWith(entries)), (e) => pattern.test(e.message), `expected ${pattern}`);

describe("entries", () => {
  // @spec ONB-SHOWCASE-052, ONB-SHOWCASE-066
  it("treats each folder not starting with _ or . as one entry", () => {
    const list = loadEntries(examplesWith({ demo: valid(), _template: { "index.md": "---\nanything: goes\n---\n" }, ".draft": { "index.md": "x" } }));
    assert.deepEqual(list.map((e) => e.slug), ["demo"]);
  });

  // @spec ONB-SHOWCASE-053, ONB-SHOWCASE-054
  it("fails on a folder name that is not lowercase letters, digits, and hyphens, naming the entry", () => {
    fails({ "My_Demo": valid() }, /My_Demo/);
  });

  // @spec ONB-SHOWCASE-055
  it("fails on a missing required field or a non-ISO date", () => {
    fails({ demo: { "index.md": front(BASE.replace("tagline: A demo.\n", "")), "shot.png": PNG } }, /demo.*tagline/);
    fails({ demo: { "index.md": front(BASE.replace("2026-01-02", "Jan 2 2026")), "shot.png": PNG } }, /demo.*date/);
    fails({ demo: { "index.md": front(BASE.replace("open_source: true", "open_source: maybe")), "shot.png": PNG } }, /demo.*open_source/);
  });

  // @spec ONB-SHOWCASE-056
  it("fails on an unknown field", () => {
    fails({ demo: valid("taglne: typo") }, /demo.*taglne/);
  });

  // @spec ONB-SHOWCASE-057
  it("fails on an entry with neither a picture nor a tree file", () => {
    fails({ demo: { "index.md": front(BASE.split("\npictures:")[0]) } }, /demo.*picture/);
  });

  // @spec ONB-SHOWCASE-058
  it("fails on a missing picture, a wrong type, empty alt text, or a picture over 2,000,000 bytes", () => {
    fails({ demo: { "index.md": front(BASE) } }, /demo.*shot\.png/);
    fails({ demo: { "index.md": front(BASE.replace("shot.png", "shot.gif")), "shot.gif": PNG } }, /demo.*shot\.gif/);
    fails({ demo: { "index.md": front(BASE.replace('alt: "A screenshot"', 'alt: ""')), "shot.png": PNG } }, /demo.*alt/);
    fails({ demo: { "index.md": front(BASE), "shot.png": Buffer.alloc(2_000_001) } }, /demo.*2,000,000/);
    assert.equal(loadEntries(examplesWith({ demo: { "index.md": front(BASE.replace("shot.png", "Shot.JPG")), "Shot.JPG": PNG } })).length, 1);
  });

  // @spec ONB-SHOWCASE-059
  it("fails on stats that are not pairs of strings", () => {
    fails({ demo: valid("stats:\n  - [Specs, 365]") }, /demo.*stats/);
  });

  // @spec ONB-SHOWCASE-060, ONB-SHOWCASE-061
  it("fails on unknown or non-https links, and on private entries linking their code", () => {
    fails({ demo: valid("links:\n  docs: https://example.com") }, /demo.*docs/);
    fails({ demo: valid("links:\n  repo: http://example.com") }, /demo.*repo/);
    fails({ demo: { "index.md": front(BASE.replace("open_source: true", "open_source: false") + "\nlinks:\n  hld: https://example.com/hld"), "shot.png": PNG } }, /demo.*hld/);
    assert.equal(loadEntries(examplesWith({ demo: { "index.md": front(BASE.replace("open_source: true", "open_source: false") + "\nlinks:\n  live: https://example.com"), "shot.png": PNG } })).length, 1);
  });

  // @spec ONB-SHOWCASE-062, ONB-SHOWCASE-063, ONB-SHOWCASE-064, ONB-SHOWCASE-065, ONB-SHOWCASE-090
  it("enforces the story rules", () => {
    fails({ demo: valid("story:\n  title: T\n  file: story.md\n  url: https://example.com") }, /demo.*story/);
    fails({ demo: valid("story:\n  title: T\n  file: notes.md", { "notes.md": "x" }) }, /demo.*story/);
    fails({ demo: valid("story:\n  title: T\n  file: story.md") }, /demo.*story\.md/);
    fails({ demo: valid("story:\n  title: T\n  url: https://example.com\n  editor: X") }, /demo.*editor/);
    fails({ demo: valid("story:\n  title: T\n  url: https://example.com", { "story.md": "x" }) }, /demo.*story\.md/);
    fails({ demo: valid("story:\n  title: T\n  file: story.md", { "story.md": "---\ntitle: X\n---\nBody" }) }, /demo.*front matter/);
    fails({ demo: valid("story:\n  title: T\n  file: story.html", { "story.html": "<html><p>No body</p></html>" }) }, /demo.*body/);
    fails({ demo: valid("story:\n  title: T\n  file: story.html", { "story.html": "<html><body><script>track()</script></body></html>" }) }, /demo.*script/);
    fails({ demo: valid("story:\n  title: T\n  file: story.html", { "story.html": '<html><body><img src="https://tracker.example/p.gif"></body></html>' }) }, /demo.*tracker\.example/);
    const ok = loadEntries(examplesWith({ demo: valid("story:\n  title: T\n  author: Claude\n  byline: Written by Claude\n  file: story.html", { "story.html": '<html><body><a href="https://example.com">a link</a><img src="pic.png"></body></html>' }) }));
    assert.equal(ok[0].story.byline, "Written by Claude");
  });

  // @spec ONB-SHOWCASE-067, ONB-SHOWCASE-068, ONB-SHOWCASE-069, ONB-SHOWCASE-053
  it("enforces the tree-file rules, failing the build with the entry's name", () => {
    const withTree = (yaml) => ({ demo: { ...valid(), "tree.yaml": yaml } });
    fails(withTree("children: []\n"), /demo.*tree/);
    fails(withTree("children:\n  - name: a\n    children: []\n"), /demo.*tree/);
    fails(withTree("children:\n  - name: a\n    specs: 2\n    built: 1\n    children:\n      - specs: 1\n        built: 1\n"), /demo.*tree/);
    fails(withTree("children:\n  - specs: 3\n"), /demo.*tree/);
    fails(withTree("children:\n  - specs: 3\n    built: 4\n"), /demo.*tree/);
    fails(withTree("children:\n  - specs: 2.5\n    built: 1\n"), /demo.*tree/);
    assert.equal(loadEntries(examplesWith(withTree("children:\n  - name: a\n  - specs: 2\n    built: 1\n"))).length, 1);
  });

  // @spec ONB-SHOWCASE-003
  it("orders entries newest first, breaking ties by slug", () => {
    const at = (date) => ({ "index.md": front(BASE.replace("2026-01-02", date)), "shot.png": PNG });
    const list = loadEntries(examplesWith({ beta: at("2026-03-01"), alpha: at("2026-03-01"), older: at("2025-12-31"), newest: at("2027-01-01") }));
    assert.deepEqual(list.map((e) => e.slug), ["newest", "alpha", "beta", "older"]);
  });

  // @spec ONB-SHOWCASE-013, ONB-SHOWCASE-014, ONB-SHOWCASE-015
  it("derives credit lines and bylines", () => {
    const list = loadEntries(examplesWith({
      own: valid("story:\n  title: T\n  url: https://example.com/post"),
      other: valid("story:\n  title: T\n  author: Claude\n  url: https://example.com/post"),
      custom: valid("story:\n  title: T\n  author: Claude\n  byline: Written by Claude, for Sam\n  url: https://example.com/post"),
    }));
    const by = Object.fromEntries(list.map((e) => [e.slug, e]));
    assert.equal(by.own.credit, "Sam's project");
    assert.equal(by.own.story.byline, "by Sam");
    assert.equal(by.other.credit, "Sam's project · post written by Claude");
    assert.equal(by.other.story.byline, "by Claude");
    assert.equal(by.custom.story.byline, "Written by Claude, for Sam");
  });
});

describe("size names", () => {
  // @spec ONB-SHOWCASE-049
  it("names sizes by spec count", () => {
    assert.equal(sizeName(0), "Small");
    assert.equal(sizeName(99), "Small");
    assert.equal(sizeName(100), "Medium");
    assert.equal(sizeName(499), "Medium");
    assert.equal(sizeName(500), "Large");
    assert.equal(sizeName(999), "Large");
    assert.equal(sizeName(1000), "Very large");
  });

  // @spec ONB-SHOWCASE-050, ONB-SHOWCASE-051
  it("takes the total from a fully counted tree, else from spec_count, else shows none", () => {
    const tree = "children:\n  - specs: 600\n    built: 600\n";
    const partial = "children:\n  - specs: 600\n    built: 600\n  - name: unknown\n";
    const list = loadEntries(examplesWith({
      counted: { ...valid("spec_count: 50"), "tree.yaml": tree },
      partial: { ...valid("spec_count: 1200"), "tree.yaml": partial },
      none: valid(),
    }));
    const by = Object.fromEntries(list.map((e) => [e.slug, e]));
    assert.equal(by.counted.size, "Large");
    assert.equal(by.partial.size, "Very large");
    assert.equal(by.none.size, null);
  });
});

describe("the tree drawing", () => {
  const tree = (yaml) => parseTreeYaml(yaml);
  const leafDots = (svg) => [...svg.matchAll(/<g class="t-leaf[^"]*"[\s\S]*?<\/g>/g)].map((g) => ({ filled: (g[0].match(/class="t-dot"/g) || []).length, hollow: (g[0].match(/class="t-gap"/g) || []).length }));

  // @spec ONB-SHOWCASE-036
  it("picks the smallest of 1, 2, 5, 10, 20, 50, 100… that keeps the tallest column within 16 rows", () => {
    // Columns hold 3 dots per row at the default width, so 48 dots fit in 16 rows.
    assert.equal(specsPerDot(48, 3), 1);
    assert.equal(specsPerDot(49, 3), 2);
    assert.equal(specsPerDot(96, 3), 2);
    assert.equal(specsPerDot(97, 3), 5);
    assert.equal(specsPerDot(4801, 3), 200);
  });

  // @spec ONB-SHOWCASE-034, ONB-SHOWCASE-035, ONB-SHOWCASE-037, ONB-SHOWCASE-038
  it("draws nodes and hangs specs as dots, rounding as specified", () => {
    const d = drawTree(tree("children:\n  - name: a\n    specs: 5\n    built: 0\n  - name: b\n    children:\n      - name: c\n        specs: 4\n        built: 3\n"));
    assert.match(d.svg, /^<svg[^>]*>/);
    assert.match(d.svg, /class="t-hld"/);
    assert.match(d.svg, /class="t-sub"/);
    assert.equal((d.svg.match(/class="t-lld"/g) || []).length, 2);
    assert.deepEqual(leafDots(d.svg), [{ filled: 0, hollow: 5 }, { filled: 3, hollow: 1 }]);
    const halves = drawTree(tree("children:\n  - specs: 99\n    built: 94\n  - specs: 2\n    built: 2\n"));
    // 99 specs need 5 per dot in 3-wide columns: 20 dots; 5 open specs / 5 = 1 hollow.
    assert.equal(halves.perDot, 5);
    assert.deepEqual(leafDots(halves.svg)[0], { filled: 19, hollow: 1 });
    const rounding = drawTree(tree("children:\n  - specs: 60\n    built: 55\n"));
    // 60 specs at 2 per dot: 30 dots; 5 open / 2 = 2.5, rounded up to 3 hollow.
    assert.equal(rounding.perDot, 2);
    assert.deepEqual(leafDots(rounding.svg)[0], { filled: 27, hollow: 3 });
    const oneOpen = drawTree(tree("children:\n  - specs: 100\n    built: 99\n"));
    assert.equal(leafDots(oneOpen.svg)[0].hollow, 1);
  });

  // @spec ONB-SHOWCASE-039
  it("shows no dots when any leaf lacks counts", () => {
    const d = drawTree(tree("children:\n  - name: a\n    specs: 5\n    built: 5\n  - name: b\n"));
    assert.doesNotMatch(d.svg, /t-dot|t-gap/);
    assert.equal(d.counted, false);
  });

  // @spec ONB-SHOWCASE-040, ONB-SHOWCASE-041, ONB-SHOWCASE-042, ONB-SHOWCASE-045, ONB-SHOWCASE-091
  it("shows no visible text but HLD, titles named nodes, and labels the whole drawing", () => {
    const d = drawTree(tree("children:\n  - name: tax\n    specs: 45\n    built: 45\n  - name: tui\n    children:\n      - name: entry\n        specs: 30\n        built: 29\n      - specs: 3\n        built: 3\n"));
    const visible = [...d.svg.replace(/<title>[\s\S]*?<\/title>/g, "").matchAll(/<text[^>]*>([^<]*)<\/text>/g)].map((m) => m[1]);
    assert.deepEqual(visible, ["HLD"]);
    const titles = [...d.svg.matchAll(/<title>([^<]*)<\/title>/g)].map((m) => m[1]);
    assert.ok(titles.includes("tax: 45 specs, all built"), titles.join(" | "));
    assert.ok(titles.includes("entry: 30 specs, 29 built"));
    assert.ok(titles.includes("tui: sub-HLD, 2 design docs below"));
    assert.equal((d.svg.match(/tabindex="0"/g) || []).length, 3);
    assert.equal(d.docs, 3);
    assert.match(d.svg, /aria-label="[^"]*3 design docs[^"]*2 levels[^"]*78 specs/);
    const anon = drawTree(tree("children:\n  - specs: 1\n    built: 1\n"));
    assert.doesNotMatch(anon.svg, /<title>|tabindex/);
  });

  // @spec ONB-SHOWCASE-048
  it("keeps a minimum leaf width and lets very wide trees scroll", () => {
    const wide = drawTree({ children: Array.from({ length: 200 }, () => ({ specs: 1, built: 1 })) });
    const width = Number(wide.svg.match(/viewBox="0 0 ([\d.]+) /)[1]);
    assert.ok(width / 200 >= 12, `each leaf gets at least 12 units, got ${width / 200}`);
    assert.equal(wide.scrolls, true);
    assert.equal(drawTree({ children: [{ specs: 1, built: 1 }] }).scrolls, false);
  });
});

describe("the built showcase", () => {
  let out;
  const page = (path) => readFileSync(join(out, path), "utf8");
  const text = (s) => s.replace(/<[^>]+>/g, " ").replace(/&#39;|&rsquo;|’/g, "'").replace(/&amp;/g, "&").replace(/\s+/g, " ").trim();
  let index;
  let entries;

  before(() => {
    out = mkdtempSync(join(tmpdir(), "lid-showcase-"));
    roots.push(out);
    execFileSync("npx", ["eleventy", `--output=${out}`], { cwd: siteDir, stdio: "pipe" });
    index = page("examples/index.html");
    entries = loadEntries(join(siteDir, "src", "examples"));
  });
  const main = (html) => html.match(/<main[\s\S]*<\/main>/)[0];
  const cards = () => [...main(index).matchAll(/<article class="node (?:feature|story)"[\s\S]*?<\/article>/g)].map((m) => m[0]);

  // @spec ONB-SHOWCASE-001, ONB-SHOWCASE-002
  it("serves the index with a claim heading that states no count", () => {
    const h1 = text(main(index).match(/<h1[^>]*>([\s\S]*?)<\/h1>/)[1]);
    assert.match(h1, /LID/);
    assert.doesNotMatch(h1, /\d|\b(one|two|three|four|five|six|seven|eight|nine|ten)\b/i);
  });

  // @spec ONB-SHOWCASE-003, ONB-SHOWCASE-004, ONB-SHOWCASE-005, ONB-SHOWCASE-008
  it("lists every entry once, newest first, the first one featured, each linking to its page", () => {
    const list = cards();
    assert.equal(list.length, entries.length);
    assert.match(list[0], /class="node feature"/);
    list.slice(1).forEach((c) => assert.match(c, /class="node story"/));
    entries.forEach((e, i) => assert.ok(list[i].includes(`href="/examples/${e.slug}/"`), e.slug));
  });

  // @spec ONB-SHOWCASE-006, ONB-SHOWCASE-007
  it("shows each card's contents", () => {
    cards().forEach((c, i) => {
      const e = entries[i];
      const t = text(c);
      for (const s of [e.project, e.credit, e.tagline, e.open_source ? "Open source" : "Code private"]) assert.ok(t.includes(text(s)), `${e.slug}: ${s}`);
      assert.ok(t.includes(text(e.story ? e.story.title : e.project)), e.slug);
      if (e.size) assert.ok(t.includes(e.size), e.slug);
      (e.stats || []).forEach((s, k) => assert.equal(t.includes(text(s[1])), k < 3, `${e.slug} stat ${k}`));
      if (e.pictures.length) assert.ok(c.includes(`src="/examples/${e.slug}/${e.pictures[0].file}"`), e.slug);
      else assert.match(c, /<svg class="tree-svg"/);
    });
  });

  // @spec ONB-SHOWCASE-009, ONB-SHOWCASE-010, ONB-SHOWCASE-011, ONB-SHOWCASE-071
  it("shows the two reference trees, measured from the repository", () => {
    const sec = main(index).match(/<section[^>]*id="whole-tree"[\s\S]*?<\/section>/)[0];
    assert.match(text(sec), /Read a whole tree/);
    assert.ok(sec.includes('href="https://github.com/jszmajda/lid/tree/main/examples/urlshort"'));
    assert.ok(sec.includes('href="https://github.com/jszmajda/lid/tree/main/docs/intent"'));
    assert.equal((sec.match(/<svg class="tree-svg"/g) || []).length, 2);
    for (const s of sec.match(/<p class="ref-sentence">[\s\S]*?<\/p>/g)) assert.doesNotMatch(text(s), /\d/);
    const lid = execFileSync("node", [join(siteDir, "scripts", "intent-tree.js"), join(repoDir, "docs", "intent")], { encoding: "utf8" });
    const total = [...lid.matchAll(/specs: (\d+)/g)].reduce((a, m) => a + Number(m[1]), 0);
    assert.ok(text(sec).includes(total.toLocaleString("en-US") + " specs"), `LID's measured total ${total}`);
    assert.match(text(sec), /Small|Medium|Large|Very large/);
  });

  // @spec ONB-SHOWCASE-012
  it("closes with the invitation to add a project", () => {
    const end = text(main(index).slice(-3000));
    assert.match(end, /pull request/i);
    assert.match(end, /private/i);
    assert.match(end, /names/i);
    assert.ok(index.includes('href="https://github.com/jszmajda/lid/blob/main/CONTRIBUTING.md#share-a-project-you-built"'));
  });

  // @spec ONB-SHOWCASE-016, ONB-SHOWCASE-017, ONB-SHOWCASE-018, ONB-SHOWCASE-023
  it("serves a page for each entry with its reading column, side column, and tree", () => {
    for (const e of entries) {
      const p = main(page(`examples/${e.slug}/index.html`));
      const reading = p.match(/<div class="proj-main">[\s\S]*?<!-- \/proj-main -->/)[0];
      const side = p.match(/<aside class="proj-side">[\s\S]*?<\/aside>/)[0];
      assert.ok(text(reading).includes(text(e.owner)), e.slug);
      assert.ok(text(reading).includes(e.open_source ? "Open source" : "Code private"), e.slug);
      assert.match(reading, new RegExp(`<h1[^>]*>${e.project}</h1>`));
      assert.ok(text(reading).includes(text(e.tagline)));
      assert.match(text(side), /How big it is/);
      if (e.size) assert.ok(text(side).includes(e.size));
      for (const s of e.stats || []) assert.ok(text(side).includes(text(s[1])), `${e.slug}: ${s[1]}`);
      for (const url of Object.values(e.links || {})) assert.ok(side.includes(`href="${url}"`), url);
      e.pictures.forEach((pic) => assert.ok(side.includes(`/examples/${e.slug}/${pic.file}`), pic.file));
      assert.equal(/<section class="sec-sm tree-section"/.test(p), Boolean(e.tree), `${e.slug} tree section`);
    }
  });

  // @spec ONB-SHOWCASE-021, ONB-SHOWCASE-022
  it("shows each story card with where the story lives", () => {
    for (const e of entries.filter((x) => x.story)) {
      const card = main(page(`examples/${e.slug}/index.html`)).match(/<div class="node story-link[\s\S]*?<!-- \/story-link -->/)[0];
      assert.ok(text(card).includes(text(e.story.title)), e.slug);
      assert.ok(text(card).includes(text(e.story.byline)), e.slug);
      if (e.story.file) assert.match(text(card), /Hosted here/);
      else if (e.story.url) assert.ok(text(card).includes(new URL(e.story.url).host), e.slug);
      else assert.match(text(card), /to come/);
      assert.equal(/<a class="btn btn-ghost"/.test(card), Boolean(e.story.file || e.story.url), e.slug);
    }
  });

  // @spec ONB-SHOWCASE-024, ONB-SHOWCASE-025, ONB-SHOWCASE-026, ONB-SHOWCASE-028
  it("hosts stories: Markdown in the site's style, HTML as written plus one bar", () => {
    for (const e of entries.filter((x) => x.story && x.story.file)) {
      const served = page(`examples/${e.slug}/story/index.html`);
      const source = readFileSync(join(siteDir, "src", "examples", e.slug, e.story.file), "utf8");
      if (e.story.file === "story.md") {
        assert.match(served, /<header class="nav-bar"/);
        assert.ok(served.includes(`href="/examples/${e.slug}/"`));
        assert.ok(text(served).includes(text(e.story.title)));
        assert.ok(text(served).includes(text(e.story.byline)));
      } else {
        const bar = served.match(/<body[^>]*>\s*(<div data-lid-story-bar[\s\S]*?<\/div>)/);
        assert.ok(bar, `${e.slug}: bar is the body's first child`);
        assert.ok(bar[1].includes(`href="/examples/${e.slug}/"`));
        assert.ok(text(bar[1]).includes(text(e.owner)));
        assert.ok(text(bar[1]).includes(text(e.story.author)));
        assert.doesNotMatch(bar[1], /class=/);
        assert.equal(served.replace(bar[1], ""), source);
      }
    }
  });

  // @spec ONB-SHOWCASE-027, ONB-SHOWCASE-092
  it("serves pictures beside each page and a hosted HTML story's files beside it", () => {
    for (const e of entries) {
      e.pictures.forEach((pic) => assert.ok(existsSync(join(out, "examples", e.slug, pic.file)), `${e.slug}/${pic.file}`));
      if (e.story && e.story.file === "story.html") {
        const others = readdirSync(join(siteDir, "src", "examples", e.slug)).filter((f) => !["index.md", "tree.yaml", "story.html"].includes(f));
        others.forEach((f) => assert.ok(existsSync(join(out, "examples", e.slug, "story", f)), `${e.slug}/story/${f}`));
      }
    }
  });

  // @spec ONB-SHOWCASE-029, ONB-SHOWCASE-033
  it("makes every picture on a project's page a link to its full-size file, with alt text", () => {
    for (const e of entries) {
      const p = main(page(`examples/${e.slug}/index.html`));
      for (const pic of e.pictures) {
        const url = `/examples/${e.slug}/${pic.file}`;
        const link = p.match(new RegExp(`<a[^>]*href="${url}"[^>]*>\\s*<img[^>]*>`));
        assert.ok(link, `${e.slug}: ${pic.file} is linked`);
        const alt = link[0].match(/alt="([^"]*)"/)[1].replace(/&#39;/g, "'").replace(/&quot;/g, '"').replace(/&amp;/g, "&");
        assert.equal(alt, pic.alt, `${e.slug}: alt`);
      }
    }
  });

  // @spec ONB-SHOWCASE-030, ONB-SHOWCASE-031, ONB-SHOWCASE-032, ONB-SHOWCASE-043, ONB-SHOWCASE-044
  it("ships the zoom dialog and tree labels as script that enhances working pages", () => {
    const js = readFileSync(join(out, "assets/js/showcase.js"), "utf8");
    assert.match(js, /showModal\(\)/);
    assert.match(js, /preventDefault\(\)/);
    assert.match(js, /Escape|cancel/);
    assert.match(js, /\.focus\(\)/);
    assert.match(js, /pointerenter/);
    assert.match(js, /pointerleave/);
    assert.match(js, /focusin|"focus"/);
    for (const e of entries) assert.match(page(`examples/${e.slug}/index.html`), /<script src="\/assets\/js\/showcase\.js[^"]*" defer><\/script>/);
  });

  // @spec ONB-SHOWCASE-046, ONB-SHOWCASE-047
  it("puts a legend under each drawing, with dot keys only for counted trees and the names line only for named ones", () => {
    for (const e of entries.filter((x) => x.tree)) {
      const sec = main(page(`examples/${e.slug}/index.html`)).match(/<section class="sec-sm tree-section"[\s\S]*?<\/section>/)[0];
      const legend = text(sec.match(/<figcaption[\s\S]*?<\/figcaption>/)[0]);
      for (const k of ["the HLD", "a sub-HLD", "a design doc"]) assert.ok(legend.includes(k), `${e.slug}: ${k}`);
      assert.equal(/built spec/.test(legend), e.drawing.counted, `${e.slug} dot keys`);
      assert.equal(/hover or tap/i.test(legend), e.drawing.named, `${e.slug} names line`);
    }
  });

  // @spec ONB-SHOWCASE-019, ONB-SHOWCASE-020
  it("stacks a project's page on narrow screens and keeps pictures under two thirds of the screen", () => {
    const css = readFileSync(join(out, "assets/css/main.css"), "utf8");
    assert.match(css, /@media \(max-width: [\d]+px\) \{[^}]*\.proj \{ grid-template-columns: 1fr;/);
    assert.match(css, /\.shot img \{[^}]*max-height: 66vh/);
  });

  // @spec ONB-SHOWCASE-066
  it("does not publish the template entry", () => {
    assert.equal(existsSync(join(out, "examples", "_template")), false);
    assert.ok(existsSync(join(siteDir, "src", "examples", "_template", "index.md")));
  });
});

describe("the example pull-request template", () => {
  const tpl = readFileSync(join(repoDir, ".github", "PULL_REQUEST_TEMPLATE", "example.md"), "utf8");
  // @spec ONB-SHOWCASE-086
  it("asks for the project's basics", () => {
    for (const k of ["Name", "Owner", "One line on what it is", "Open source"]) assert.ok(tpl.includes(k), k);
  });
  // @spec ONB-SHOWCASE-087
  it("lists the folder's files with the tree command and its option", () => {
    for (const k of ["- [ ] `index.md`", "- [ ] A screenshot", "- [ ] `tree.yaml`", "node site/scripts/intent-tree.js", "--no-names", "story.md", "story.html"]) assert.ok(tpl.includes(k), k);
  });
  // @spec ONB-SHOWCASE-088
  it("asks where the numbers come from", () => assert.match(tpl, /## About the numbers/));
  // @spec ONB-SHOWCASE-089
  it("asks for the three confirmations", () => {
    assert.match(tpl, /- \[ \] I own this project, or its owner has agreed/);
    assert.match(tpl, /- \[ \] Every picture and every word/);
    assert.match(tpl, /- \[ \] If an AI wrote the story's words, the entry credits it/);
  });
});
