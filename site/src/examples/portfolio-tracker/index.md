---
project: portfolio-tracker
owner: Jess Szmajda
tagline: A personal stock and tax tracker with a terminal UI, backed by Google Sheets, with its money math formally proven.
date: 2026-06-14
open_source: true
pictures:
  - file: ledger.png
    alt: "portfolio-tracker's Positions screen in its gilt Ledger theme: total value, net after tax, and a table of holdings with trend sparklines."
stats:
  - ["Code", "~44k lines of Rust"]
  - ["Tests", "~820"]
  - ["CI gate", "Fails the build on any uncited spec"]
  - ["Proofs", "Verus and Kani on the accounting and tax kernels"]
stats_source: "Counted from the repository on 14 November 2026."
story:
  title: Write the whole tree, then hand it to a workflow
  file: story.md
links:
  repo: https://github.com/jszmajda/portfolio-tracker
  hld: https://github.com/jszmajda/portfolio-tracker/blob/main/docs/high-level-design.md
  intent_tree: https://github.com/jszmajda/portfolio-tracker/tree/main/docs/intent
---
Google Sheets is the store of record, a ratatui terminal UI is the way in, and the accounting and tax kernels are proven with Verus and Kani.

Every design doc and spec was written first, together with Jess, before any code. Then a 34-agent workflow built it test-first, with zero-context adversarial review. CI fails the build when a spec goes uncited.
