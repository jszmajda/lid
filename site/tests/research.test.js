// Checks the research section: entry validation, and the built index and report pages.
// Run from the repository root:
//   node --test site/tests/research.test.js
import { execFileSync } from "node:child_process";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { after, before, describe, it } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { loadReports, STATUS_LABELS } from "../scripts/research-entries.js";

const siteDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const PNG = Buffer.from(
  "89504e470d0a1a0a0000000d4948445200000001000000010806000000" + "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082",
  "hex",
);
const roots = [];
after(() => roots.forEach((r) => rmSync(r, { recursive: true, force: true })));

const TODAY = "2026-11-24";
const FIELDS = [
  'title: "A study"',
  "date: 2026-11-20",
  "status: pilot",
  'summary: "What a study found, in its own words."',
  "tested:",
  '  lid: "1.4.6"',
  '  agent: "Claude Code 2.1.323"',
  '  model: "Claude Sonnet 5.5, medium effort"',
  'records: "https://github.com/jszmajda/lid/tree/main/docs/research"',
];
const BODY = "## What we found\n\nSome text.\n";
const front = (fields, body = BODY) => `---\n${fields.join("\n")}\n---\n${body}`;
const fieldsWith = (overrides = {}, drop = []) => {
  const out = FIELDS.filter((f) => !drop.some((d) => f.startsWith(d + ":")) && !(drop.includes("tested") && f.startsWith("  ")));
  return out.map((f) => {
    const key = f.split(":")[0];
    return key in overrides ? `${key}: ${overrides[key]}` : f;
  });
};

// Writes entry folders into a fresh research directory and returns that directory.
function researchWith(entries, loose = {}) {
  const root = mkdtempSync(join(tmpdir(), "research-"));
  roots.push(root);
  for (const [slug, files] of Object.entries(entries)) {
    mkdirSync(join(root, slug), { recursive: true });
    for (const [name, content] of Object.entries(files)) writeFileSync(join(root, slug, name), content);
  }
  for (const [name, content] of Object.entries(loose)) writeFileSync(join(root, name), content);
  return root;
}
const entry = (fields = FIELDS, body = BODY, files = {}) => ({ "index.md": front(fields, body), ...files });
const load = (entries, loose) => loadReports(researchWith(entries, loose), { today: TODAY });
const fails = (entries, pattern, loose) =>
  assert.throws(() => load(entries, loose), (e) => pattern.test(e.message), `expected ${pattern}`);

describe("research entries", () => {
  // @spec ONB-RESEARCH-040, ONB-RESEARCH-041
  it("reads each folder not starting with _ or . as one entry", () => {
    const list = load({ study: entry(), _template: { "index.md": "---\nanything: goes\n---\n" }, ".draft": { "index.md": "x" } });
    assert.deepEqual(list.map((e) => e.slug), ["study"]);
    assert.equal(list[0].title, "A study");
    assert.match(list[0].body, /## What we found/);
  });

  // @spec ONB-RESEARCH-050
  it("names the entry and the rule when an entry breaks one", () => {
    assert.throws(() => load({ "bad-one": entry(fieldsWith({ status: "final" })) }), /research\/bad-one: .*status/);
  });

  // @spec ONB-RESEARCH-051
  it("rejects a slug with anything but lowercase letters, digits, and hyphens", () => {
    fails({ "Study_1": entry() }, /slug/);
  });

  // @spec ONB-RESEARCH-052
  it("requires every required field and rejects unknown ones", () => {
    for (const field of ["title", "date", "status", "summary", "tested", "records"]) fails({ study: entry(fieldsWith({}, [field])) }, new RegExp(field));
    fails({ study: entry([...FIELDS, "author: Someone"]) }, /unknown field `author`/);
  });

  // @spec ONB-RESEARCH-053
  it("requires a title and a summary with something other than whitespace", () => {
    fails({ study: entry(fieldsWith({ title: '"   "' })) }, /title/);
    fails({ study: entry(fieldsWith({ summary: '""' })) }, /summary/);
  });

  // @spec ONB-RESEARCH-054
  it("requires real calendar dates no later than the day of the build in UTC", () => {
    assert.equal(load({ study: entry(fieldsWith({ date: '"2026-11-24"' })) })[0].date, "2026-11-24");
    fails({ study: entry(fieldsWith({ date: "2026-02-30" })) }, /date/);
    fails({ study: entry(fieldsWith({ date: '"2026-2-3"' })) }, /date/);
    fails({ study: entry(fieldsWith({ date: "2026-11-25" })) }, /date.*later than the day of the build/);
    fails({ study: entry([...FIELDS, "revised: 2026-11-25"]) }, /revised/);
  });

  // @spec ONB-RESEARCH-055
  it("requires a revision date later than the first date", () => {
    fails({ study: entry([...FIELDS, "revised: 2026-11-20"]) }, /revised.*later than/);
    assert.equal(load({ study: entry([...FIELDS, "revised: 2026-11-22"]) })[0].revised, "2026-11-22");
  });

  // @spec ONB-RESEARCH-056
  it("accepts only pilot, counted, and superseded as a status", () => {
    for (const s of ["pilot", "counted"]) assert.equal(load({ study: entry(fieldsWith({ status: s })) })[0].status, s);
    fails({ study: entry(fieldsWith({ status: "draft" })) }, /status/);
  });

  // @spec ONB-RESEARCH-057
  it("requires a superseded entry to name an existing, current entry other than itself", () => {
    const old = (to) => entry([...fieldsWith({ status: "superseded" }), `superseded_by: ${to}`]);
    const list = load({ old: old("new"), new: entry(fieldsWith({ date: "2026-11-23" })) });
    assert.equal(list.find((e) => e.slug === "old").supersededBy.slug, "new");
    fails({ old: entry(fieldsWith({ status: "superseded" })) }, /superseded_by/);
    fails({ old: old("old") }, /superseded_by/);
    fails({ old: old("missing") }, /superseded_by/);
    fails({ old: old("New") }, /superseded_by/);
    fails({ a: old("b"), b: entry([...fieldsWith({ status: "superseded", date: "2026-11-21" }), "superseded_by: c"]), c: entry() }, /superseded_by/);
  });

  // @spec ONB-RESEARCH-058
  it("rejects superseded_by on an entry that isn't superseded", () => {
    fails({ a: entry([...FIELDS, "superseded_by: b"]), b: entry() }, /superseded_by/);
  });

  // @spec ONB-RESEARCH-059
  it("requires tested to give lid, agent, and model and nothing else", () => {
    const tested = (lines) => [...FIELDS.filter((f) => !f.startsWith("tested") && !f.startsWith("  ")), "tested:", ...lines];
    fails({ study: entry(tested(['  lid: "1.4.6"', '  agent: "Claude Code"'])) }, /tested/);
    fails({ study: entry(tested(['  lid: "1.4.6"', '  agent: "Claude Code"', '  model: "  "'])) }, /tested/);
    fails({ study: entry(tested(['  lid: "1.4.6"', '  agent: "Claude Code"', '  model: "Sonnet"', '  os: "macOS"'])) }, /tested/);
    fails({ study: entry([...FIELDS.filter((f) => !f.startsWith("tested") && !f.startsWith("  ")), 'tested: "LID 1.4.6"']) }, /tested/);
  });

  // @spec ONB-RESEARCH-060
  it("requires a plain-text summary of at most 300 characters", () => {
    fails({ study: entry(fieldsWith({ summary: '"A *bold* claim."' })) }, /summary/);
    fails({ study: entry(fieldsWith({ summary: '"See [the notes](https://example.com)."' })) }, /summary/);
    fails({ study: entry(fieldsWith({ summary: `"${"a".repeat(301)}"` })) }, /summary/);
    assert.equal(load({ study: entry(fieldsWith({ summary: `"${"é".repeat(300)}"` })) })[0].summary.length, 300);
    assert.ok(load({ study: entry(fieldsWith({ summary: '"It costs 3.3 to 5.5 times as much & asks more."' })) }));
  });

  // @spec ONB-RESEARCH-061
  it("requires records to be an https URL with a host", () => {
    fails({ study: entry(fieldsWith({ records: '"http://example.com"' })) }, /records/);
    fails({ study: entry(fieldsWith({ records: '"https://"' })) }, /records/);
    fails({ study: entry(fieldsWith({ records: '"/docs/research"' })) }, /records/);
  });

  // @spec ONB-RESEARCH-062
  it("requires a report body with something other than whitespace", () => {
    fails({ study: entry(FIELDS, "\n   \n") }, /body/);
  });

  // @spec ONB-RESEARCH-063
  it("rejects a level-1 heading in either form, but not one inside a code block", () => {
    fails({ study: entry(FIELDS, "# Title\n\nText.\n") }, /h1|level-1/);
    fails({ study: entry(FIELDS, "Title\n=====\n\nText.\n") }, /h1|level-1/);
    assert.ok(load({ study: entry(FIELDS, "## A section\n\n```\n# not a heading\n```\n") }));
  });

  // @spec ONB-RESEARCH-064
  it("rejects raw HTML, but not autolinks or code", () => {
    fails({ study: entry(FIELDS, "## A\n\n<div>block</div>\n") }, /HTML/);
    fails({ study: entry(FIELDS, "## A\n\nText with a <br> break.\n") }, /HTML/);
    fails({ study: entry(FIELDS, "## A\n\n<!-- a note -->\n") }, /HTML/);
    assert.ok(load({ study: entry(FIELDS, "## A\n\nSee <https://example.com>, `<div>` and\n\n```\n<script>x</script>\n```\n") }));
  });

  // @spec ONB-RESEARCH-065
  it("allows only https links, anchors, mailto, and bare names of images in the folder", () => {
    assert.ok(load({ study: entry(FIELDS, "## A\n\n[x](https://example.com/a) [y](#a) [z](mailto:a@example.com) ![chart](chart.png)\n", { "chart.png": PNG }) }));
    for (const href of ["http://example.com", "//example.com/x", "./chart.png", "sub/chart.png", "../chart.png", "/research/", "missing.png", "notes.csv"]) {
      fails({ study: entry(FIELDS, `## A\n\n[x](${href})\n`, { "chart.png": PNG, "notes.csv": "a,b" }) }, /link|file/);
    }
  });

  // @spec ONB-RESEARCH-066
  it("rejects files the report doesn't reference, and files that aren't images", () => {
    fails({ study: entry(FIELDS, BODY, { "unused.png": PNG }) }, /unused\.png/);
    fails({ study: entry(FIELDS, BODY, { "data.csv": "a,b" }) }, /data\.csv/);
    assert.ok(load({ study: entry(FIELDS, "## A\n\n[the chart](chart.png)\n", { "chart.png": PNG }) }));
  });

  // @spec ONB-RESEARCH-067
  it("accepts lowercase png, jpg, jpeg, and svg images of at most 2,000,000 bytes", () => {
    fails({ study: entry(FIELDS, "## A\n\n![c](chart.PNG)\n", { "chart.PNG": PNG }) }, /chart\.PNG/);
    fails({ study: entry(FIELDS, "## A\n\n![c](chart.gif)\n", { "chart.gif": PNG }) }, /chart\.gif/);
    fails({ study: entry(FIELDS, "## A\n\n![c](big.png)\n", { "big.png": Buffer.alloc(2_000_001) }) }, /big\.png/);
    assert.ok(load({ study: entry(FIELDS, "## A\n\n![c](a.jpg) ![d](b.jpeg)\n", { "a.jpg": PNG, "b.jpeg": PNG }) }));
  });

  // @spec ONB-RESEARCH-068
  it("rejects an SVG that could carry code or reach outside the folder", () => {
    const svg = (inner) => `<svg xmlns="http://www.w3.org/2000/svg">${inner}</svg>`;
    const withSvg = (inner) => entry(FIELDS, "## A\n\n![c](c.svg)\n", { "c.svg": svg(inner), "other.png": PNG });
    assert.ok(load({ study: entry(FIELDS, "## A\n\n![c](c.svg) ![o](other.png)\n", { "c.svg": svg('<use href="#a"/><image href="other.png"/>'), "other.png": PNG }) }));
    for (const inner of ["<script>alert(1)</script>", '<rect onclick="x()"/>', "<foreignObject></foreignObject>", '<image href="https://example.com/a.png"/>', '<image xlink:href="../a.png"/>', '<rect style="fill:url(https://example.com/a)"/>']) {
      fails({ study: withSvg(inner) }, /svg|SVG/);
    }
  });

  // @spec ONB-RESEARCH-069
  it("rejects a file directly in the research folder", () => {
    fails({ study: entry() }, /stray\.md/, { "stray.md": "x" });
  });

  // @spec ONB-RESEARCH-004
  it("orders entries newest first, ties by slug, and ignores revised", () => {
    const list = load({
      "b-study": entry(fieldsWith({ date: "2026-11-20" })),
      "a-study": entry(fieldsWith({ date: "2026-11-20" })),
      newer: entry(fieldsWith({ date: "2026-11-22" })),
      older: entry([...fieldsWith({ date: "2026-11-01" }), "revised: 2026-11-23"]),
    });
    assert.deepEqual(list.map((e) => e.slug), ["newer", "a-study", "b-study", "older"]);
  });

  // @spec ONB-RESEARCH-020, ONB-RESEARCH-022
  it("labels each status and records which reports each entry replaces", () => {
    assert.deepEqual(STATUS_LABELS, { pilot: "Pilot results", counted: "Counted results", superseded: "Superseded" });
    const old = (date) => entry([...fieldsWith({ status: "superseded", date }), "superseded_by: new"]);
    const list = load({ old1: old("2026-11-01"), old2: old("2026-11-02"), new: entry(fieldsWith({ date: "2026-11-23", status: "counted" })) });
    const replacement = list.find((e) => e.slug === "new");
    assert.equal(replacement.statusLabel, "Counted results");
    assert.deepEqual(replacement.replaces.map((r) => r.slug).sort(), ["old1", "old2"]);
  });
});

describe("the built research pages", () => {
  let out;
  const page = (p) => readFileSync(join(out, p), "utf8");
  before(() => {
    const dir = researchWith({
      "first-study": entry(
        [...fieldsWith({ title: '"The first study"', date: "2026-11-01", status: "superseded", summary: '"First results & more, as 3 < 4."' }), "revised: 2026-11-05", "superseded_by: second-study"],
        "## Results\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\n![a chart](chart.png)\n",
        { "chart.png": PNG },
      ),
      "second-study": entry(fieldsWith({ title: '"The second study"', date: "2026-11-20", status: "counted" })),
    });
    out = mkdtempSync(join(tmpdir(), "research-site-"));
    roots.push(out);
    execFileSync("npx", ["eleventy", `--output=${out}`], { cwd: siteDir, stdio: "pipe", env: { ...process.env, LID_RESEARCH_DIR: dir, LID_RESEARCH_TODAY: TODAY } });
  });

  // @spec ONB-RESEARCH-001, ONB-RESEARCH-002, ONB-RESEARCH-003
  it("serves the index with an h1 about costs and payoffs, stating no finding", () => {
    const html = page("research/index.html");
    const h1 = html.match(/<h1[^>]*>([\s\S]*?)<\/h1>/)[1];
    assert.match(h1, /costs/i);
    assert.match(h1, /buys/i);
    assert.doesNotMatch(h1 + (html.match(/<p class="lede">([\s\S]*?)<\/p>/) || ["", ""])[1], /\d|times as much|more than|fewer|better|worse/i);
  });

  // @spec ONB-RESEARCH-004, ONB-RESEARCH-005, ONB-RESEARCH-006, ONB-RESEARCH-013, ONB-RESEARCH-017, ONB-RESEARCH-018
  it("lists every report once, newest first, with its details and a link", () => {
    const html = page("research/index.html");
    const cards = html.match(/<article class="report-card[\s\S]*?<\/article>/g);
    assert.equal(cards.length, 2);
    assert.match(cards[0], /The second study/);
    assert.match(cards[1], /The first study/);
    for (const [card, slug] of [[cards[0], "second-study"], [cards[1], "first-study"]]) {
      assert.match(card, new RegExp(`href="/research/${slug}/"`));
      assert.match(card, /1\.4\.6/);
      assert.match(card, /Claude Code 2\.1\.323/);
      assert.match(card, /Claude Sonnet 5\.5, medium effort/);
    }
    assert.match(cards[0], /Counted results/);
    assert.match(cards[1], /Superseded/);
    assert.match(cards[1], /1 Nov 2026/);
    assert.doesNotMatch(cards[1], /5 Nov 2026|revised/i);
    assert.match(cards[1], /First results &amp; more, as 3 &lt; 4\./);
  });

  // @spec ONB-RESEARCH-010, ONB-RESEARCH-011, ONB-RESEARCH-012, ONB-RESEARCH-014, ONB-RESEARCH-018
  it("serves each report with its header above the report", () => {
    const html = page("research/first-study/index.html");
    assert.equal((html.match(/<h1\b/g) || []).length, 1);
    const head = html.slice(0, html.indexOf('class="prose'));
    assert.match(head, /href="\/research\/"/);
    assert.match(head, /<h1[^>]*>The first study<\/h1>/);
    assert.match(head, /1 Nov 2026/);
    assert.match(head, /revised[^<]*5 Nov 2026|revised<\/span>\s*5 Nov 2026/);
    assert.match(head, /Superseded/);
    assert.match(head, /What was tested/);
    const tested = head.slice(head.indexOf("What was tested"));
    assert.ok(tested.indexOf("1.4.6") < tested.indexOf("Claude Code") && tested.indexOf("Claude Code") < tested.indexOf("Claude Sonnet"));
    assert.match(head, /<a href="https:\/\/github\.com\/jszmajda\/lid\/tree\/main\/docs\/research">The study&#39;s records<\/a>|<a href="https:\/\/github\.com\/jszmajda\/lid\/tree\/main\/docs\/research">The study’s records<\/a>|>The study's records<\/a>/);
    assert.match(html, /<h2[^>]*>Results<\/h2>/);
    assert.ok(existsSync(join(out, "research", "first-study", "chart.png")));
  });

  // @spec ONB-RESEARCH-015
  it("puts each table in its own sideways-scrolling frame", () => {
    assert.match(page("research/first-study/index.html"), /<div class="table-frame">\s*<table>/);
    assert.match(readFileSync(join(siteDir, "src", "assets", "css", "main.css"), "utf8"), /\.table-frame\s*\{[^}]*overflow-x:\s*auto/);
  });

  // @spec ONB-RESEARCH-021, ONB-RESEARCH-022
  it("links a superseded report to its replacement, and back, below the h1", () => {
    const first = page("research/first-study/index.html");
    const afterH1 = first.slice(first.indexOf("</h1>"), first.indexOf("</h1>") + 600);
    assert.match(afterH1, /class="supersede-note[^"]*"[\s\S]*href="\/research\/second-study\/"/);
    const second = page("research/second-study/index.html");
    const afterH1b = second.slice(second.indexOf("</h1>"), second.indexOf("</h1>") + 600);
    assert.match(afterH1b, /class="supersede-note[^"]*"[\s\S]*href="\/research\/first-study\/"/);
  });

  // @spec ONB-RESEARCH-030, ONB-RESEARCH-031
  it("previews the index and each report with the default card", () => {
    const index = page("research/index.html");
    assert.match(index, /<meta property="og:image" content="[^"]*\/assets\/social-card\.png"/);
    assert.match(index, /<meta property="og:title" content="Research/);
    const report = page("research/second-study/index.html");
    assert.match(report, /<meta property="og:image" content="[^"]*\/assets\/social-card\.png"/);
    assert.match(report, /<meta property="og:title" content="The second study/);
    assert.match(report, /<meta property="og:description" content="What a study found, in its own words\."/);
  });
});

describe("the real research section", () => {
  let out;
  before(() => {
    out = mkdtempSync(join(tmpdir(), "research-real-"));
    roots.push(out);
    execFileSync("npx", ["eleventy", `--output=${out}`], { cwd: siteDir, stdio: "pipe" });
  });

  // @spec ONB-RESEARCH-042
  it("carries a commented template that the site doesn't publish", () => {
    const template = readFileSync(join(siteDir, "src", "research", "_template", "index.md"), "utf8");
    const frontMatter = template.split("---")[1];
    for (const field of ["title", "date", "revised", "status", "superseded_by", "summary", "tested", "records"]) {
      assert.match(frontMatter, new RegExp(`#.*\\b${field}\\b|\\b${field}\\b.*#`), field);
    }
    assert.ok(!existsSync(join(out, "research", "_template")));
  });

  // @spec ONB-RESEARCH-001, ONB-RESEARCH-010
  it("publishes every real entry", () => {
    for (const e of loadReports(join(siteDir, "src", "research"))) assert.ok(existsSync(join(out, "research", e.slug, "index.html")), e.slug);
  });
});
