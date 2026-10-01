# Capability flags

This file answers one question for the person pairing with you: **can they use LID with this model, and will it be effective?** LID's guidance runs on whatever model the user chooses. Most of it holds on any model, but some kinds of judgment depend on the model and on how much it reasons. LID's evals measure those kinds of judgment across the model configurations listed here. Where a configuration is known to miss one, LID brings that judgment to the user instead of letting the model settle it alone.

## How to use this file

1. Find your configuration: your model name and the reasoning effort you run at. Each section below lists every configuration tested for that kind of judgment, flagged or not.
2. If your configuration is **flagged** for a kind of judgment, bring that judgment to the user whenever your work touches it, even if they have let that kind of judgment go. Tell them why, once and plainly. If they have seen the flag and still prefer to let it go, follow that.
3. If your configuration **passed**, handle that kind of judgment as the user has asked.
4. If there is **no row** for your configuration (an untested model, a different reasoning effort, or you cannot tell what you run at), treat every flag in this file as applying to you.

A flag says where to look harder. It does not limit what you do: do your best work everywhere, and bring the flagged judgment to the user as well.

## What the rows record

- **Configuration**: exact model ID, the harness it ran in, and its reasoning effort. LID's own evidence runs pin effort at `medium`.
- **Evidence**: runs per test project and the pass rate on each, with the date.
- **Release date and size tier**: recorded as data, not used to decide whether a flag applies.

A flag enters this file only when the gap is real: at least 10 runs per configuration, a gap larger than the spread between repeated runs of one model, and the gap appearing on at least two test projects. A configuration leaves a flag when a rerun no longer shows the gap.

## Flags

<!-- One section per kind of judgment that has at least one flagged configuration.
     Kinds of judgment are named as in the core workflow's list ("Judgment still reaches the user").
     Template:

### Tenet or goal conflict

Noticing that a design's mechanism works against one of the project's own tenets or goals, when the two share no wording.

| Configuration | Harness | Effort | Test projects (pass rate) | Result | Date | Released | Size |
|---|---|---|---|---|---|---|---|
| model-id | claude -p / opencode | medium | eval 15 0/10; eval 16 0/10 | **flagged** | YYYY-MM-DD | YYYY-MM | small / mid / large |
| model-id | ... | medium | eval 15 10/10; eval 16 10/10 | passed | YYYY-MM-DD | YYYY-MM | ... |
-->
