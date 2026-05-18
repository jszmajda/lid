# LID Coach — Not Yet Configured

I looked through your project and there's nothing for me to coach against yet. The directory is empty: no `CLAUDE.md`, no `docs/` tree, no high-level design, no LLDs, no EARS specs, and no `docs/arrows/` overlay. There are no LID-shaped artifacts anywhere.

The coach is a principle-level review — it compares the intent you've already captured (HLD, LLDs, specs, the arrow overlay) against LID's own principles and tells you where patterns are drifting or leaving value on the table. With no intent captured yet, there's nothing to review, so I'm not going to produce a scorecard or findings against an empty tree (that would just be noise).

## What to do instead

This project isn't LID-configured yet, so the next step is to set it up rather than to review it:

- **If you just want to bootstrap LID into this project** — run **`/update-lid`**. It state-dispatches: on an unconfigured project like this one it bootstraps the configuration (creates `CLAUDE.md` directives, sets your LID mode, lays out the standard `docs/` structure).

- **If you already have a specific change or feature in mind** — run **`/linked-intent-dev`** with a description of what you want to build. Its first phase calls the bootstrap branch as a sub-step and then walks your change forward through the arrow (HLD → LLD → EARS → tests → code), so you get the setup and your first real arrow in one pass. This is usually the better starting point for a fresh project with work to do.

Once there's an arrow in place — even a sparse one — come back and run `/lid-coach` again and I can give you a real principle review.

## Broader questions

If you have questions about *how* to adopt LID before you start — multi-repo organization, where PRDs fit relative to the HLD, choosing between Full and Scoped mode, or how to structure things for your particular project — I'm happy to talk through those with you. Just ask.
