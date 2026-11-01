// Checks the built Logo Ideas page. Run from the repository root:
//   node --test site/tests/logo-ideas.test.js
// Removed along with the page once a logo is chosen.
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, readdirSync, rmSync, statSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join, relative } from "node:path";
import { after, before, describe, it } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";

const siteDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const MAIN_LOGOS = ["Nodes, plain I", "Nodes, slab I", "Markdown", "Wiki Link"];
const MORE_LOGOS = ["Pointer Tails", "Link Dot", "Deref", "Snake", "Soft Cut", "Git Graph"];

let out;
let page;

function htmlFiles(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return htmlFiles(path);
    return name.endsWith(".html") ? [path] : [];
  });
}

function section(cls) {
  const match = page.match(new RegExp(`<section class="${cls}"[\\s\\S]*?</section>`));
  assert.ok(match, `the page has a ${cls} section`);
  return match[0];
}

function logosIn(html) {
  return [...html.matchAll(/data-logo="([^"]+)"/g)].map((m) => m[1]);
}

function articles() {
  return [...page.matchAll(/<article class="logo-card[^"]*"[\s\S]*?<\/article>/g)].map((m) => m[0]);
}

function mainContent() {
  return page.match(/<main[\s\S]*<\/main>/)[0];
}

function pageStyle() {
  return mainContent().match(/<style>([\s\S]*?)<\/style>/)[1];
}

before(() => {
  out = mkdtempSync(join(tmpdir(), "lid-site-"));
  execFileSync("npx", ["eleventy", `--output=${out}`], { cwd: siteDir, stdio: "pipe" });
  page = readFileSync(join(out, "logo-ideas", "index.html"), "utf8");
});

after(() => {
  if (out) rmSync(out, { recursive: true, force: true });
});

describe("Logo Ideas page", () => {
  // @spec MKT-SITE-019
  it("stays outside the five top-level pages in the navigation", () => {
    const home = readFileSync(join(out, "index.html"), "utf8");
    const nav = home.match(/<ul class="nav-list">[\s\S]*?<\/ul>/)[0];
    const labels = [...nav.matchAll(/<a [^>]*>([^<]+)<\/a>/g)].map((m) => m[1].trim());
    assert.deepEqual(labels, ["Home", "Start", "Examples", "Anti-patterns", "Tour", "GitHub ↗"]);
  });

  // @spec MKT-SITE-083
  it("presents the logos as ideas and says none has been chosen", () => {
    assert.match(mainContent(), /no logo has been chosen/i);
  });

  // @spec MKT-SITE-084
  it("is not linked from any other page", () => {
    const linking = htmlFiles(out)
      .filter((file) => !file.endsWith(join("logo-ideas", "index.html")))
      .filter((file) => readFileSync(file, "utf8").includes("logo-ideas"))
      .map((file) => relative(out, file));
    assert.deepEqual(linking, []);
  });

  // @spec MKT-SITE-085
  it("asks search engines not to index it, without listing it in robots.txt", () => {
    assert.match(page, /<meta name="robots" content="noindex"/);
    assert.doesNotMatch(readFileSync(join(out, "robots.txt"), "utf8"), /logo-ideas/);
    assert.doesNotMatch(readFileSync(join(out, "index.html"), "utf8"), /name="robots"/, "other pages stay indexable");
  });

  // @spec MKT-SITE-086
  it("shows the main logos first", () => {
    assert.deepEqual(logosIn(section("logo-ideas-main")), MAIN_LOGOS);
    assert.ok(page.indexOf('class="logo-ideas-main"') < page.indexOf('class="logo-ideas-more"'));
  });

  // @spec MKT-SITE-087
  it("shows the other logos after them, at a smaller size", () => {
    assert.deepEqual(logosIn(section("logo-ideas-more")), MORE_LOGOS);
    assert.match(pageStyle(), /\.logo-ideas-main \.logo-grid/);
    assert.match(pageStyle(), /\.logo-ideas-more \.logo-grid/);
  });

  // @spec MKT-SITE-088
  it("gives each logo at least three lettered palettes, starting on A", () => {
    const cards = articles();
    assert.equal(cards.length, MAIN_LOGOS.length + MORE_LOGOS.length);
    for (const card of cards) {
      const radios = [...card.matchAll(/<input type="radio"[^>]*>/g)].map((m) => m[0]);
      assert.ok(radios.length >= 3, "at least three palettes");
      const values = radios.map((radio) => radio.match(/value="([a-z])"/)[1]);
      assert.deepEqual(values, "abcdefgh".slice(0, values.length).split(""));
      assert.deepEqual(radios.map((radio) => /\schecked/.test(radio)), radios.map((_, n) => n === 0));
    }
  });

  // @spec MKT-SITE-089
  it("builds the switch from native radio buttons and CSS", () => {
    for (const card of articles()) {
      const id = card.match(/id="(logo-[a-z-]+)"/)[1];
      const names = new Set([...card.matchAll(/<input type="radio" name="([^"]+)"/g)].map((m) => m[1]));
      assert.equal(names.size, 1, "one radio group per logo");
      assert.match(pageStyle(), new RegExp(`#${id}:has\\(input\\[value="b"\\]:checked\\)`));
    }
  });

  // @spec MKT-SITE-090
  it("has a label for every palette of every logo", () => {
    for (const card of articles()) {
      const name = card.match(/data-logo="([^"]+)"/)[1];
      const letters = [...card.matchAll(/<input type="radio"[^>]*value="([a-z])"/g)].map((m) => m[1]);
      for (const letter of letters) {
        assert.ok(
          card.includes(`data-palette="${letter}">${name}, palette ${letter.toUpperCase()}</span>`),
          `${name} has a label for palette ${letter}`
        );
      }
    }
  });

  // @spec MKT-SITE-090
  it("has a CSS rule that reveals the label of every palette letter in use", () => {
    const letters = new Set(articles().flatMap((card) => [...card.matchAll(/<input type="radio"[^>]*value="([a-z])"/g)].map((m) => m[1])));
    for (const letter of [...letters].filter((l) => l !== "a")) {
      assert.ok(
        pageStyle().includes(`.logo-card:has(input[value="${letter}"]:checked) .logo-label [data-palette="${letter}"]`),
        `palette ${letter} has a label rule`
      );
    }
  });

  // @spec MKT-SITE-097
  it("offers seven palettes on each main logo", () => {
    const main = section("logo-ideas-main");
    for (const name of MAIN_LOGOS) {
      const card = [...main.matchAll(/<article class="logo-card[^"]*"[\s\S]*?<\/article>/g)].map((m) => m[0]).find((c) => c.includes(`data-logo="${name}"`));
      assert.equal((card.match(/<input type="radio"/g) || []).length, 7, `${name} has seven palettes`);
    }
  });

  // @spec MKT-SITE-098
  it("gives plain and slab Nodes different palettes", () => {
    const palettes = (slug) => [...pageStyle().matchAll(new RegExp(`#logo-${slug}(?::has\\([^)]*\\))?\\{([^}]+)\\}`, "g"))].map((m) => m[1]);
    const plain = palettes("nodes-plain");
    const slab = palettes("nodes-slab");
    assert.ok(plain.length >= 3 && slab.length >= 3, "both versions have palettes");
    assert.deepEqual(plain.filter((p) => slab.includes(p)), []);
  });

  // @spec MKT-SITE-091
  it("adds copy buttons with a script, only where the clipboard is available", () => {
    assert.doesNotMatch(mainContent().replace(/<script[\s\S]*?<\/script>/g, ""), /<button/);
    const script = mainContent().match(/<script>([\s\S]*?)<\/script>/)[1];
    assert.match(script, /navigator\.clipboard/);
    assert.match(script, /writeText/);
  });

  // @spec MKT-SITE-092
  it("asks readers to send labels wherever they received the link", () => {
    assert.match(mainContent(), /send[^.]*labels?[^.]*wherever you received/i);
  });

  // @spec MKT-SITE-093
  it("has no comments, votes, forms, or feedback links in its main content", () => {
    const main = mainContent();
    for (const pattern of [/<form/, /<textarea/, /<iframe/, /type="text"/, /discussions/, /issues\/new/]) {
      assert.doesNotMatch(main, pattern);
    }
  });

  // @spec MKT-SITE-094
  it("sets logo colors per logo, with no theme-specific colors", () => {
    assert.doesNotMatch(pageStyle(), /prefers-color-scheme|data-theme/);
    for (const card of articles()) {
      const id = card.match(/id="(logo-[a-z-]+)"/)[1];
      assert.match(pageStyle(), new RegExp(`#${id}\\{--logo-ground:`));
    }
  });

  // @spec MKT-SITE-095
  it("keeps the standard navigation and drops only the sheet-number line", () => {
    assert.match(page, /<header class="site-nav">/);
    assert.doesNotMatch(page, /SHEET \d/);
    assert.match(readFileSync(join(out, "start", "index.html"), "utf8"), /SHEET 02 OF 05/);
  });

  it("draws every logo from shapes, with no font-dependent text and no duplicate ids", () => {
    const main = mainContent();
    assert.doesNotMatch(main, /<text[\s>]/);
    assert.equal((main.match(/<svg/g) || []).length, MAIN_LOGOS.length + MORE_LOGOS.length);
    const ids = [...page.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]);
    assert.deepEqual(ids.filter((id, n) => ids.indexOf(id) !== n), []);
  });
});
