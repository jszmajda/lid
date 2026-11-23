---
project: compost
owner: Friday
tagline: A window system for Linux where every window is a terminal, so anything that can print can draw.
date: 2026-11-14
open_source: false
pictures:
  - file: desk.png
    alt: "The compost desktop: two terminals, the cat clock, and garden's drawers down the right, under a pale menu bar."
  - file: battuta.png
    alt: "battuta, compost's browser, showing one of Help's pages from disk."
  - file: plumb.png
    alt: "A shell beside acme: plumb notes.txt:12 has just run in the shell, and acme selects line 12."
  - file: folders.png
    alt: "Two folder windows; the front one has stripes and boxes, the one behind is flat."
  - file: help.png
    alt: "compost's Help window, with its guides and every design document listed down the left."
stats:
  - ["Specs", "1,652 built"]
  - ["Implementer runs", "156"]
  - ["Time", "8 days"]
  - ["Code", "Erlang/OTP and Rust"]
stats_source: "Numbers from the project's own story, as of 14 November 2026. The tree's shape comes from compost's Help window."
spec_count: 1652
story:
  title: A desktop in ten days
  author: Claude
  byline: Written by Claude, for Friday
  file: story.html
---
compost rebuilds the MGR window model on today's Linux: a program draws, makes menus, and reads the mouse only by writing bytes to its own window, so a shell script can draw, even over ssh. On top sit the classic Macintosh's System 6 shapes, Plan 9's plumber, a terminal that runs tmux and Claude Code, and a browser.

Friday wrote down what compost should be and made the choices. Claude sessions built it in parallel: clean-room implementers that worked from the design alone, and reviewers that attacked each design before any code existed.
