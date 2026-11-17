# Seed: ReleaseDesk

The second seed: an archive's publication service, where embargoes, approvals, and takedowns decide what the public can see, and every new surface (search, bundles, previews, manifests) must respect the same rules. GPT-6.1 Sol proposed it ([seed-proposals/gpt-6.1-sol.md](../../seed-proposals/gpt-6.1-sol.md)).

**Status:** the brief, oracle, and change script were accepted by the maintainer on 2026-11-15. The probes (71, in three setups) were drafted by GPT-6.1 Sol, reviewed by Claude Fable, fixed, and checked by Fable, and are recorded as version 2: after the ceiling check, one probe also retrieves the folder its expectation is about, and one writes its import fixture with the grading tool's new file operation. The first seed showed that a strong model guesses most intent that is a sensible default (see [log.md](../../log.md), 2026-11-14). ReleaseDesk is meant to also carry intent a strong model wouldn't guess, which real owners set either way, and which later changes have to keep respecting. Ideas come first from several model families, starting with Gemini 4 Carbon and Claude Fable, working independently from [prompts/01-surprising-intent.md](prompts/01-surprising-intent.md).

- **Public:** this README, the [brief](brief.md) every arm receives, and the authoring prompts in [prompts/](prompts/) (the prompt for the oracle names the hidden rules, so it stays private until the runs finish).
- **Private, in `hidden/`:** each model's ideas, and later the oracle, change script, probes, and edit log, until the runs that use them finish.

## How the hidden intent was chosen

1. GPT-6.1 Sol drafted the owner's up-front material, deliberately silent on 15 open questions.
2. Gemini 4 Carbon wrote the brief from it, and Claude Fable checked it for hints.
3. Gemini 4 Carbon and Claude Fable, working independently, proposed surprising owner rules.
4. A cold panel of six models from five families measured how often each candidate is guessed, and the bands were fixed before any trajectory.
5. A seeded lottery drew 4 low-guess, 2 medium, and 2 high-guess rules. The seed was the hash of the commit that recorded the procedure.
6. Sol drafted the oracle and change script with those eight as the only latent items. Fable reviewed the drafts, the main session made the fixes, and Fable checked them.
7. The probes went through the same chain: Sol drafted them, Fable reviewed them, the main session fixed them, and Fable checked the fixes.

The private record of each step is in `hidden/`.

## Hashes

| Version | Date | File | SHA-256 |
|---|---|---|---|
| 1 | 2026-11-15 | `brief.md` | `79c9bdea8a9e378036175b3bc2e0d2acc09d5610b2160fb5ef98f0eeca753a4a` |
| 1 | 2026-11-15 | `hidden/oracle.md` | `56fc35b2941ae6a4264ba32b327a37ae7154e969ee11f69a6c879b8f1ba8f26f` |
| 1 | 2026-11-15 | `hidden/change-script.md` | `321f68cd17adacedec5a7fcd5161a13c26bc5eaee93b165505078424ffd6f695` |
| 1 | 2026-11-15 | `hidden/probes.md` | `350bc195f74dd40d1f0a3e2846e189e6d31dff4418ad5e18a43c102b391b9df5` |
| 2 | 2026-11-15 | `hidden/probes.md` | `840a26f3c061b771a129e2079c02f450e9b9e14adc2aba9005d1f13bcecda6b7` |
| 1 | 2026-11-16 | `hidden/owner-items.json` | `c7e00ae23d66c7968778a61546008ae25faee65de1796772d4982142ae3fee61` |
