<!-- Add a project you built with LID to the site's examples showcase.
     Thank you! Your project gets a page of its own on the LID site, with its pictures, a short
     brief, a drawing of its intent tree, and a link to its story.
     How to: CONTRIBUTING.md § "Share a project you built". The format, in full:
     docs/intent/onboarding/examples-showcase/examples-showcase-design.md -->

## The project

- **Name:**
- **Owner** (as you'd like to be credited):
- **One line on what it is:**
- **Open source?** <!-- yes, with a link / no. Private projects are welcome: the page shows only what you choose. -->

## What's in this pull request

One folder, `site/src/examples/<your-project>/` (lowercase letters, digits, and hyphens), holding:

- [ ] `index.md`: your entry. Copy `site/src/examples/_template/index.md` and fill it in.
- [ ] A screenshot or two (PNG or JPEG, at most 2 MB each), each with alt text. No screen to show? Leave them out and add `tree.yaml`; the site draws your tree instead.
- [ ] `tree.yaml`: your intent tree's shape and spec counts, made by running `node site/scripts/intent-tree.js <your-repo>/docs/intent > tree.yaml` from a checkout of this repository. Add `--no-names` to leave every name out (for a private design, or names that would spoil something), or delete single names from the file by hand.
- [ ] Your story, if you'd like it hosted here: `story.md`, or a self-contained `story.html` (no scripts, nothing loaded from other sites). Hosted somewhere else? Put its link in `index.md` instead.

## About the numbers

<!-- Where do the stats in index.md come from: counted from the repository, or your own estimate?
     Rough is fine. They are there to give readers a sense of scale. -->

## Credit and permission

- [ ] I own this project, or its owner has agreed to it being featured.
- [ ] Every picture and every word in this entry may be published on the LID site.
- [ ] If an AI wrote the story's words, the entry credits it (for example, "Written by Claude, for Friday").

## Anything else

<!-- Optional: what you hope readers take away, or anything the maintainer should know. -->
