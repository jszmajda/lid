# Contributing to LID

**For human readers:** this guide is written for the coding agent helping you contribute. Point your agent at this file before starting work, then review the diff before opening a PR. If you are contributing without an agent, read it yourself — it is LID applied to LID, and the methodology lives in [`docs/high-level-design.md`](docs/high-level-design.md).

The rest of this document is for the agent.

## The bar

Contributions follow LID. This repository is the canonical LID-on-LID reference — its `docs/` tree is LID applied to LID, the plugins under `plugins/` walk the arrow like any other intent component, and any contribution does the same.

Walk the arrow for whichever phases the change touches. Changes originate upstream and cascade down. A change that starts at the HLD will update LLDs, EARS specs, and skill prose in the same PR. A change that starts at an LLD will update its specs, skill prose, and — for behavioral skills — evals. The methodology is in [`docs/high-level-design.md`](docs/high-level-design.md); the operating workflow is in [`AGENTS.md`](AGENTS.md).

## Trivial changes

The following do not require walking the arrow:

- Typo and grammar fixes in existing prose
- Broken-link repairs
- Formatting and whitespace
- Updating a stale external reference (e.g., a tool's docs URL changed)

Anything that changes the meaning of intent — including a one-line edit to an EARS spec, a skill description, or an HLD principle — is not trivial. Walk the arrow.

## Out of scope

LID's territory is the **structure of intent the agent compiles from**. Not orchestration, not collaboration style, not work scheduling. When a proposal sounds like "LID should help me *do* X" rather than "LID should help my intent stay coherent as the system grows," it is outside LID's scope.

Concrete categories that have come up and been declined:

- **Multi-agent orchestration or agent teams.** Coordination belongs to the harness layer, which is evolving fast. LID picking a coordination model freezes a choice the ecosystem has not settled.
- **Personas.** A prompting technique that lives at the model/harness layer. Pure surface growth from LID's perspective.
- **Development styles or team ceremonies.** Owned by the team, not by their intent-tracking tool.
- **Task management or work tracking.** LID's artifacts are *intent*, not *work*. A spec is not a ticket. Linear, Jira, GitHub Issues, and agent-harness task trackers already exist and evolve fast.

This list is descriptive, not exhaustive. New proposals are judged against the principle above.

## Arrow variant by change type

Every contribution walks an arrow, but the arrow shape varies by what is being changed. The HLD's *Key Design Decisions* section names the variants. The practical decision:

- **Change to an existing core plugin** (`linked-intent-dev` or `arrow-maintenance`) — walk that plugin's arrow.
  - *Behavioral skill* (slash-command-invoked, produces verifiable state changes): `HLD → LLD → EARS → evals + SKILL.md + references/`. A passing eval suite is the gate.
  - *Pure-prose skill* (shapes how the agent approaches work, no verifiable output): `HLD → LLD → SKILL.md + references/`. Verification is dogfooding — the next LID operation in this repo is the integration test.
  - *Dual-mode skill* (auto-trigger and slash-command): EARS covers command-mode behavior; ambient-mode behavior is verified by dogfooding.
- **Novel capability not in core** — does not land directly in a core plugin. Lands in [`plugins/lid-experimental/`](plugins/lid-experimental/) first, walking the standard arrow rooted in that plugin's LLD. Promotion into core is earned through community adoption and concrete value stories, not requested.
- **HLD or methodology change** — cascade through every affected LLD and spec in the same PR. Cross-segment cascade pauses for verification (per the HLD tenet *within-segment cascade is free; across-segment cascade pauses*); call those pauses out in the PR description.
- **Site, examples, or positioning content** — `HLD → LLD → EARS → content + assets`. Build-time link and structural checks substitute for evals.
- **New first-class plugin host** (a tool with its own plugin/skill marketplace, e.g. Cursor) — add its marketplace manifest and per-plugin manifests reusing the existing `plugins/` source, plus a plugin-host section in [`docs/setup.md`](docs/setup.md). `HLD → LLD → EARS → content + assets`.
- **New rule-file tool adapter** (Aider, Continue, etc.) — adapter file plus an entry in [`docs/setup.md`](docs/setup.md). The adapter points the agent at `AGENTS.md`; LID itself stays one source of truth.

The principle behind these variants: **tests when the artifact has a runtime to assert against; dogfooding-or-justify when it does not.** "I could not write a test" is a fine answer for pure-prose skills. It is not a fine answer for behavioral skills or content artifacts — those have established verification modes, and skipping them is breaking the arrow.

## Minimum-surface gate

A new command, skill, plugin, or convention is not just cognitive load for users — it is LID reaching into territory the fast-moving tooling layer (models, harnesses, IDEs, memory systems) is likely to handle better next quarter. Before adding any new surface, clear the gate the HLD names:

> Can the existing surface absorb this, or is the agent about to absorb it anyway?

If existing surface can absorb the change, fold it in. If the agent is about to absorb it, let the agent. Only if both answers are no does new surface get considered, and even then, novel capabilities land in `lid-experimental` first.

## Mechanics

**One PR = one coherent intent change, walked end-to-end through whichever arrow phases it touches.**

Coherence, not size, is the unit:

- Tiny is fine: a sharpened EARS line plus the eval that checks it.
- Larger is fine: an LLD section rewrite cascaded through its specs and skill prose.
- Wrong: bundling unrelated improvements ("while I was in here, I also fixed…"). Each independent improvement gets its own PR.

The reviewer test: *would I have to context-switch between two unrelated things to evaluate this PR?* If yes, split.

For changes that may add new surface, file an issue before walking the arrow — the minimum-surface gate is better discussed before arrow work that may not survive the conversation. Changes that fit clearly within existing surface (sharpening an existing skill, repairing drift in an LLD, adding an EARS spec to an existing component) go straight to a PR.

Branch from `main`. Lead the PR description with what reviewers actually use:

- **Why** — the motivation and impact: the problem, who it affects, why it's worth doing.
- **What changed** — the substance.
- **How it's been tested** — builds, evals, cold-reads, real-project checks, or the dogfooding scenarios a pure-prose change was exercised against.
- **Arrow touched** — a lightweight line naming the segments and EARS IDs (or that the change is trivial).

Include the heavier gate items only when the change involves them: the minimum-surface gate answers when introducing new surface, and the cross-segment pause points (with what was verified at each) when a cascade crosses a boundary.

These are conventions, not a template to copy-paste; [`.github/PULL_REQUEST_TEMPLATE.md`](.github/PULL_REQUEST_TEMPLATE.md) is the starting point.

## Release / versioning

LID is versioned with semver per plugin, and `linked-intent-dev`'s version is the canonical "LID conventions" version. There is no CI gate keeping the version strings in sync — this release step is the conventional discipline that substitutes for one, in keeping with LID's stance that it is not a linter or validator.

**When to bump.** The version reflects what a downstream project must or may act on, not every plugin change. *Major* = radically new or breaking behavior; *minor* = an important structural or convention change projects adopt; *patch* = a smaller change a project may act on. A change that requires nothing of existing projects — a new supported host or platform, internal refactors, docs — gets **no version bump**: record it under `## [No Version Update Required]` in the CHANGELOG; it folds into the next numbered version's entry when one is cut. (New experiments are typically a patch; core-skill changes are minor or major by extent.) Withholding the bump when nothing is required keeps `/update-lid` from triggering a no-op version-walk on every project. The steps below apply only when you are actually advancing the version.

When cutting a release:

- Bump the `version` field in each plugin's `.claude-plugin/plugin.json` and the matching entry in [`.claude-plugin/marketplace.json`](.claude-plugin/marketplace.json) together — six version strings, kept equal per plugin. The Cursor manifests (`.cursor-plugin/marketplace.json` and each `.cursor-plugin/plugin.json`) carry no `version` and are not part of this sync.
- Add a [`CHANGELOG.md`](CHANGELOG.md) entry for the release (Keep a Changelog format), including a `### Migration (vX → vY)` section whenever conventions changed so `update-lid` can walk downstream projects through the upgrade.
- Keep the `CHANGELOG.md` top version equal to `linked-intent-dev`'s `plugin.json` version — that is the canonical LID version.
- Publish the release: create the git tag and GitHub Release with notes from the new `CHANGELOG.md` entry, announcing it to the community in one step — `gh release create vX.Y.Z --notes-file <entry> --discussion-category Announcements`. This tag-and-Release step is what keeps published releases from falling behind the manifests, and the `--discussion-category` flag posts the announcement to Discussions automatically.

The changelog is canonical at `plugins/linked-intent-dev/CHANGELOG.md` and aliased by the repo-root symlink, so it ships inside the plugin. Reviewers confirm the versions and changelog match before merging the release.
