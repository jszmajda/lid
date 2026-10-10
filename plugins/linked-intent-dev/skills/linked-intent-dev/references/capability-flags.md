# Capability flags

This file answers one question for the person pairing with you: **can they use LID with this model, and will it be effective?** LID's guidance runs on whatever model the user chooses. Most of it holds on any model, but some kinds of judgment depend on the model and on how much it reasons. LID's evals measure those kinds of judgment across the model configurations listed here. Where a configuration is known to miss one, LID brings that judgment to the user instead of letting the model settle it alone.

## How to use this file

1. Find your configuration: your model name and the reasoning effort you run at. Each section below lists every configuration tested for that kind of judgment, flagged or not.
2. If your configuration is **flagged** for a kind of judgment, bring that judgment to the user whenever your work touches it, even if they have let that kind of judgment go. Tell them why, once and plainly. If they have seen the flag and still prefer to let it go, follow that.
3. If your configuration **passed**, handle that kind of judgment as the user has asked.
4. If there is **no row** for your configuration (an untested model, a different reasoning effort, or you cannot tell what you run at), treat every flag in this file as applying to you.

A flag says where to look harder. It does not limit what you do: do your best work everywhere, and bring the flagged judgment to the user as well.

5. If your configuration is listed under **Tendencies**, the behavior still reaches the user, so nothing changes about who decides. When the behavior comes up, tell the user once that models configured like you lean that way, so they can weigh it.

## What the rows record

- **Configuration**: exact model ID, the harness it ran in, and its reasoning effort. LID's own evidence runs pin effort at `medium`.
- **Evidence**: runs per test project and the pass rate on each, with the date.
- **Release date and size tier**: recorded as data, not used to decide whether a flag applies.

A flag enters this file only when the gap is real: at least 10 runs per configuration, a gap larger than the spread between repeated runs of one model, and the gap appearing on at least two test projects. A configuration leaves a flag when a rerun no longer shows the gap.

## Flags

Evidence for every row: 10 runs per test project, reasoning effort `medium`, graded blind. Strong configurations score 9 or 10 of 10 on each project across repeated batches; a flag marks a gap well beyond that spread, on both of its projects. The test projects are small and state the conditions a judgment turns on fairly plainly, so a passing row means the model makes the judgment when the docs make it visible; it says less about a large real project where nothing announces it.

### Tenet or goal conflict

Noticing that a design's mechanism works against one of the project's own tenets or goals, when the two share no wording. Test projects: lid-coach evals 15 (library holds) and 16 (home-visit openings).

| Configuration | Harness | Effort | Test projects (pass rate) | Result | Date | Released | Size |
|---|---|---|---|---|---|---|---|
| `claude-sonnet-4-5` | claude -p (Claude Code 2.1.296) | medium | eval 15 0/10; eval 16 0/10 | **flagged** | 2026-10-10 | 2025-09 | mid |
| `claude-haiku-4-5` | claude -p (Claude Code 2.1.296) | medium | eval 15 0/10; eval 16 0/10 | **flagged** | 2026-10-10 | 2025-10 | small |
| `z-ai/glm-5.3-flash` | opencode-ai@1.18.32 | medium | eval 15 1/10; eval 16 5/10 | **flagged** | 2026-10-10 | 2026-08 | small |
| `claude-sonnet-4-6` | claude -p (Claude Code 2.1.296) | medium | eval 15 6/10; eval 16 10/10 | passed | 2026-10-10 | 2026-02 | mid |
| `deepseek/deepseek-v4.1-flash` | opencode-ai@1.18.32 | medium | eval 15 8/10; eval 16 9/10 | passed | 2026-10-10 | 2026-09 | small |
| `claude-haiku-5-5` | claude -p (Claude Code 2.1.296) | medium | eval 15 10/10; eval 16 10/10 | passed | 2026-10-10 | 2026-10 | small |
| `claude-sonnet-5-5` | claude -p (Claude Code 2.1.296) | medium | eval 15 10/10; eval 16 10/10 | passed | 2026-10-10 | 2026-09 | mid |
| `claude-opus-4-8` | claude -p (Claude Code 2.1.296) | medium | eval 15 10/10; eval 16 10/10 | passed | 2026-10-10 | 2026-05 | large |
| `claude-opus-5-5` | claude -p (Claude Code 2.1.296) | medium | eval 15 10/10; eval 16 10/10 | passed | 2026-10-10 | 2026-09 | large |
| `z-ai/glm-5.3` | opencode-ai@1.18.32 | medium | eval 15 10/10; eval 16 10/10 | passed | 2026-10-10 | 2026-08 | large |
| `openai/gpt-5.6-terra` | opencode-ai@1.18.32 | medium | eval 15 10/10; eval 16 10/10 | passed | 2026-10-10 | 2026-07 | mid |
| `openai/gpt-5.6-sol` | opencode-ai@1.18.32 | medium | eval 15 10/10; eval 16 10/10 | passed | 2026-10-10 | 2026-07 | large |
| `openai/gpt-6.1-sol` | opencode-ai@1.18.32 | medium | eval 15 10/10; eval 16 10/10 | passed | 2026-10-10 | 2026-09 | mid |

### Under-captured decision

Recognizing when a settled choice will stay live for a later reader, so it deserves a fuller record: offering a decision doc when you settle such a choice, and, in review, flagging a decision whose record does not let a cold reader reconstruct what was given up. Test projects: core evals 0 (an HLD-level choice) and 3 (a design-doc-level choice), where the doc should be offered; lid-coach evals 10 and 11, where a thin record should be flagged. The flagged Claude rows miss on both kinds; `openai/gpt-5.6-terra` flags thin records in review but rarely offers the doc while designing.

| Configuration | Harness | Effort | Test projects (pass rate) | Result | Date | Released | Size |
|---|---|---|---|---|---|---|---|
| `claude-sonnet-4-5` | claude -p (Claude Code 2.1.296) | medium | core 0 4/10; core 3 0/10; coach 10 8/10; coach 11 6/10 | **flagged** | 2026-10-10 | 2025-09 | mid |
| `claude-haiku-4-5` | claude -p (Claude Code 2.1.296) | medium | core 0 2/10; core 3 0/10; coach 10 5/10; coach 11 2/10 | **flagged** | 2026-10-10 | 2025-10 | small |
| `openai/gpt-5.6-terra` | opencode-ai@1.18.32 | medium | core 0 6/10; core 3 3/10; coach 10 10/10; coach 11 10/10 | **flagged** | 2026-10-10 | 2026-07 | mid |
| `claude-sonnet-4-6` | claude -p (Claude Code 2.1.296) | medium | core 0 9/10; core 3 3/10; coach 10 10/10; coach 11 10/10 | passed | 2026-10-10 | 2026-02 | mid |
| `z-ai/glm-5.3-flash` | opencode-ai@1.18.32 | medium | core 0 10/10; core 3 10/10; coach 10 10/10; coach 11 6/10 | passed | 2026-10-10 | 2026-08 | small |
| `openai/gpt-5.6-sol` | opencode-ai@1.18.32 | medium | core 0 10/10; core 3 9/10; coach 10 10/10; coach 11 10/10 | passed | 2026-10-10 | 2026-07 | large |
| `deepseek/deepseek-v4.1-flash` | opencode-ai@1.18.32 | medium | core 0 10/10; core 3 10/10; coach 10 10/10; coach 11 10/10 | passed | 2026-10-10 | 2026-09 | small |
| `claude-haiku-5-5` | claude -p (Claude Code 2.1.296) | medium | core 0 10/10; core 3 10/10; coach 10 10/10; coach 11 10/10 | passed | 2026-10-10 | 2026-10 | small |
| `claude-sonnet-5-5` | claude -p (Claude Code 2.1.296) | medium | core 0 10/10; core 3 10/10; coach 10 10/10; coach 11 10/10 | passed | 2026-10-10 | 2026-09 | mid |
| `claude-opus-4-8` | claude -p (Claude Code 2.1.296) | medium | core 0 10/10; core 3 10/10; coach 10 10/10; coach 11 10/10 | passed | 2026-10-10 | 2026-05 | large |
| `claude-opus-5-5` | claude -p (Claude Code 2.1.296) | medium | core 0 10/10; core 3 10/10; coach 10 10/10; coach 11 10/10 | passed | 2026-10-10 | 2026-09 | large |
| `z-ai/glm-5.3` | opencode-ai@1.18.32 | medium | core 0 10/10; core 3 10/10; coach 10 10/10; coach 11 10/10 | passed | 2026-10-10 | 2026-08 | large |
| `openai/gpt-6.1-sol` | opencode-ai@1.18.32 | medium | core 0 10/10; core 3 10/10; coach 10 10/10; coach 11 10/10 | passed | 2026-10-10 | 2026-09 | mid |

## Tendencies

A tendency is a lean in a behavior the user already sees and decides, so it changes nothing about who decides. When it comes up, mention it once.

### Offers decision docs too readily

Offering, or inviting the user to ask for, a decision doc for a choice a Decisions row covers: one an inherited constraint settles, or one that affects only its own design node however long it was debated. If you are listed, then when you offer a doc, add that models configured like you tend to offer them more often than needed. Test projects: core evals 1 (a constraint-settled choice) and 2 (a long debate over a single-node choice); the pass rate is how often the model held back.

| Configuration | Harness | Effort | Test projects (pass rate) | Result | Date | Released | Size |
|---|---|---|---|---|---|---|---|
| `claude-opus-4-8` | claude -p (Claude Code 2.1.296) | medium | core 1 3/10; core 2 4/10 | **listed** | 2026-10-10 | 2026-05 | large |
| `z-ai/glm-5.3-flash` | opencode-ai@1.18.32 | medium | core 1 6/10; core 2 3/10 | **listed** | 2026-10-10 | 2026-08 | small |
| `deepseek/deepseek-v4.1-flash` | opencode-ai@1.18.32 | medium | core 1 6/10; core 2 8/10 | not listed | 2026-10-10 | 2026-09 | small |
| `z-ai/glm-5.3` | opencode-ai@1.18.32 | medium | core 1 8/10; core 2 7/10 | not listed | 2026-10-10 | 2026-08 | large |
| `claude-sonnet-5-5` | claude -p (Claude Code 2.1.296) | medium | core 1 8/10; core 2 9/10 | not listed | 2026-10-10 | 2026-09 | mid |
| `claude-sonnet-4-6` | claude -p (Claude Code 2.1.296) | medium | core 1 10/10; core 2 8/10 | not listed | 2026-10-10 | 2026-02 | mid |
| `claude-sonnet-4-5` | claude -p (Claude Code 2.1.296) | medium | core 1 10/10; core 2 9/10 | not listed | 2026-10-10 | 2025-09 | mid |
| `claude-haiku-4-5` | claude -p (Claude Code 2.1.296) | medium | core 1 10/10; core 2 9/10 | not listed | 2026-10-10 | 2025-10 | small |
| `openai/gpt-5.6-terra` | opencode-ai@1.18.32 | medium | core 1 9/10; core 2 10/10 | not listed | 2026-10-10 | 2026-07 | mid |
| `openai/gpt-5.6-sol` | opencode-ai@1.18.32 | medium | core 1 10/10; core 2 9/10 | not listed | 2026-10-10 | 2026-07 | large |
| `claude-haiku-5-5` | claude -p (Claude Code 2.1.296) | medium | core 1 10/10; core 2 10/10 | not listed | 2026-10-10 | 2026-10 | small |
| `claude-opus-5-5` | claude -p (Claude Code 2.1.296) | medium | core 1 10/10; core 2 10/10 | not listed | 2026-10-10 | 2026-09 | large |
| `openai/gpt-6.1-sol` | opencode-ai@1.18.32 | medium | core 1 10/10; core 2 10/10 | not listed | 2026-10-10 | 2026-09 | mid |

## Notes

- `claude-sonnet-4-5` is deprecated: Anthropic retires it on its API on 2026-11-30, and Amazon Bedrock ends it on 2027-04-08. `claude-haiku-4-5` may be deprecated soon (its committed availability runs to 2026-10-15). `claude-haiku-5-5` is the tested successor and passed every project.
- `claude-sonnet-4-6` missed the design-doc-level offer (core 3, 3/10) while catching the HLD-level one (core 0, 9/10). One project is below the bar for a flag; it is recorded here so a later run can confirm or clear it.
- Some configurations report tenet conflicts too readily: on lid-coach eval 15, which carries a decoy mechanism that only costs something toward a goal, `claude-haiku-5-5` also flagged the decoy in 9 of 10 runs and `claude-opus-5-5` in 6 of 10, while both caught the real conflict every time. Eval 16 did not reproduce it strongly (2 of 10 for each), so it is below the bar for a tendency and recorded here. If you are one of these, check that each tenet finding names a condition the docs describe, rather than a cost the design already accepts.
- Release month and size are data, not keys. In this evidence neither predicts a miss: a small model (`claude-haiku-5-5`) passed everything, and a mid one (`claude-sonnet-4-5`) is flagged twice.
