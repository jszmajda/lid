// The examples showcase's data: every entry in src/examples/, and the two reference trees
// measured from the repository at build time.
// @spec ONB-SHOWCASE-009, ONB-SHOWCASE-010, ONB-SHOWCASE-025, ONB-SHOWCASE-026
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import { loadEntries } from "../../scripts/entries.js";
import { measureTree } from "../../scripts/intent-tree.js";
import { drawTree, sizeName } from "../../scripts/tree-svg.js";

const srcDir = join(dirname(fileURLToPath(import.meta.url)), "..");
const repoDir = join(srcDir, "..", "..");
const repoUrl = "https://github.com/jszmajda/lid";
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// The thin bar a hosted story.html gets as its body's first child. Inline styles only, and no
// nested <div>, so the author's page and the bar keep apart.
function storyBar(entry) {
  const link = `<a href="/examples/${entry.slug}/" style="color:#FF9A76;text-decoration:none;font-weight:600">&larr; ${esc(entry.project)} on the LID site</a>`;
  const who = `<span style="opacity:.75">${esc(entry.owner)}&rsquo;s project &middot; story by ${esc(entry.story.author)}</span>`;
  return `<div data-lid-story-bar style="position:sticky;top:0;z-index:2147483647;display:flex;flex-wrap:wrap;gap:6px 16px;align-items:center;margin:0;padding:10px 18px;background:#14100D;color:#F4EDE8;font:500 14px/1.4 system-ui,-apple-system,sans-serif">${link}${who}</div>`;
}

function withStory(entry) {
  if (entry.story && entry.story.file === "story.md") return { ...entry, storyMarkdown: readFileSync(join(srcDir, "examples", entry.slug, "story.md"), "utf8") };
  if (!entry.story || entry.story.file !== "story.html") return entry;
  const source = readFileSync(join(srcDir, "examples", entry.slug, "story.html"), "utf8");
  const storyHtml = source.replace(/<body\b[^>]*>/i, (tag) => tag + storyBar(entry));
  return { ...entry, storyHtml };
}

function reference(title, sentence, designDir, href) {
  const tree = measureTree(join(repoDir, designDir));
  const drawing = drawTree(tree);
  return { title, sentence, href, drawing, total: drawing.total, docs: drawing.docs, size: sizeName(drawing.total) };
}

export default function () {
  const entries = loadEntries(join(srcDir, "examples")).map(withStory);
  return {
    entries,
    featured: entries[0] || null,
    rest: entries.slice(1),
    mdStories: entries.filter((e) => e.story && e.story.file === "story.md"),
    htmlStories: entries.filter((e) => e.story && e.story.file === "story.html"),
    references: [
      reference(
        "URL shortener",
        "Intent only: a design and its requirements, with no code at all. Hand it to a fresh agent and see what it builds.",
        "examples/urlshort/docs/specs",
        `${repoUrl}/tree/main/examples/urlshort`,
      ),
      reference(
        "LID itself",
        "This repository is designed with the method it ships: its plugins, this site, and the tools that check them.",
        "docs/intent",
        `${repoUrl}/tree/main/docs/intent`,
      ),
    ],
  };
}
