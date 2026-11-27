---
# A filled-in sample research entry. Copy this folder to site/src/research/<slug>/, where <slug>
# is the report's URL: lowercase letters, digits, and hyphens. The build does not publish it.
#
# title: the report's title, as shown on its card and as its page's h1.
title: "What a study found"
# date: the day the study's results were in (its last run or analysis), YYYY-MM-DD, which can be
# well before the report is published; it orders the index, newest first.
date: 2026-01-15
# revised: the day of its latest revision, later than date. Leave it out until it's revised.
revised: 2026-02-01
# status: pilot (analyses not fixed in advance), counted (pre-registered), or superseded.
status: pilot
# superseded_by: only when status is superseded; the slug of the report that replaces it.
# superseded_by: a-later-study
# summary: one or two sentences in the study's own words, plain text, at most 300 characters.
summary: "One or two sentences on what the study found, with its main caveat."
# tested: what was tested, so every number can be scoped: the LID version, the coding agent and
# its version, and the model and its effort.
tested:
  lid: "1.4.6"
  agent: "Claude Code 2.1.323"
  model: "Claude Sonnet 5.5, medium effort"
# records: a public https URL for the study's notebook, data, and code.
records: "https://github.com/jszmajda/lid"
---

## The question

The report itself, in Markdown. The page's header holds the title, so headings start at h2.
Links are https URLs, anchors within the page, or the bare file names of images in this folder.
