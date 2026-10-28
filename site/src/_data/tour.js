// Content for the Tour page, read at build time from the newcomer tour's own
// files in the linked-intent-dev plugin, so the page and the in-agent tour
// share one source. The site renders the marked regions and leaves out the
// parts marked as making sense only inside the agent.
// @spec MKT-SITE-073, MKT-SITE-074, MKT-SITE-077, MKT-SITE-079, MKT-SITE-080

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.resolve(here, "../../..");
const references = path.join(repoRoot, "plugins/linked-intent-dev/skills/linked-intent-dev/references");

function region(text, name, file) {
  const match = text.match(new RegExp(`<!-- tour:${name} -->([\\s\\S]*?)<!-- /tour:${name} -->`));
  if (!match) throw new Error(`${file}: missing the <!-- tour:${name} --> region`);
  return match[1];
}

function withoutAgentOnly(text) {
  return text.replace(/<!-- agent-only -->[\s\S]*?<!-- \/agent-only -->\n?/g, "");
}

// Splits a region on its level-2 headings. A section may give its own anchor
// with an <!-- anchor: name --> line, which keeps links stable when a title
// changes; otherwise the anchor comes from the title.
function sections(markdown) {
  return markdown
    .split(/^## /m)
    .slice(1)
    .map((part) => {
      const lineEnd = part.indexOf("\n");
      const title = part.slice(0, lineEnd).trim();
      let body = part.slice(lineEnd + 1);
      const given = body.match(/<!-- anchor: ([a-z0-9-]+) -->/);
      body = body.replace(/<!-- anchor: [a-z0-9-]+ -->\n?/, "");
      const anchor = given
        ? given[1]
        : title.toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");
      return { title, anchor, body: body.trim() };
    });
}

export default function () {
  const read = (file) => readFileSync(path.join(references, file), "utf8");
  const manifest = JSON.parse(
    readFileSync(path.join(repoRoot, "plugins/linked-intent-dev/.claude-plugin/plugin.json"), "utf8"),
  );
  return {
    version: manifest.version,
    steps: sections(withoutAgentOnly(region(read("tour.md"), "steps", "tour.md"))).map((step) => {
      // "Tour 2 of 5: writing the design down" becomes "Writing the design down" for the sidebar.
      const label = step.title.replace(/^[^:]*:\s*/, "");
      return { ...step, label: label.charAt(0).toUpperCase() + label.slice(1) };
    }),
    topics: sections(withoutAgentOnly(region(read("tour-topics.md"), "topics", "tour-topics.md"))),
  };
}
