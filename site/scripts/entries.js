// Reads and checks the showcase's entries in site/src/examples/. Any broken rule throws, so the
// site's build fails with a message naming the entry and the rule.
// @spec ONB-SHOWCASE-052, ONB-SHOWCASE-053
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { join } from "node:path";
import matter from "gray-matter";
import { drawTree, sizeName } from "./tree-svg.js";

const FIELDS = ["project", "owner", "tagline", "date", "open_source", "pictures", "stats", "stats_source", "spec_count", "story", "links"];
const REQUIRED = ["project", "owner", "tagline", "date", "open_source"];
const LINKS = ["repo", "hld", "intent_tree", "live"];
const STORY_FIELDS = ["title", "author", "byline", "file", "url"];
const STORY_FILES = ["story.md", "story.html"];
const MAX_PICTURE = 2_000_000;

class EntryError extends Error {}
const fail = (slug, rule) => {
  throw new EntryError(`examples/${slug}: ${rule}`);
};
const isHttps = (v) => typeof v === "string" && /^https:\/\/[^\s/]+/.test(v);

// Parses the tree file's YAML: nested `children` lists of nodes with name, specs, and built.
export function parseTreeYaml(text) {
  const lines = text
    .split("\n")
    .map((raw) => raw.replace(/\s+#.*$/, ""))
    .filter((l) => l.trim() && !l.trim().startsWith("#"))
    .map((l) => ({ indent: l.length - l.trimStart().length, text: l.trim() }));
  let i = 0;
  const scalar = (v) => (/^-?\d+(\.\d+)?$/.test(v) ? Number(v) : v.replace(/^(["'])(.*)\1$/, "$2"));
  // Reads `key: value` pairs (and nested `children:` lists) at one indent into an object.
  const readMap = (indent, obj) => {
    while (i < lines.length && lines[i].indent === indent && !lines[i].text.startsWith("- ")) {
      const m = lines[i].text.match(/^([A-Za-z_]+):\s*(.*)$/);
      if (!m) throw new Error(`cannot read line "${lines[i].text}"`);
      i += 1;
      if (m[2] === "" || m[2] === "[]") obj[m[1]] = m[2] === "[]" ? [] : readList();
      else obj[m[1]] = scalar(m[2]);
    }
    return obj;
  };
  const readList = () => {
    const list = [];
    if (i >= lines.length || !lines[i].text.startsWith("- ")) return list;
    const indent = lines[i].indent;
    while (i < lines.length && lines[i].indent === indent && lines[i].text.startsWith("- ")) {
      const first = lines[i].text.slice(2).trim();
      const node = {};
      if (first !== "{}") {
        lines[i] = { indent: indent + 2, text: first };
        readMap(indent + 2, node);
      } else {
        i += 1;
      }
      list.push(node);
    }
    return list;
  };
  const doc = readMap(0, {});
  if (i < lines.length) throw new Error(`cannot read line "${lines[i].text}"`);
  return doc;
}

// @spec ONB-SHOWCASE-067, ONB-SHOWCASE-068, ONB-SHOWCASE-069
function checkTree(slug, tree) {
  if (!tree || !Array.isArray(tree.children) || !tree.children.length) fail(slug, "tree.yaml needs a non-empty `children` list");
  const check = (n) => {
    const keys = Object.keys(n);
    const bad = keys.find((k) => !["name", "children", "specs", "built"].includes(k));
    if (bad) fail(slug, `tree.yaml node has an unknown field \`${bad}\``);
    if (n.children !== undefined) {
      if (!Array.isArray(n.children) || !n.children.length) fail(slug, "tree.yaml sub-HLD needs a non-empty `children` list");
      if (n.specs !== undefined || n.built !== undefined) fail(slug, "tree.yaml node has both `children` and counts");
      n.children.forEach(check);
    } else if (n.specs !== undefined || n.built !== undefined) {
      if (n.specs === undefined || n.built === undefined) fail(slug, "tree.yaml leaf needs both `specs` and `built`, or neither");
      if (!Number.isInteger(n.specs) || !Number.isInteger(n.built) || n.specs < 0 || n.built < 0) fail(slug, "tree.yaml counts must be whole numbers");
      if (n.built > n.specs) fail(slug, "tree.yaml leaf has `built` greater than `specs`");
    }
    if (n.name !== undefined) n.name = String(n.name);
  };
  tree.children.forEach(check);
}

// @spec ONB-SHOWCASE-065, ONB-SHOWCASE-090
function checkStoryHtml(slug, html) {
  if (!/<body[\s>]/i.test(html)) fail(slug, "story.html needs a <body> element");
  if (/<script[\s>]/i.test(html)) fail(slug, "story.html may not contain a <script> element");
  const outside = [
    ...html.matchAll(/<(?:img|link|iframe|frame|source|video|audio|embed|object|track|image|use)\b[^>]*?\s(?:src|href|srcset|data|poster|xlink:href)\s*=\s*["']?((?:https?:)?\/\/[^"'\s>]+)/gi),
    ...html.matchAll(/url\(\s*["']?((?:https?:)?\/\/[^"')\s]+)/gi),
    ...html.matchAll(/@import\s+["']((?:https?:)?\/\/[^"']+)/gi),
  ];
  if (outside.length) fail(slug, `story.html loads a resource from outside its folder: ${outside[0][1]}`);
}

function readEntry(dir, slug) {
  // @spec ONB-SHOWCASE-054
  if (!/^[a-z0-9-]+$/.test(slug)) fail(slug, "a folder name must be lowercase letters, digits, and hyphens");
  const folder = join(dir, slug);
  const indexPath = join(folder, "index.md");
  if (!existsSync(indexPath)) fail(slug, "index.md is missing");
  const { data, content } = matter(readFileSync(indexPath, "utf8"));

  // @spec ONB-SHOWCASE-055, ONB-SHOWCASE-056
  const unknown = Object.keys(data).find((k) => !FIELDS.includes(k));
  if (unknown) fail(slug, `unknown field \`${unknown}\``);
  for (const k of REQUIRED) if (data[k] === undefined || data[k] === null || data[k] === "") fail(slug, `missing required field \`${k}\``);
  const date = data.date instanceof Date ? data.date.toISOString().slice(0, 10) : String(data.date);
  if (!/^\d{4}-\d{2}-\d{2}$/.test(date) || Number.isNaN(Date.parse(date))) fail(slug, "`date` must be an ISO date (YYYY-MM-DD)");
  if (typeof data.open_source !== "boolean") fail(slug, "`open_source` must be true or false");

  // @spec ONB-SHOWCASE-058
  const pictures = data.pictures || [];
  if (!Array.isArray(pictures)) fail(slug, "`pictures` must be a list");
  for (const p of pictures) {
    if (!p || typeof p.file !== "string") fail(slug, "each picture needs a `file`");
    if (!/\.(png|jpe?g)$/i.test(p.file) || p.file.includes("/")) fail(slug, `picture ${p.file} must be a .png, .jpg, or .jpeg file in the entry's folder`);
    if (!existsSync(join(folder, p.file))) fail(slug, `picture ${p.file} is missing`);
    if (statSync(join(folder, p.file)).size > MAX_PICTURE) fail(slug, `picture ${p.file} is larger than 2,000,000 bytes`);
    if (typeof p.alt !== "string" || !p.alt.trim()) fail(slug, `picture ${p.file} needs non-empty \`alt\` text`);
  }

  // @spec ONB-SHOWCASE-059
  const stats = data.stats || [];
  if (!Array.isArray(stats) || !stats.every((s) => Array.isArray(s) && s.length === 2 && s.every((v) => typeof v === "string"))) fail(slug, "`stats` must be a list of [label, value] pairs of strings");

  // @spec ONB-SHOWCASE-060, ONB-SHOWCASE-061
  const links = data.links || {};
  for (const [k, v] of Object.entries(links)) {
    if (!LINKS.includes(k)) fail(slug, `unknown link \`${k}\``);
    if (!isHttps(v)) fail(slug, `link \`${k}\` must be an https URL`);
  }
  if (!data.open_source) for (const k of ["repo", "hld", "intent_tree"]) if (links[k]) fail(slug, `a private entry may not link its \`${k}\``);

  // @spec ONB-SHOWCASE-062, ONB-SHOWCASE-063, ONB-SHOWCASE-064, ONB-SHOWCASE-015
  let story = null;
  if (data.story) {
    const s = data.story;
    const extra = Object.keys(s).find((k) => !STORY_FIELDS.includes(k));
    if (extra) fail(slug, `unknown story field \`${extra}\``);
    if (typeof s.title !== "string" || !s.title.trim()) fail(slug, "`story` needs a `title`");
    if (s.file && s.url) fail(slug, "`story` may name a `file` or a `url`, not both");
    if (s.file !== undefined && !STORY_FILES.includes(s.file)) fail(slug, "`story.file` must be story.md or story.html");
    if (s.file && !existsSync(join(folder, s.file))) fail(slug, `${s.file} is missing`);
    if (s.url !== undefined && !isHttps(s.url)) fail(slug, "`story.url` must be an https URL");
    const author = s.author || data.owner;
    story = { title: s.title, author, byline: s.byline || `by ${author}`, file: s.file || null, url: s.url || null };
  }
  for (const f of STORY_FILES) if (existsSync(join(folder, f)) && (!story || story.file !== f)) fail(slug, `${f} is in the folder but the entry does not name it`);
  if (story && story.file === "story.md" && /^---\s*\n/.test(readFileSync(join(folder, "story.md"), "utf8"))) fail(slug, "story.md may not have front matter");
  if (story && story.file === "story.html") checkStoryHtml(slug, readFileSync(join(folder, "story.html"), "utf8"));

  // @spec ONB-SHOWCASE-057
  let tree = null;
  if (existsSync(join(folder, "tree.yaml"))) {
    try {
      tree = parseTreeYaml(readFileSync(join(folder, "tree.yaml"), "utf8"));
    } catch (e) {
      fail(slug, `tree.yaml cannot be read: ${e.message}`);
    }
    checkTree(slug, tree);
  }
  if (!pictures.length && !tree) fail(slug, "an entry needs at least one picture or a tree file");

  if (data.spec_count !== undefined && !(Number.isInteger(data.spec_count) && data.spec_count >= 0)) fail(slug, "`spec_count` must be a whole number");
  const drawing = tree ? drawTree(tree) : null;
  // @spec ONB-SHOWCASE-050, ONB-SHOWCASE-051
  const total = drawing && drawing.counted ? drawing.total : data.spec_count;
  // @spec ONB-SHOWCASE-013, ONB-SHOWCASE-014
  const credit = `${data.owner}'s project` + (story && story.author !== data.owner ? ` · post written by ${story.author}` : "");

  return {
    slug,
    project: String(data.project),
    owner: String(data.owner),
    tagline: String(data.tagline),
    date,
    open_source: data.open_source,
    pictures,
    stats,
    stats_source: data.stats_source || null,
    links,
    story,
    tree,
    drawing,
    size: total === undefined || total === null ? null : sizeName(total),
    credit,
    brief: content.trim(),
  };
}

// Loads every entry in `dir`, newest first, ties broken by slug.
// @spec ONB-SHOWCASE-003
export function loadEntries(dir) {
  if (!existsSync(dir)) return [];
  const slugs = readdirSync(dir).filter((name) => !name.startsWith("_") && !name.startsWith(".") && statSync(join(dir, name)).isDirectory());
  const list = slugs.map((slug) => readEntry(dir, slug));
  return list.sort((a, b) => (a.date === b.date ? (a.slug < b.slug ? -1 : 1) : a.date < b.date ? 1 : -1));
}
