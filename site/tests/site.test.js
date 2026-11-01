// Checks the built site. Run from the repository root:
//   node --test site/tests/site.test.js
import { execFileSync } from "node:child_process";
import { existsSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { after, before, describe, it } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";

const siteDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoUrl = "https://github.com/jszmajda/lid";
const PAGES = { Home: "index.html", Start: "start/index.html", Examples: "examples/index.html", "Anti-patterns": "anti-patterns/index.html", Tour: "tour/index.html" };

let out;
const html = {};
let css;

before(() => {
  out = mkdtempSync(join(tmpdir(), "lid-site-"));
  execFileSync("npx", ["eleventy", `--output=${out}`], { cwd: siteDir, stdio: "pipe" });
  for (const [name, file] of Object.entries(PAGES)) html[name] = readFileSync(join(out, file), "utf8");
  css = readFileSync(join(out, "assets/css/main.css"), "utf8");
});

after(() => {
  if (out) rmSync(out, { recursive: true, force: true });
});

const text = (fragment) => fragment.replace(/<[^>]+>/g, " ").replace(/&#39;|&rsquo;/g, "'").replace(/&quot;|&ldquo;|&rdquo;/g, '"').replace(/&amp;/g, "&").replace(/\s+/g, " ").replace(/\s+([,.;:!?])/g, "$1").trim();
function section(id, page = html.Home) {
  const match = page.match(new RegExp(`<section[^>]*\\bid="${id}"[\\s\\S]*?<!-- /section:${id} -->`));
  assert.ok(match, `the page has a ${id} section`);
  return match[0];
}
const cards = (fragment) => [...fragment.matchAll(/<li class="step"[\s\S]*?<!-- \/step -->/g)].map((m) => m[0]);
const files = (fragment) => [...fragment.matchAll(/<figure class="file">\s*<figcaption>([\s\S]*?)<\/figcaption>/g)].map((m) => text(m[1]));
const nav = (page) => page.match(/<header class="nav-bar"[\s\S]*?<\/header>/)[0];
const footer = (page) => page.match(/<footer class="site-footer"[\s\S]*?<\/footer>/)[0];
const rule = (selector) => {
  const match = css.match(new RegExp(`(^|\\n)${selector.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*\\{([^}]*)\\}`));
  assert.ok(match, `the stylesheet has a rule for ${selector}`);
  return match[2];
};

describe("structure and navigation", () => {
  // @spec MKT-SITE-019
  it("has exactly the five top-level pages", () => {
    const labels = [...nav(html.Home).match(/<ul class="nav-links">[\s\S]*?<\/ul>/)[0].matchAll(/<a [^>]*>([^<]+)<\/a>/g)].map((m) => m[1].trim());
    assert.deepEqual(labels, ["Start", "Examples", "Anti-patterns", "Tour", "GitHub"]);
    assert.equal(existsSync(join(out, "logo-ideas")), false);
  });

  // @spec MKT-SITE-020
  it("links every page to the others and to the repository", () => {
    for (const page of Object.values(html)) {
      const n = nav(page);
      for (const href of ["/start/", "/examples/", "/anti-patterns/", "/tour/", repoUrl]) assert.ok(n.includes(`href="${href}"`), href);
      assert.match(n, /<a class="home" href="\/"/);
    }
  });

  // @spec MKT-SITE-125
  it("shows the slab-I wordmark on its orange ground in every navigation", () => {
    for (const page of Object.values(html)) {
      const mark = nav(page).match(/<a class="home"[\s\S]*?<\/a>/)[0];
      assert.match(mark, /fill="#FF6B3D"/);
      assert.match(mark, /fill="#1A0F0A"/);
      assert.match(mark, /aria-label="LID home"/);
    }
  });

  // @spec MKT-SITE-126
  it("uses the flush-cut L as the favicon", () => {
    const icon = readFileSync(join(out, "assets/favicon.svg"), "utf8");
    assert.match(icon, /fill="#FF6B3D"/);
    assert.match(icon, /<clipPath/);
    assert.match(icon, /M23 24\.5H45V31\.5H23Z/, "the pointer starts flush with the stem");
    for (const page of Object.values(html)) assert.match(page, /<link rel="icon" href="\/assets\/favicon\.svg"/);
  });

  // @spec MKT-SITE-127
  it("keeps the navigation on screen with an Install button on every page", () => {
    assert.match(rule(".nav-bar"), /position:\s*sticky/);
    for (const page of Object.values(html)) assert.match(nav(page), /<a class="btn btn-go nav-install" href="\/#quickstart">Install<\/a>/);
  });

  // @spec MKT-SITE-128
  it("collapses the links into a Menu button on narrow screens, without JavaScript", () => {
    for (const page of Object.values(html)) {
      const menu = nav(page).match(/<details class="nav-menu">[\s\S]*?<\/details>/);
      assert.ok(menu, "the navigation has a details menu");
      assert.match(menu[0], /<summary[^>]*>[\s\S]*Menu[\s\S]*<\/summary>/);
      for (const href of ["/start/", "/examples/", "/anti-patterns/", "/tour/"]) assert.ok(menu[0].includes(`href="${href}"`));
    }
    assert.match(css, /@media \(max-width: 899px\) \{[^@]*\.nav-links \{ display: none; \}[^@]*\.nav-menu \{ display: block; \}/);
  });

  // @spec MKT-SITE-129
  it("draws the primary action as an orange pill and the secondary as an outlined pill", () => {
    const go = rule(".btn-go");
    assert.match(go, /background:\s*#FF6B3D/);
    assert.match(go, /color:\s*#1A0F0A/);
    assert.match(rule(".btn"), /border-radius:\s*999px/);
    assert.match(rule(".btn-ghost"), /border-color:\s*var\(--ink\)/);
    const ctas = section("hero").match(/<div class="ctas">[\s\S]*?<\/div>/)[0];
    assert.match(ctas, /class="btn btn-go" href="#quickstart"/);
    assert.match(ctas, /class="btn btn-ghost" href="https:\/\/github\.com\/jszmajda\/lid"/);
  });

  // @spec MKT-SITE-130
  it("loads Geologica and Spline Sans Mono from Bunny Fonts", () => {
    for (const page of Object.values(html)) assert.match(page, /fonts\.bunny\.net\/css\?family=geologica[^"]*spline-sans-mono/);
    assert.match(css, /--sans:\s*"Geologica"/);
    assert.match(css, /--mono:\s*"Spline Sans Mono"/);
  });

  // @spec MKT-SITE-131
  it("signs every footer with the icon, the author, the license, and the segment's docs", () => {
    for (const page of Object.values(html)) {
      const f = footer(page);
      assert.match(f, /<svg class="icon"/);
      assert.match(f, /Jess Szmajda/);
      assert.match(f, /MIT/);
      assert.ok(f.includes(`${repoUrl}/blob/main/docs/intent/marketing-site/marketing-site-design.md`));
      assert.ok(f.includes(`${repoUrl}/blob/main/docs/intent/marketing-site/marketing-site-specs.md`));
    }
  });
});

describe("home page", () => {
  // @spec MKT-SITE-007, MKT-SITE-064
  it("orders its sections around one request", () => {
    const ids = [...html.Home.matchAll(/<section[^>]*\bid="([a-z]+)"/g)].map((m) => m[1]);
    assert.deepEqual(ids, ["hero", "gap", "narrowing", "change", "check", "time", "teams", "quickstart", "experimental", "ecosystem", "paths"]);
  });

  // @spec MKT-SITE-111
  it("shows the finished rings in the hero, without labels", () => {
    const svg = section("hero").match(/<svg[^>]*class="rings-svg"[\s\S]*?<\/svg>/);
    assert.ok(svg, "the hero has a static rings drawing");
    assert.doesNotMatch(svg[0], />(HLD|LLD|tenet|TRIAL-003)</);
    assert.match(svg[0], /class="code"/);
  });

  // @spec MKT-SITE-099, MKT-SITE-103
  it("shows the gap: one request and the decisions it leaves open", () => {
    const gap = text(section("gap"));
    assert.match(section("gap"), /<div class="bubble">[\s\S]*Give new users a 30-day free trial\./);
    for (const decision of ["When the trial starts", "What happens when it ends", "Second trials", "When exactly day 30 ends"]) assert.ok(gap.includes(decision), decision);
  });

  // @spec MKT-SITE-100
  it("names the Tokyo signup", () => {
    assert.match(text(section("gap")), /11 p\.m\. on the 1st, in Tokyo/);
  });

  // @spec MKT-SITE-067
  it("says why green tests miss a misreading", () => {
    assert.match(text(section("gap")), /green tests/i);
    assert.match(text(section("gap")), /same guess/);
  });

  // @spec MKT-SITE-101, MKT-SITE-102
  it("narrows the request through six cards, each level a file in the project", () => {
    const c = cards(section("narrowing"));
    assert.equal(c.length, 6);
    assert.match(c[0], /<div class="bubble">[\s\S]*Give new users a 30-day free trial\./);
    assert.match(text(c[1]), /New users can try the app free for 30 days before they pay\./);
    assert.match(text(c[2]), /Customer delight over perfect cost management\./);
    assert.match(text(c[3]), /The trial ends 720 hours after signup\./);
    for (const id of ["TRIAL-001", "TRIAL-002", "TRIAL-003"]) assert.ok(text(c[4]).includes(id));
    assert.match(c[5], /@spec <span[^>]*>TRIAL-003<\/span>/);
    assert.deepEqual(files(section("narrowing")), ["docs/high-level-design.md", "docs/high-level-design.md", "docs/intent/trial/trial-design.md", "docs/intent/trial/trial-specs.md", "tests/trial.test.ts"]);
  });

  // @spec MKT-SITE-104
  it("writes the tenet as a preference between two good options", () => {
    const tenet = text(cards(section("narrowing"))[2]);
    assert.ok(tenet.includes("Customer delight over perfect cost management. When a choice could go either way, we lean toward the customer."));
    assert.match(tenet, /could reasonably (choose|pick) the other side/);
  });

  // @spec MKT-SITE-105
  it("writes every requirement in an EARS pattern", () => {
    const lines = [section("narrowing"), section("change")]
      .flatMap((s) => [...s.matchAll(/<b>(TRIAL-\d{3})<\/b>: ([^\n]*)/g)].map((m) => text(m[2])));
    assert.ok(lines.length >= 4);
    const ears = /^(The system shall|When [^,]+, the system shall|While [^,]+, the system shall|Where [^,]+, the system shall|If [^,]+, then the system shall) [^.]+\.$/;
    for (const line of lines) assert.match(line, ears);
  });

  // @spec MKT-SITE-106
  it("opens the change explainer by owning the volume", () => {
    const head = text(section("change").match(/<header class="sec-head">[\s\S]*?<\/header>/)[0]);
    assert.match(head, /a lot to write down/);
    assert.match(head, /pays off when you change your mind/);
  });

  // @spec MKT-SITE-107, MKT-SITE-103
  it("follows one change through four cards", () => {
    const c = cards(section("change"));
    assert.equal(c.length, 4);
    assert.match(c[0], /<div class="bubble">[\s\S]*End trials at midnight in each user's own time zone\./);
    assert.match(text(c[1]), /still hold/);
    assert.match(c[2], /<ol class="drafts">/);
    assert.match(text(c[3]), /TRIAL-003/);
  });

  // @spec MKT-SITE-108
  it("shows the drafts as numbered options, with the reasons below", () => {
    const card = cards(section("change"))[2];
    const options = [...card.match(/<ol class="drafts">([\s\S]*?)<\/ol>/)[1].matchAll(/<li class="draft[^"]*"[^>]*>([\s\S]*?)<\/li>/g)].map((m) => text(m[1]));
    assert.equal(options.length, 2);
    assert.match(options[0], /midnight on day 30, in the user's time zone\.$/);
    assert.match(options[1], /first midnight, in the user's time zone, after 720 hours\.$/);
    for (const option of options) assert.doesNotMatch(option, /tenet|approve/i, "the options hold only the drafts");
    const why = text(card.match(/<p class="why">[\s\S]*?<\/p>/)[0]);
    assert.match(why, /tenet rules it out/);
    assert.match(why, /approve/);
  });

  // @spec MKT-SITE-109
  it("changes only TRIAL-003", () => {
    const last = text(cards(section("change"))[3]);
    assert.match(last, /TRIAL-003: When the user's local time first reaches midnight after 720 hours from signup, the system shall end the trial\./);
    assert.match(last, /TRIAL-001 and TRIAL-002 still hold/);
  });

  // @spec MKT-SITE-110, MKT-SITE-003
  it("plays the recording after the change explainer's cards", () => {
    const change = section("change");
    const steps = change.lastIndexOf("<!-- /step -->");
    const recording = change.indexOf("asciinema.org/a/");
    assert.ok(steps > 0 && recording > steps);
    assert.match(text(change.slice(steps)), /Watch it happen in a real project/);
  });

  // @spec MKT-SITE-112
  it("keeps each explainer's drawing in view", () => {
    assert.match(rule(".scrolly-fig"), /position:\s*sticky/);
    assert.match(css, /@media \(min-width: 900px\) \{\s*\.scrolly \{[^}]*grid-template-columns/);
  });

  // @spec MKT-SITE-116, MKT-SITE-117
  it("reads in full and shows finished drawings without JavaScript", () => {
    for (const id of ["narrowing", "change"]) {
      const s = section(id);
      const svg = s.match(/<svg[^>]*class="rings-svg"[\s\S]*?<\/svg>/);
      assert.ok(svg, `${id} has a static drawing`);
      assert.match(svg[0], /<title[^>]*>[^<]+<\/title>/);
      assert.match(svg[0], /<desc[^>]*>[^<]+<\/desc>/);
      assert.match(svg[0], /class="code"/);
      for (const card of cards(s)) assert.doesNotMatch(card, /\shidden[\s>=]|display:\s*none/);
    }
    assert.match(section("change").match(/<svg[^>]*class="rings-svg"[\s\S]*?<\/svg>/)[0], /draft|TRIAL-003/);
  });

  // @spec MKT-SITE-045, MKT-SITE-056
  it("shows one search finding the requirement, the test, and the code", () => {
    const check = section("check");
    const grep = text(check.match(/<pre class="grep">[\s\S]*?<\/pre>/)[0]);
    assert.match(grep, /grep -r TRIAL-003/);
    for (const path of ["docs/intent/trial/trial-specs.md", "tests/trial.test.ts", "src/trial.ts"]) assert.ok(grep.includes(path), path);
    assert.match(text(check), /reviewer/);
  });

  // @spec MKT-SITE-055
  it("keeps the verification claim bounded", () => {
    const claim = text(section("check"));
    assert.match(claim, /mechanical/);
    assert.match(claim, /CI/);
    assert.match(claim, /what you mean/);
    assert.doesNotMatch(claim, /just a walk/);
  });

  // @spec MKT-SITE-038, MKT-SITE-042, MKT-SITE-043, MKT-SITE-061
  it("scales one feature's links up to the whole codebase", () => {
    const check = section("check");
    const dag = check.match(/<svg class="dag"[\s\S]*?<\/svg>/);
    assert.ok(dag, "the check section has the DAG");
    const edges = [...dag[0].matchAll(/<path class="dag-edge[^"]*"[^>]*>/g)].map((m) => m[0]);
    assert.ok(edges.length > 10);
    for (const edge of edges) assert.match(edge, /marker-end="url\(#dag-/);
    assert.ok(edges.filter((edge) => edge.includes("dag-edge-cross")).length >= 2);
    assert.match(text(check), /what LID calls an arrow/);
  });

  // @spec MKT-SITE-046, MKT-SITE-057, MKT-SITE-062, MKT-SITE-063, MKT-SITE-070
  it("says where your time goes, and the price", () => {
    const time = text(section("time"));
    assert.match(section("time"), /<h2[^>]*>Your time goes into the design\.<\/h2>/);
    assert.match(time, /HLD/);
    assert.match(time, /bug fix/);
    assert.match(time, /editable/);
    assert.match(time, /audit/);
    assert.match(time, /The price/);
    assert.match(time, /tokens/);
  });

  // @spec MKT-SITE-069
  it("keeps the one first-person sentence beside the price", () => {
    const time = section("time");
    assert.ok(time.includes('href="https://github.com/jszmajda/portfolio-tracker"'));
    const firstPerson = (page) => text(page.match(/<main[\s\S]*<\/main>/)[0]).split(/(?<=[.!?])\s+/).filter((s) => /\bI\b/.test(s)).length;
    assert.equal(firstPerson(html.Home), 1);
    // The Start page's path headings ("I'm evaluating.") are the reader's voice, which the design doc allows.
    for (const name of ["Examples", "Anti-patterns"]) assert.equal(firstPerson(html[name]), 0, name);
  });

  // @spec MKT-SITE-022
  it("asks for nothing beyond install and use", () => {
    for (const page of Object.values(html)) {
      const main = page.match(/<main[\s\S]*<\/main>/)[0];
      assert.doesNotMatch(main, /<form|newsletter|subscribe|sign up for/i);
      for (const m of main.matchAll(/class="btn btn-go"[^>]*href="([^"]+)"/g)) assert.match(m[1], /#quickstart$/);
    }
  });

  // @spec MKT-SITE-050
  it("surfaces the experimental plugin as opt-in, outside the core install", () => {
    const experimental = section("experimental");
    assert.match(experimental, /lid-experimental/);
    assert.match(experimental, /\/plugin install lid-experimental@jszmajda-lid/);
    assert.match(experimental, /plugins\/lid-experimental\/README\.md/);
    assert.doesNotMatch(section("quickstart"), /lid-experimental/);
  });

  // @spec MKT-SITE-068
  it("states a claim in each persuasive heading", () => {
    const h2 = (id) => text(section(id).match(/<h2[^>]*>([\s\S]*?)<\/h2>/)[1]);
    assert.equal(h2("gap"), "A short request leaves the decisions to your agent.");
    assert.equal(h2("narrowing"), "Each level you write down rules out what you didn't mean.");
    assert.equal(h2("change"), "Change your mind in one place, and the agent carries it down.");
    assert.equal(h2("check"), "One search finds everything built from a line.");
    assert.equal(h2("time"), "Your time goes into the design.");
    assert.equal(h2("teams"), "Alignment is a pull request.");
  });

  // @spec MKT-SITE-006, MKT-SITE-008, MKT-SITE-040, MKT-SITE-004
  it("keeps the Quickstart in step with the README", () => {
    const readme = readFileSync(join(siteDir, "..", "README.md"), "utf8");
    const commands = [...section("quickstart").matchAll(/<code>(\/[^<]+)<\/code>/g)].map((m) => m[1]);
    assert.equal(commands.length, 4);
    for (const command of commands) assert.ok(readme.includes(command), command);
    assert.match(section("hero"), /href="#quickstart"/);
  });
});
