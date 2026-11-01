import eleventyNavigationPlugin from "@11ty/eleventy-navigation";
import markdownIt from "markdown-it";

// Light syntax coloring for the Tour page's fenced code: diff lines in red and
// green, and comments, strings, keywords, and numbers in TypeScript. Returning
// an empty string hands any other language back to markdown-it's own escaping.
// @spec MKT-SITE-075
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
