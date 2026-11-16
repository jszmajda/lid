import eleventyNavigationPlugin from "@11ty/eleventy-navigation";
import { cpSync, mkdirSync, readdirSync } from "node:fs";
import { join } from "node:path";
import markdownIt from "markdown-it";
import { loadEntries } from "./scripts/entries.js";

// Light syntax coloring for the Tour page's fenced code: diff lines in red and
// green, and comments, strings, keywords, and numbers in TypeScript. Returning
// an empty string hands any other language back to markdown-it's own escaping.
// @spec ONB-SITE-075
function escapeHtml(text) {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

function highlight(code, lang) {
  if (lang === "diff") {
    return code
      .split("\n")
      .map((line) => {
        const html = escapeHtml(line);
        if (line.startsWith("+")) return `<span class="hl-add">${html}</span>`;
        if (line.startsWith("-")) return `<span class="hl-del">${html}</span>`;
        return html;
      })
      .join("\n");
  }
  if (["ts", "typescript", "js", "javascript"].includes(lang)) {
    const token =
      /(\/\/[^\n]*)|("(?:[^"\\\n]|\\.)*"|'(?:[^'\\\n]|\\.)*'|`(?:[^`\\]|\\.)*`)|\b(const|let|var|function|return|export|import|from|if|else|new|type|interface|true|false|null|undefined|it|expect)\b|\b(\d+(?:\.\d+)?)\b/g;
    let html = "";
    let last = 0;
    let match;
    while ((match = token.exec(code))) {
      html += escapeHtml(code.slice(last, match.index));
      const kind = match[1] ? "comment" : match[2] ? "string" : match[3] ? "keyword" : "number";
      html += `<span class="hl-${kind}">${escapeHtml(match[0])}</span>`;
      last = token.lastIndex;
    }
    return html + escapeHtml(code.slice(last));
  }
  return "";
}

const markdown = markdownIt({ html: true, linkify: true, highlight });

export default function (eleventyConfig) {
  eleventyConfig.addPlugin(eleventyNavigationPlugin);

  // The showcase's entries are data, read by src/_data/examples.js, never pages of their own.
  // After each build, each entry's pictures are copied beside its page, and a hosted
  // story.html's other files beside the story, so its relative links resolve.
  // @spec ONB-SHOWCASE-027, ONB-SHOWCASE-052, ONB-SHOWCASE-066, ONB-SHOWCASE-092
  eleventyConfig.ignores.add("src/examples/**");
  eleventyConfig.addWatchTarget("src/examples/");
  eleventyConfig.on("eleventy.after", ({ directories, dir }) => {
    const output = (directories || dir).output;
    const examplesDir = join("src", "examples");
    for (const entry of loadEntries(examplesDir)) {
      const from = join(examplesDir, entry.slug);
      const to = join(output, "examples", entry.slug);
      mkdirSync(to, { recursive: true });
      for (const pic of entry.pictures) cpSync(join(from, pic.file), join(to, pic.file));
      if (entry.story && entry.story.file === "story.html") {
        for (const f of readdirSync(from)) {
          if (["index.md", "tree.yaml", "story.html"].includes(f)) continue;
          cpSync(join(from, f), join(to, "story", f), { recursive: true });
        }
      }
    }
  });

  // Pass through static assets untouched.
  eleventyConfig.addPassthroughCopy("src/assets");
  eleventyConfig.addPassthroughCopy({ "src/robots.txt": "robots.txt" });
  // CNAME tells GitHub Pages which custom domain to serve. Must land at the
  // root of the build output.
  eleventyConfig.addPassthroughCopy({ "src/CNAME": "CNAME" });

  // Watch CSS for reload.
  eleventyConfig.addWatchTarget("src/assets/css/");

  // Date filter for footer year.
  eleventyConfig.addFilter("year", () => new Date().getFullYear());

  // Showcase helpers: a readable date, thousands separators, and a URL's host name.
  eleventyConfig.addFilter("showcaseDate", (iso) => new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" }));
  eleventyConfig.addFilter("commas", (n) => Number(n).toLocaleString("en-US"));
  eleventyConfig.addFilter("host", (url) => new URL(url).host);

  // Renders Markdown read from the tour's files (see src/_data/tour.js).
  eleventyConfig.addFilter("markdown", (text) => markdown.render(text || ""));

  // Build-time timestamp for cache-busting static asset URLs. Every build
  // gets a new value, so references like `/assets/css/main.css?v={{ buildId }}`
  // generate fresh URLs that force browsers to re-fetch. Without this,
  // aggressive mobile-browser caching (Firefox Android especially) serves
  // stale CSS/JS across dev-server rebuilds and production redeploys.
  eleventyConfig.addGlobalData("buildId", Date.now().toString(36));

  return {
    dir: {
      input: "src",
      output: "_site",
      includes: "_includes",
      data: "_data",
    },
    templateFormats: ["njk", "md", "html"],
    markdownTemplateEngine: "njk",
    htmlTemplateEngine: "njk",
    pathPrefix: process.env.PATH_PREFIX || "/",
  };
}
