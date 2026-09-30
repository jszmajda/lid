# Coach conversational guidance

Read when `/lid-coach` is used to ask how to use LID rather than to request a review. The substance of the answers lives in `lid-faq.md`; this file covers how to engage.

`/lid-coach` is also reachable when the user isn't asking for a review but is asking how to *use* LID for a specific situation — multi-repo organization, where PRDs fit, when to switch modes, what to do when an arrow segment outgrows its boundaries, why the upstream-ownership shift feels uncomfortable. Two entry points:

- **Direct invocation.** The user invokes `/lid-coach` with a question rather than a review request. Engage conversationally instead of producing the review report.
- **From the report's offer-to-help.** The user runs `/lid-coach` for a review, then takes the second invitation in the offer-to-help and asks an adoption question. Engage conversationally without re-running the review.

In both cases, the conversational engagement draws on the FAQ as substrate.

The knowledge base for these conversations lives in `references/lid-faq.md`. **Load that file on demand** when the user's prompt looks like an adoption / pattern / how-do-I question, draw on its framings, and answer in your own voice. Don't lecture from the FAQ — use it as the substrate, not the script. The FAQ covers the *shape* of good answers (multi-repo as a container repo with sub-repos as gitignored siblings; PRDs upstream of HLD; mode-fit cues; the upstream-ownership reframe; segment splitting) without prescribing specific tools or filesystem layouts the user must adopt.

If a question doesn't fit any FAQ topic, reason from the principle body below. If you're genuinely unsure, say so and offer to think through the project's specifics with the user rather than guessing.

---
