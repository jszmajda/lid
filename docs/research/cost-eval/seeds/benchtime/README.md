# Seed: BenchTime

BenchTime is a reservation service for shared lab instruments, with cleaning buffers, qualifications that must cover the whole booking, inspection before an instrument is available again, and maintenance closures. It is the pilot seed. GPT-6.1 Sol proposed it ([seed-proposals/gpt-6.1-sol.md](../../seed-proposals/gpt-6.1-sol.md)), and the reasons it was chosen are in [seed-proposals/README.md](../../seed-proposals/README.md).

**Status:** reviewed and accepted by the maintainer on 2026-11-13, including the three edits marked for review. Each arm designs its own interface, so the brief is in the owner's words and fixes only the stack, one start command, one data location, and reading time from the system clock. The probes (92, for all 53 graded items) were drafted by Sol and edited. At the maintainer's request, Claude Fable reviewed them in the maintainer's place; the fixes were checked by Fable again. The probes are recorded as version 2, the oracle as version 3, and the change script as version 2.

- **Public:**
  - [brief.md](brief.md), the brief every arm receives at the start, about 550 words;
  - [prompts/](prompts/), the authoring prompts.
- **Private, in `hidden/`:**
  - the oracle: 55 items, of which 53 are graded (14 stated at the start, 15 stated in later changes, 17 askable, 3 recognised on sight, 2 emerging, and 2 realised on a symptom) and 2 are marked Dropped;
  - the change script: 10 changes and a probe;
  - the probes: 92 scenarios with expected observations, in 8 named setups, and Sol's unedited draft;
  - the unedited drafts;
  - the edit log (51 edits to the oracle and probes, and one to the change script; three marked for review, all accepted);
  - the first versions with a fixed interface, kept in `fixed-interface-v1/` as a fallback.

Drafting has cost about $1.00 on OpenRouter so far.

## Materials

| Material | Who writes it | Public? |
|---|---|---|
| Hidden oracle and change script | GPT-6.1 Sol drafts; the main session edits | No, until the runs that use them finish |
| Probes | GPT-6.1 Sol drafts; the main session edits | No, until the runs that use them finish |
| Product brief | Gemini 4 Argon drafts from the items stated at the start; the main session edits | Yes |
| Authoring prompts | The main session | Yes, in [prompts/](prompts/) |
| Edit log and unedited drafts | — | No, until the runs that use them finish |

The rules for editing, and the reason the hidden materials stay private, are in [design.md](../../design.md) under "Seed projects". The private files live in `hidden/`, which git ignores.

## Hashes

SHA-256 hashes of the materials as accepted. If any of them change before the counted runs, a new version is added here with the reason.

| Version | Date | File | SHA-256 |
|---|---|---|---|
| 1 | 2026-11-13 | `brief.md` | `7c31dec2295d36501e7e890834cb1289f78546ebda21de4807d4d5f8dc073f10` |
| 1 | 2026-11-13 | `hidden/oracle.md` | `e2449448cd5e2ce25b0939fc62ebb3ba2a3bc4550bbddae73a0b4281c7e55b54` |
| 1 | 2026-11-13 | `hidden/change-script.md` | `94c7d2ef93257cba706b161dc2cf60c4f9ff77d8c95bf3c3ff7a1fca87f37b3e` |
| 2 | 2026-11-13 | `hidden/oracle.md` | `9dd8060599c9795b34e5c0acac4aa3d0fcbe10be051ef67956c875baf69d71af` |
| 1 | 2026-11-13 | `hidden/probes.md` | `64afcee1e8c1e3f2a00a33174817282ec3063763178724bf49a697bf411587d9` |
| 3 | 2026-11-14 | `hidden/oracle.md` | `7d1d39884a4e38c206e0bc089bb4103a586d7471d60340fbdc6d1d1d5c5d1cd8` |
| 2 | 2026-11-14 | `hidden/change-script.md` | `43030f3119c3a34fe505a5309248f3fb0d493e9fa3ad6bdcb460eb730301cb8e` |
| 2 | 2026-11-14 | `hidden/probes.md` | `c31a9cf28da8e637e9019ce7dc753924fb456881dff1489f761ea0c9aeb0c531` |

Oracle version 2 moves one clause from an item stated in a change to the askable item it depended on (edit E30), as edit E14 did before. Version 1 of the oracle is replaced. The brief and the change script are unchanged.

Oracle version 3 and change script version 2 (edits E48 to E51 and C1) change only what the simulated owner holds, after Claude Fable's review of the simulator and its live tests. They remove a study note and four passages that put recognised-on-sight rules or a graded boundary into the owner's own words, state in one item's text a case its sketch already graded, and list the items change 2's redirect introduces. No probe and no graded behaviour changes. The brief and the probes are unchanged.

Probes version 2 (edits E52 to E57) follows Claude Fable's spot-check of grader verdicts and its check of the fixes. Six probes that asked for more than their oracle items (mostly fields an item doesn't require, such as a shown deadline or a checkout reference) now ask only what the item says, with behavioural checks where needed. One probe's two physical blocks now run as independent cases.
