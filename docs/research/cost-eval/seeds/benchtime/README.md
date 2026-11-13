# Seed: BenchTime

BenchTime is a reservation service for shared lab instruments, with cleaning buffers, qualifications that must cover the whole booking, inspection before an instrument is available again, and maintenance closures. It is the pilot seed. GPT-6.1 Sol proposed it ([seed-proposals/gpt-6.1-sol.md](../../seed-proposals/gpt-6.1-sol.md)), and the reasons it was chosen are in [seed-proposals/README.md](../../seed-proposals/README.md).

**Status:** second edited versions ready for the maintainer's review (2026-11-12). Each arm now designs its own interface, so the brief is in the owner's words and fixes only the stack, one start command, one data location, and reading time from the system clock.

- **Public:**
  - [brief.md](brief.md), the brief every arm receives at the start, about 550 words;
  - [prompts/](prompts/), the authoring prompts.
- **Private, in `hidden/`:**
  - the oracle: 55 items, of which 53 are graded (14 stated at the start, 15 stated in later changes, 17 askable, 3 recognised on sight, 2 emerging, and 2 realised on a symptom) and 2 are marked Dropped;
  - the change script: 10 changes and a probe;
  - the unedited drafts;
  - the edit log (15 edits, three marked for review);
  - the first versions with a fixed interface, kept in `fixed-interface-v1/` as a fallback.

Drafting has cost about $0.65 on OpenRouter so far.

## Materials

| Material | Who writes it | Public? |
|---|---|---|
| Hidden oracle and change script | GPT-6.1 Sol drafts; the main session edits | No, until the runs that use them finish |
| Product brief | Gemini 4 Argon drafts from the items stated at the start; the main session edits | Yes |
| Authoring prompts | The main session | Yes, in [prompts/](prompts/) |
| Edit log and unedited drafts | — | No, until the runs that use them finish |

The rules for editing, and the reason the hidden materials stay private, are in [design.md](../../design.md) under "Seed projects". The private files live in `hidden/`, which git ignores.

## Hashes

SHA-256 hashes of the hidden materials will be recorded here before any counted run.
