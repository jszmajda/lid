---
project: Clowder
owner: Jess Szmajda
tagline: A cozy incremental game for the terminal, built to live in a tmux pane for weeks. Nothing in it ever dies.
date: 2026-10-15
open_source: true
pictures:
  - file: clowder.png
    alt: "Clowder in a tmux pane: the stores down the left, a list of things to do and build in the middle, and the inspector on the right."
stats:
  - ["Code", "~100k lines of Rust, tests included"]
  - ["Author's prompts", "77 over 15 weeks"]
  - ["Tests", "~1,760"]
stats_source: "Counted from the repository on 14 November 2026. Most of the tree's names are left off on purpose: they would spoil the game."
story:
  title: How Clowder was built
  url: https://github.com/jszmajda/clowder/blob/main/docs/how-it-was-built.md
links:
  repo: https://github.com/jszmajda/clowder
---
Jess wanted to be surprised by her own game, so she never read its design docs, specs, tests, or code. She wrote the brief, chose how the agents were organized and reviewed, and played it. Agents did the rest, from 77 prompts over 15 weeks.

Agent reviewers and the high-level design's tenets stood in for the reviews LID usually pauses for. Playing the game was the one check they did not replace: it caught what the test suite missed.
