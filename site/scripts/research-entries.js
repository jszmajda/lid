// Reads and checks the research section's entries in site/src/research/. Any broken rule throws,
// so the site's build fails with a message naming the entry and the rule.
// @spec ONB-RESEARCH-040, ONB-RESEARCH-041, ONB-RESEARCH-050
import { existsSync, readdirSync, readFileSync, statSync } from "node:fs";
import { extname, join } from "node:path";
import matter from "gray-matter";
import markdownIt from "markdown-it";

export const STATUS_LABELS = { pilot: "Pilot results", counted: "Counted results", superseded: "Superseded" };
const FIELDS = ["title", "date", "revised", "status", "superseded_by", "summary", "tested", "records"];
const REQUIRED = ["title", "date", "status", "summary", "tested", "records"];
const TESTED = ["lid", "agent", "model"];
const IMAGE_TYPES = [".png", ".jpg", ".jpeg", ".svg"];
const MAX_IMAGE = 2_000_000;
const SUMMARY_MAX = 300;

class ReportError extends Error {}
const fail = (slug, rule) => {
  throw new ReportError(`research/${slug}: ${rule}`);
};
const isHttps = (v) => typeof v === "string" && /^https:\/\/[^\s/?#]+/.test(v);
const hasText = (v) => typeof v === "string" && v.trim() !== "";
const bareName = (v) => /^[A-Za-z0-9._-]+$/.test(v) && v !== "." && v !== "..";
const escapeHtml = (s) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");

// Parses with HTML recognised, so raw HTML shows up as tokens the rules can reject.
const parser = markdownIt({ html: true, linkify: true });

const todayUtc = () => new Date().toISOString().slice(0, 10);

// A date as written in the file, quoted or not. It is read from the front matter's own text,
// because YAML turns an unquoted date into a Date and rolls an impossible one (2026-02-30) on.
// @spec ONB-RESEARCH-054
function readDate(slug, field, value, today, raw) {
  const written = raw.match(new RegExp(`^${field}:\\s*["']?([^"'\\s#]*)["']?\\s*(?:#.*)?$`, "m"));
  const text = written ? written[1] : value instanceof Date ? value.toISOString().slice(0, 10) : String(value);
  const m = text.match(/^(\d{4})-(\d{2})-(\d{2})$/);
  const real = m && (() => {
    const d = new Date(Date.UTC(+m[1], +m[2] - 1, +m[3]));
    return d.getUTCFullYear() === +m[1] && d.getUTCMonth() === +m[2] - 1 && d.getUTCDate() === +m[3];
  })();
  if (!real) fail(slug, `\`${field}\` must be a real calendar date written YYYY-MM-DD`);
  if (text > today) fail(slug, `\`${field}\` is later than the day of the build (${today}, UTC)`);
  return text;
}

// @spec ONB-RESEARCH-063, ONB-RESEARCH-064, ONB-RESEARCH-065
function checkBody(slug, body, folderFiles) {
  if (!hasText(body)) fail(slug, "the report body is empty");
  const referenced = new Set();
  const checkTarget = (target, kind) => {
    if (isHttps(target) || target.startsWith("#") || /^mailto:\S+/.test(target)) return;
    if (bareName(target) && IMAGE_TYPES.includes(extname(target)) && folderFiles.includes(target)) {
      referenced.add(target);
      return;
    }
    fail(slug, `${kind} \`${target}\` must be an https URL, an anchor, a mailto address, or the bare file name of an image in the entry's folder`);
  };
  const walk = (tokens) => {
    for (const t of tokens) {
      if (t.type === "heading_open" && t.tag === "h1") fail(slug, "the report body has a level-1 heading (h1); its headings start at h2");
      if (t.type === "html_block" || t.type === "html_inline") fail(slug, "the report body contains raw HTML");
      if (t.type === "link_open") checkTarget(t.attrGet("href"), "the link");
      if (t.type === "image") checkTarget(t.attrGet("src"), "the image");
      if (t.children) walk(t.children);
    }
  };
  walk(parser.parse(body, {}));
  return referenced;
}

// @spec ONB-RESEARCH-068
function checkSvg(slug, name, text, folderFiles) {
  const bad = (why) => fail(slug, `the SVG ${name} ${why}`);
  if (/<\s*script\b/i.test(text)) bad("contains a script element");
  if (/<\s*foreignObject\b/i.test(text)) bad("contains a foreignObject element");
  if (/\son[a-z]+\s*=/i.test(text)) bad("has an event-handler attribute");
  const refs = [...text.matchAll(/\s(?:xlink:href|href|src)\s*=\s*["']([^"']*)["']/gi)].map((m) => m[1]);
  refs.push(...[...text.matchAll(/url\(\s*["']?([^"')]*)["']?\s*\)/gi)].map((m) => m[1]));
  for (const ref of refs) {
    if (ref.startsWith("#")) continue;
    if (bareName(ref) && ref !== name && folderFiles.includes(ref)) continue;
    bad(`refers to \`${ref}\`, outside its own folder`);
  }
}

function readEntry(dir, slug, today) {
  // @spec ONB-RESEARCH-051
  if (!/^[a-z0-9-]+$/.test(slug)) fail(slug, "the slug must be lowercase letters, digits, and hyphens");
  const folder = join(dir, slug);
  const indexPath = join(folder, "index.md");
  if (!existsSync(indexPath)) fail(slug, "the entry has no index.md");
  const parsed = matter(readFileSync(indexPath, "utf8"));
  const { data, content } = parsed;
  const raw = parsed.matter || "";

  // @spec ONB-RESEARCH-052, ONB-RESEARCH-053
  for (const key of Object.keys(data)) if (!FIELDS.includes(key)) fail(slug, `unknown field \`${key}\``);
  for (const key of REQUIRED) if (data[key] === undefined || data[key] === null) fail(slug, `missing required field \`${key}\``);
  if (!hasText(data.title)) fail(slug, "`title` must be a string with text in it");
  if (!hasText(data.summary)) fail(slug, "`summary` must be a string with text in it");

  // @spec ONB-RESEARCH-054, ONB-RESEARCH-055
  const date = readDate(slug, "date", data.date, today, raw);
  let revised = null;
  if (data.revised !== undefined) {
    revised = readDate(slug, "revised", data.revised, today, raw);
    if (revised <= date) fail(slug, "`revised` must be later than `date`");
  }

  // @spec ONB-RESEARCH-056, ONB-RESEARCH-058
  if (!(data.status in STATUS_LABELS)) fail(slug, "`status` must be pilot, counted, or superseded");
  if (data.status !== "superseded" && data.superseded_by !== undefined) fail(slug, "only a superseded entry may have `superseded_by`");
  if (data.status === "superseded" && !hasText(data.superseded_by)) fail(slug, "a superseded entry needs `superseded_by`");

  // @spec ONB-RESEARCH-059
  const tested = data.tested;
  if (!tested || typeof tested !== "object" || Array.isArray(tested)) fail(slug, "`tested` must give lid, agent, and model");
  const keys = Object.keys(tested);
  if (keys.length !== TESTED.length || !TESTED.every((k) => keys.includes(k)) || !TESTED.every((k) => hasText(tested[k]))) {
    fail(slug, "`tested` must give exactly lid, agent, and model, each with text in it");
  }

  // @spec ONB-RESEARCH-060
  const summary = data.summary;
  if ([...summary].length > SUMMARY_MAX) fail(slug, `\`summary\` is longer than ${SUMMARY_MAX} characters`);
  if (parser.renderInline(summary) !== escapeHtml(summary)) fail(slug, "`summary` must be plain text, with no Markdown");

  // @spec ONB-RESEARCH-061
  if (!isHttps(data.records)) fail(slug, "`records` must be an https URL");

  // @spec ONB-RESEARCH-066, ONB-RESEARCH-067
  const folderFiles = readdirSync(folder).filter((f) => f !== "index.md");
  const referenced = checkBody(slug, content, folderFiles);
  for (const f of folderFiles) {
    if (!IMAGE_TYPES.includes(extname(f))) fail(slug, `${f} is not an image the entry may hold (.png, .jpg, .jpeg, or .svg, in lowercase)`);
    if (statSync(join(folder, f)).size > MAX_IMAGE) fail(slug, `${f} is larger than 2,000,000 bytes`);
    if (!referenced.has(f)) fail(slug, `${f} is not referenced by the report`);
    if (extname(f) === ".svg") checkSvg(slug, f, readFileSync(join(folder, f), "utf8"), folderFiles);
  }

  return {
    slug,
    title: data.title,
    date,
    revised,
    status: data.status,
    statusLabel: STATUS_LABELS[data.status],
    superseded_by: data.superseded_by || null,
    summary,
    tested: { lid: tested.lid, agent: tested.agent, model: tested.model },
    records: data.records,
    body: content,
    images: [...referenced],
  };
}

export function loadReports(dir, { today = todayUtc() } = {}) {
  if (!existsSync(dir)) return [];
  const list = [];
  for (const name of readdirSync(dir)) {
    if (name.startsWith("_") || name.startsWith(".")) continue;
    // @spec ONB-RESEARCH-069
    if (!statSync(join(dir, name)).isDirectory()) fail(name, `${name} sits directly in the research folder, outside any entry`);
    list.push(readEntry(dir, name, today));
  }
  // @spec ONB-RESEARCH-057, ONB-RESEARCH-022
  const bySlug = new Map(list.map((e) => [e.slug, e]));
  for (const e of list) {
    e.replaces = [];
    if (e.status !== "superseded") continue;
    const target = bySlug.get(e.superseded_by);
    if (!target || target === e || target.status === "superseded") {
      fail(e.slug, "`superseded_by` must give the slug of another existing entry that is not itself superseded");
    }
    e.supersededBy = { slug: target.slug, title: target.title };
  }
  for (const e of list) if (e.supersededBy) bySlug.get(e.supersededBy.slug).replaces.push({ slug: e.slug, title: e.title });
  // @spec ONB-RESEARCH-004
  return list.sort((a, b) => (a.date === b.date ? (a.slug < b.slug ? -1 : a.slug > b.slug ? 1 : 0) : a.date < b.date ? 1 : -1));
}
