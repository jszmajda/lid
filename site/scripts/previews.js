// Link-preview metadata: the tags every page carries, one renderer for the site's layout and for
// hosted HTML stories, and the pixel size of a PNG or JPEG.
// @spec ONB-SITE-135, ONB-SITE-136, ONB-SITE-137

export const SITE_NAME = "Linked-Intent Development";
export const DEFAULT_CARD = { path: "/assets/social-card.png", width: 1200, height: 630, alt: "LID: How do you know your agent built what you meant? linked-intent.dev" };

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

// The tags in the order they are written: [key, html]. `key` names the tag for the "already has it" check.
function tagList(t) {
  const meta = (attr, key, value) => [key, `<meta ${attr}="${key}" content="${esc(value)}" />`];
  return [
    ["canonical", `<link rel="canonical" href="${esc(t.url)}" />`],
    meta("property", "og:title", t.title),
    meta("property", "og:description", t.description),
    meta("property", "og:type", t.type || "website"),
    meta("property", "og:site_name", SITE_NAME),
    meta("property", "og:url", t.url),
    meta("property", "og:image", t.image),
    meta("property", "og:image:alt", t.imageAlt),
    meta("property", "og:image:width", t.imageWidth),
    meta("property", "og:image:height", t.imageHeight),
    meta("name", "twitter:card", "summary_large_image"),
  ];
}

export function renderPreviewTags(t) {
  return tagList(t).map(([, html]) => html).join("\n    ");
}

// Adds to a page's <head> each preview tag it lacks, leaving the author's own untouched.
// @spec ONB-SHOWCASE-095
export function addPreviewTags(html, t) {
  const head = html.match(/<head\b[^>]*>[\s\S]*?<\/head>/i);
  if (!head) return html;
  const has = (key) =>
    key === "canonical"
      ? /<link\b[^>]*\brel=["']?canonical\b/i.test(head[0])
      : new RegExp(`<meta\\b[^>]*\\b(?:property|name)=["']?${key.replace(/[.:]/g, "\\$&")}["'\\s>]`, "i").test(head[0]);
  const missing = tagList(t).filter(([key]) => !has(key)).map(([, tag]) => tag);
  if (!missing.length) return html;
  const block = `<!-- lid:preview -->${missing.join("")}<!-- /lid:preview -->`;
  const closeAt = head.index + head[0].length - "</head>".length;
  return html.slice(0, closeAt) + block + html.slice(closeAt);
}

// Reads a PNG's or JPEG's pixel size from its header. @spec ONB-SHOWCASE-094
export function imageSize(buf) {
  if (buf.length > 24 && buf.readUInt32BE(0) === 0x89504e47) return { width: buf.readUInt32BE(16), height: buf.readUInt32BE(20) };
  if (buf[0] === 0xff && buf[1] === 0xd8) {
    let i = 2;
    while (i + 9 < buf.length) {
      if (buf[i] !== 0xff) return null;
      const marker = buf[i + 1];
      const len = buf.readUInt16BE(i + 2);
      if (marker >= 0xc0 && marker <= 0xcf && ![0xc4, 0xc8, 0xcc].includes(marker)) return { width: buf.readUInt16BE(i + 7), height: buf.readUInt16BE(i + 5) };
      i += 2 + len;
    }
  }
  return null;
}
