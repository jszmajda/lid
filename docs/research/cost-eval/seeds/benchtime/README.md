# Seed: BenchTime

BenchTime is a reservation service for shared lab instruments, with cleaning buffers, qualifications that must cover the whole booking, inspection before an instrument is available again, and maintenance closures. It is the pilot seed. GPT-6.1 Sol proposed it ([seed-proposals/gpt-6.1-sol.md](../../seed-proposals/gpt-6.1-sol.md)), and the reasons it was chosen are in [seed-proposals/README.md](../../seed-proposals/README.md).

**Status:** first edited versions ready for the maintainer's review (2026-11-12).

- **Public:**
  - [brief.md](brief.md), the product brief every arm receives at the start;
  - [prompts/](prompts/), the authoring prompts.
- **Private, in `hidden/`:**
  - the interface specification, the oracle (43 items: 14 stated at the start, 12 stated in later changes, 10 askable, 3 recognised on sight, 2 emerging, and 2 realised on a symptom), and the change script (10 changes and a probe);
  - the unedited drafts;
  - an edit log of the main session's eight edits to Sol's draft and one to Argon's, three of which are marked for review.

Drafting cost about $0.40 on OpenRouter: $0.24 for Sol and $0.15 for Argon.

## Materials

| Material | Who writes it | Public? |
|---|---|---|
| Interface specification, hidden oracle, and change script | GPT-6.1 Sol drafts; the main session edits | No, until the runs that use them finish |
| Product brief | Gemini 4 Argon drafts from the interface and the items stated at the start; the main session edits | Yes |
| Authoring prompts | The main session | Yes, in [prompts/](prompts/) |
| Edit log and unedited drafts | — | No, until the runs that use them finish |

The rules for editing, and the reason the hidden materials stay private, are in [design.md](../../design.md) under "Seed projects". The private files live in `hidden/`, which git ignores.

## Hashes

SHA-256 hashes of the hidden materials will be recorded here before any counted run.
