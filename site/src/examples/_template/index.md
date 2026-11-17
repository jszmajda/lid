---
# A sample entry. Copy this folder to site/src/examples/<your-project>/ (lowercase letters,
# digits, and hyphens), fill it in, and delete the fields you don't use. The site builds your
# project's page from it; the build fails, naming the rule, if something is off.
# See docs/intent/onboarding/examples-showcase/examples-showcase-design.md for the full format.

project: Your project            # required: its name as shown
owner: Your Name                # required: who owns it, as they want to be credited
tagline: One sentence on what it is.   # required
date: 2026-11-16                # required: ISO date the entry is about; the index is newest first
open_source: true               # required: true or false; private entries link no repo, HLD, or intent tree

pictures:                       # a picture or a tree.yaml is required; the first picture leads
  - file: screenshot.png        # PNG or JPEG in this folder, at most 2,000,000 bytes
    alt: "What the picture shows, for someone who can't see it."

stats:                          # [label, value] pairs of strings, in your words; cards show the first three
  - ["Code", "~20k lines of Go"]
  - ["Time", "Three weeks"]
stats_source: "Where the numbers come from, in one sentence."

spec_count: 240                 # only when tree.yaml has no counts: sets the size name

story:                          # optional
  title: How it was built
  author: Your Name             # defaults to owner; when it differs, cards say "post written by …"
  byline: Written by …          # optional: replaces "by <author>"
  url: https://example.com/your-post    # a post elsewhere, or instead `file: story.md` / `file: story.html` here

links:                          # optional, https only: repo, hld, intent_tree, live
  repo: https://github.com/you/your-project
---
A paragraph or two on what the project is and how it was built. This is the site's framing of
your project, so the maintainer may edit it at review; your story keeps your own words.
