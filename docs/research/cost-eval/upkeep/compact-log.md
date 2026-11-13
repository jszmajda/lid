# Procedure: compact the research log

Hand this file to a subagent, for example on Haiku. It describes the whole job. The session that runs it checks the result afterwards (see "Checking the result" at the end).

## When to run it

Run it when `log.md` is over about 2,000 words. The session that updates the log at the end of a working session checks the count with `wc -w log.md`.

## What the job is

The research log (`docs/research/cost-eval/log.md`) is a journal, newest entry first. Each entry is a `## ` heading that starts with a date (`## 2026-11-12 (night): ...`), followed by its body. The job keeps the log short enough for someone to read cold, without losing anything:

- recent entries stay in the log in full;
- older entries move, word for word, into monthly archive files;
- a short summary at the bottom of the log keeps the overall arc;
- a ledger, `decisions.md`, keeps every decision that still stands, one line each.

Only `log.md`, `decisions.md`, and files in `log-archive/` may be changed. Don't edit any other file.

## Steps

1. **Read `log.md`.** It has, in order:
   - a title and introduction at the top;
   - the entries;
   - possibly an "Earlier, in brief" section at the bottom, written by an earlier run of this procedure.
2. **Choose which entries stay.** Starting from the newest, keep entries in order for as long as the kept entries total no more than about 1,000 words. Always keep the newest entry, even if it is longer than that on its own. Every older entry moves.
3. **Move each older entry into the archive, word for word.** The archive file is `log-archive/YYYY-MM.md`, using the year and month from the entry's heading. If the file doesn't exist, create it with this first line:

   ```
   # Research log archive: YYYY-MM
   ```

   followed by a blank line and this sentence: "Entries moved out of [the research log](../log.md), newest first, unchanged apart from link paths."
   - Keep the archive file newest first, like the log. Put each moved entry where its date belongs.
   - Copy the heading and body exactly. The only change allowed is to relative links, because the archive sits one folder deeper. A link like `(design.md)` becomes `(../design.md)`, and `(seeds/benchtime/README.md)` becomes `(../seeds/benchtime/README.md)`. Leave links that start with `http`, `#`, or `../` alone, unless they start with `../` and point outside the `cost-eval` folder, in which case add one more `../`.
4. **Update the decisions ledger.** `decisions.md` lists every decision that still stands, one line each, in the form "- DATE, DECIDER: decision." For each decision in the entries you just moved, add a line if it isn't already there. If a later entry (moved or kept) replaced a decision, remove the old line. Keep the wording close to the log's. The decider is whoever the entry says decided ("Decided by the maintainer", "Decided by the main session"). If the entry doesn't say, write "decider not named" and mention it in your report.
5. **Rewrite the "Earlier, in brief" section** at the bottom of `log.md`, creating it if it isn't there. Build it from the previous "Earlier, in brief" section (if any) plus the entries you just moved. It has three parts and stays under about 300 words:
   - **The arc so far:** a short paragraph saying what happened in the moved entries, in the order it happened. Use only what the log says, without adding interpretation.
   - **Decisions:** one sentence pointing to [decisions.md](decisions.md).
   - **Archive:** a list of links to the archive files, newest first.
6. **Leave the top of `log.md` alone**, apart from its introduction, which should end with this sentence (add it if it's missing): "Older entries move to [log-archive/](log-archive/) when this file passes about 2,000 words, and 'Earlier, in brief' at the bottom summarizes them."
7. **Report back.** List:
   - which entries moved and to which files;
   - the word count of `log.md` before and after;
   - anything you weren't sure about.

## How to write the summary

Write plain, full sentences that a person reading quickly understands the first time. Start each sentence with its idea, without a lead-in. Use plain verbs. Give human verbs (decide, remember, know) only to people and agents, not to files or sessions. Don't use italics.

## Checking the result

The session that ran the procedure checks it with a short script or by reading:

- **Nothing was lost.** Every moved entry appears in the archive, identical to its old text apart from link paths.
- **Order is right.** The entries kept in `log.md` are the newest ones, still newest first.
- **The ledger is faithful.** Every line in `decisions.md` can be found in the log or the archive, with the right date and decider, and no replaced decision is still listed.
- **Links work.** Relative links in the archive still resolve.
