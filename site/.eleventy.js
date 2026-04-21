import eleventyNavigationPlugin from "@11ty/eleventy-navigation";

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
