# Seed: ReleaseDesk

The second seed: an archive's publication service, where embargoes, approvals, and takedowns decide what the public can see, and every new surface (search, bundles, previews, manifests) must respect the same rules. GPT-6.1 Sol proposed it ([seed-proposals/gpt-6.1-sol.md](../../seed-proposals/gpt-6.1-sol.md)).

**Status:** the brief, oracle, and change script were accepted by the maintainer on 2026-11-15. The probes (71, in three setups) were drafted by GPT-6.1 Sol, reviewed by Claude Fable, fixed, and checked by Fable, and are recorded as version 2: after the ceiling check, one probe also retrieves the folder its expectation is about, and one writes its import fixture with the grading tool's new file operation. The first seed showed that a strong model guesses most intent that is a sensible default (see [log.md](../../log.md), 2026-11-14). ReleaseDesk is meant to also carry intent a strong model wouldn't guess, which real owners set either way, and which later changes have to keep respecting. Ideas come first from several model families, starting with Gemini 4 Carbon and Claude Fable, working independently from [prompts/01-surprising-intent.md](prompts/01-surprising-intent.md).

**Growth seed.** For the growth test ([design.md](../../design.md), "The growth test"), changes 11–40 extend ReleaseDesk by three more blocks of ten, after the ten above. GPT-6.2 Sol drafted them blind to the hypotheses, in four rounds: first from counts by change type and distance, then from lists of requirements. Claude Fable and GPT-6.2 Astra reviewed the first draft and re-checked the second. Each course change carries a reliance request that runs only as a discarded fork. The same cold panel as block 1 banded every latent rule in the new blocks. Four more latent rules were then chosen from Sol's candidates by a selection rule fixed before that panel ran. The change script and oracle additions are private in `hidden/`, beside block 1's, with their hashes below. Their probes come next.

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
| 2 | 2026-11-16 | `hidden/change-script.md` | `6f463a9b6649f7a35f12cb171a2cf888c1195a308a727422eb2f67f5eb559362` |
| 4 | 2026-11-20 | `hidden/change-script-growth.md` | `58089178abdcc430d697779912655e04ce9ed074bad03a2783d7545b2f1dac49` |
| 4 | 2026-11-20 | `hidden/oracle-growth.md` | `4fb990cf98f15b234c9a1d27cff4e2589a22ac101443cb8ac8b0fc62530f1920` |
| 1 | 2026-11-20 | `hidden/panel-growth/hidden/bands.json` | `618cbe2b8251713a7a4d9ab5c1c486e70c2f33cd24c08191342391b775e73aed` |
| 1 | 2026-11-20 | `hidden/panel-growth-rest/hidden/bands.json` | `7eeca2d952d8a7300165aed4801791af26678277ee8036e88eaa9a12b65c654b` |
| 1 | 2026-11-20 | `hidden/panel-growth-candidates/hidden/bands.json` | `ef9e88bf3e0effdaac045e422a30e6e5928da156689bb0f1dd5c0dde562d7575` |
| 1 | 2026-11-20 | `hidden/panel-growth-candidates/hidden/selection.json` | `c8656f37b2da22d1f43bcd4f94837110e7fba0a4d0987e07365608fbefbe7b2d` |
