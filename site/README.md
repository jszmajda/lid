# LID marketing site

The conversion and orientation surface for Linked-Intent Development. Deep docs live in the repo root; this site is for first impressions and evaluator paths.

**Intent anchors (read these before editing content):**

- `../docs/llds/marketing-site.md` — LLD, including structure, tone, and decisions
- `../docs/specs/marketing-site-specs.md` — EARS specs (MKT-SITE-001 through 037)
- `../docs/high-level-design.md` — HLD (§ Target Users, § Goals 3 and 5)

## Preview locally

```
cd site
npm install
npm run dev
```

The dev server starts on [http://localhost:8080](http://localhost:8080) and hot-reloads on changes.

## Build for production

```
npm run build
```

Output lands in `_site/`. The workflow at `.github/workflows/site-build.yml` publishes to GitHub Pages on push to `main`; with the `CNAME` file at `src/CNAME`, the live site serves from `https://linked-intent.dev/`.

## Structure

```
site/
  .eleventy.js          # Eleventy config
  package.json
  src/
    _data/site.json     # site-wide metadata (pitch, framing, quickstart commands)
    _includes/
      base.njk          # base HTML layout
      nav.njk           # primary navigation
    assets/css/main.css # theme + base styles (dark default, light via prefers-color-scheme)
    index.njk           # Home — pitch, framing, quickstart, demo, paths
    start.njk           # Start — four audience paths
    examples.njk        # Examples — urlshort + threadkeeper
    anti-patterns.njk   # Anti-patterns — when LID is wrong
```

## Content cascade

When editing content, remember the cascade rules from the LLD:

- The home-page Quickstart commands (`src/_data/site.json`) must match the repository README's Quickstart (`MKT-SITE-008`, `MKT-SITE-009`).
- When the HLD changes, review site content for claim drift (`MKT-SITE-033`).
- When a plugin LLD that describes user-facing behavior changes, review the Start page path descriptions and Quickstart commands (`MKT-SITE-034`).
- When skill behavior changes materially, re-record the asciinema demo before the next deploy (`MKT-SITE-035`).

The site is a named segment in `docs/arrows/index.yaml` once the overlay is bootstrapped — it is auditable under `/arrow-maintenance`.

## Design

Visual polish (typography, hero visual, component styling) is delegated to the `frontend-design` plugin's skill. The current CSS in `src/assets/css/main.css` is a working first pass; `frontend-design` can iterate on it without changing content or structure.

## Asciinema

The demo placeholder in `src/index.njk` expects a cascade scenario (see `MKT-SITE-003`). Record via `asciinema rec`, upload to asciinema.org, and replace the placeholder block with the official embed snippet.
