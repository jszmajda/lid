# High-Level Design: Linked-Intent Development

## Problem

Modern AI coding agents rarely write bugs anymore. What they write are *intent gaps* — places where the agent assumed one meaning and the human held another. With frontier models, the binding constraint on building complex systems is no longer code generation; it's creating, clarifying, and maintaining intent as a system grows and changes.

Terms used throughout — *arrow*, *drift*, *coherence*, *cascade*, *intent component* — are defined in the Glossary section near the end of this document.

Traditional intent-maintenance tools don't close the gap:

- **Tribal knowledge** requires a human longevity that teams rarely have and doesn't transfer between people.
- **Documentation** rots faster than it can be maintained; invaluable in 0-1, stale by year two.
- **End-to-end tests** are slow, which creates pressure to add mocks that silently lie.
- **Behavior-Driven Development (BDD)** frameworks are readable but separate spec from step definitions, forcing agents to load more files and still leaving drift detection to a human spotter.
- **Canaries** work well but are expensive and only cover production flows.
- **Modularization** reduces local complexity while worsening whole-system understanding — implicit contracts across subsystems multiply.

Agentic coding magnifies all of this. Each session brings a new capable programmer who doesn't share the previous session's context. `CLAUDE.md` and agent memory systems narrow the gap but don't close it. There remains a persistent mismatch between what's in the human's head and what's in the agent's context window.

LID reframes the problem: **code is no longer the artifact of attention. Intent is.** The agent is an english compiler; specifications are source; code is compiled output. A system is correct only when its *arrow of intent* — vision through design through requirements through tests through code — stays coherent top to bottom. LID exists to keep that arrow coherent with the minimum possible tooling.

## LID as a Structure for Intent

The clearest way to describe what LID *is*, rather than what it *does*, is that it is **a structure for the English you give your coding agent** — a layered way of writing intent at different levels of detail, from broad direction at the top down to the granular claims tests can verify. Agentic coding tools — Claude Code, Cursor, Windsurf, GitHub Copilot, Aider, Continue, Codex, JetBrains Junie, Zed, and their descendants — accept English as input and produce working software as output. They compile English into code. Unstructured English is too ambiguous to compile faithfully: the compiler guesses, the guesses drift, and the drift compounds across sessions. LID gives that English a shape the compiler can parse unambiguously. The artifacts look like documentation; their load-bearing job is to be source material an agent can compile without guessing. That source material is written in the project's own language — the domain words the user and the codebase already use — which LID structures rather than replaces; LID's own structural vocabulary is scaffolding for that structure, not a vocabulary the user must adopt.

Other spec-driven-development systems exist, and they are also structuring choices for the same kind of input. Read this way, LID is not in the "SDD methodology" category competing for the same slot; it is one particular structure with its own design trade-offs. LID's choices optimize for three things: *minimum surface* (few conventions for the user to learn), *continuous coherence across the whole project over time* (not just the next change), and *aggressive cascade downstream when intent changes*. Other structures make different choices — specialized agents, multi-step orchestration, enforcement layers, and so on. The question a project should ask is not "should I use LID?" but "how should the input to my English compiler be organized?" LID is one principled answer; others are others.

A practical consequence: **changes to LID are structure-design work, not tool-design work**. Adding a command adds a named slot in the structure. Changing a convention is changing how a slot is used. The minimum-system discipline named in Goal 2 is therefore not an aesthetic preference — it is the load-bearing design constraint that holds LID apart from structures that reach for orchestration or enforcement. Where others add machinery, LID leaves the work to the compiler (the agent) and to the project's own tooling.

The sections that follow describe LID's specific mechanisms — narrowing the latent space, linkage, semantic legibility, tests-first. Read them as the shape of this particular structure, not as a generic methodology. Every mechanism is there because it makes the resulting English more compilable by an agent that has not been in this project before.

## Approach: Narrowing the Latent Space

Frontier agents produce a vast range of plausible systems from any given prompt. Prompts never exhaustively specify intent — most of what the user wants remains latent, carried in their head and never written down. Without constraint, the agent samples from its distribution of plausible outputs; what it picks is usually close to the user's intent, but rarely exact, and the delta is the intent gap.

The fundamental purpose of LID is to narrow the agent's output distribution to the specific system the user actually had in mind. Specs narrow it. Tests narrow it. Linkage between them narrows it further. Every mechanism described in the sections below — explicit linkage, semantic legibility, tests-first — is, underneath, a technique for *edge detection*: a way for the agent to notice "I'm about to build something outside the user's intent" before it commits to doing so.

Specs, tests, and linkage narrow the decisions already in view. The gap that hurts most, though, is the decision *not yet in view* — the choice the agent will face in some future session that no spec anticipated. **Tenets** narrow that space ahead of time: a tenet is a one-line tie-breaker stating which way to lean when a decision has two defensible answers and no spec covers it. The discriminating test is the defensible opposite — a real tenet's reverse is a choice a different project could reasonably make; a statement whose opposite is absurd is a platitude that narrows nothing. A second test guards the other edge: a tenet is a *lean across a class* of decisions no spec anticipates, not a triggered rule. A candidate that reads as *when X, do Y* — a definite action behind a trigger — is a spec in a tenet's clothes and belongs in EARS, not the tenet list, even when its opposite is defensible. A tenet says which way to **lean**; a spec says what to **do**; a Key Design Decision records what was already **chosen**. Tenets are captured at the HLD phase, where project-wide preference belongs, ordered so the higher one wins a conflict, and they are edge detection for the decisions the arrow has not reached yet.

Framed this way, LID is less a documentation system than an **intent-narrowing system**. The artifacts happen to look like documentation, but their load-bearing job is constraint. The mechanisms in the sections below should be read with that frame in mind.

## Approach: Linkage-based Intent Tracking

Linkage is a narrowing mechanism: it gives the agent explicit paths to user intent, so the intent it is supposed to fit can be located cheaply and re-checked whenever an implementation decision approaches an edge.

Intent expressed in English documents does not naturally flow to its representation in code — certainly not in any project large enough to span more than one context window. Agents cannot hold the whole system in view at once, and English prose does not expose navigation points an agent can follow to find the code behind an intent, or the intent behind a piece of code.

LID's core mechanism is **explicit linkage**. The arrow of intent is walkable in both directions because each level of the arrow carries identifiers that point to the adjacent level:

- **Easy Approach to Requirements Syntax (EARS) specs** are single-line statements with globally unique IDs. An ID is the **root-to-leaf path** plus an optional within-leaf type/area segment and a number: `FEATURE-NNN` or `FEATURE-TYPE-NNN` in a flat project, the path extending one segment at a time as the tree deepens (`PEVAL-RUN-014`, `PEVAL-PERF-LOAD-003`). The leaf path is the cascade boundary; the optional trailing type/area segment groups specs *within* a leaf and is not a boundary. Because the path *is* the position, a single `grep` gathers all intent under any node (`grep PEVAL-PERF` returns the whole performance subtree), an agent finds the spec for an observed behavior in one search, and it finds every implementation of a spec by grepping the ID across code and tests. Resolving an ID to its owning design doc is one lookup against the leaf's `prefix:` frontmatter (or `index.yaml` where the overlay is present). (See `docs/decisions/namespace-structure.md`.)
- **`@spec` annotations** in code and tests point upstream from implementation to specification. A function tagged `// @spec IMPORT-002` is a navigable pointer: the agent loads one spec line, not the whole spec document.
- **Spec-file headers** point downstream by naming the artifact files they drive, closing the loop for discovery in the other direction.

The payoff is token-efficient traversal. An agent investigating a bug does not need to load the HLD, every LLD, and every spec to orient itself. The spec ID names the path: from a single `@spec PEVAL-PERF-LOAD-003` a prefix-grep gathers the segment's specs and code by construction, and one `prefix:`/`index.yaml` lookup resolves the ID to its owning leaf LLD; from there it walks leaf LLD → any sub-HLDs above it → the HLD, stripping a path segment to climb. In projects too large for a single context window, linkage is the only reliable way for an agent to locate intent quickly and act on it correctly — without it, the arrow of intent is a nice diagram but not something an agent can actually follow.

EARS syntax and `@spec` annotations are the specific implementations of this linkage principle. Projects large enough to need the `arrow-maintenance` overlay add a further layer — `docs/arrows/index.yaml` — which is a linkage manifest for the design tree. All three mechanisms exist to serve the same underlying goal: making the arrow walkable in tokens, not in hours of reading.

## Approach: Semantic Legibility as Cheap Linkage

Semantic legibility is a second narrowing mechanism — passive, carried by the code's own surface. Every name that echoes a spec is a reminder to the agent of the intent it is operating under, without requiring any spec file to be loaded.

Code is the last artifact in the arrow, but it is not outside the arrow. Agents navigate code semantically — via identifier names, type signatures, module boundaries, and file organization — before they navigate by explicit linkage. A descriptive function name, a type that encodes an invariant, or a module layout that mirrors an LLD is itself a linkage mechanism — cheaper than `@spec` because the code's own surface carries the intent.

Concretely: when an agent reads a function called `reconcile_overlapping_arrows` whose signature mentions `Scope` and returns `Result<ReconciledArrow, OverlapConflict>`, it has already traversed most of the arrow without loading a single spec. Names echo LLDs; types echo EARS invariants; module boundaries echo arrow boundaries. The agent only needs to consult the linkage when semantic navigation runs out — which is often, but much less often than if the code gave up no information on its own.

LID does not prescribe naming conventions, type system choices, or module layouts. These are language-specific and project-specific, and the moment LID dictates them it stops being a minimum system and starts being a style guide in competition with every language community's own conventions. What LID *does* claim is that agents follow the arrow more cheaply when the code's surface aligns with its intent, and that ignoring this cost is expensive over a project's lifetime. Code whose names and types disagree with the specs silently burns tokens on every future session — the kind of rot that does not show up in tests but does show up in the wall-clock time every change takes.

The principle: **specs are the authoritative linkage; semantic legibility is the cheap linkage; both compound.** Teams that care about either get the other nearly for free when they write code after specs and tests rather than before.

## Approach: Tests-first as Intent Preloading

Tests-first is the sharpest narrowing mechanism: the test is a hard, executable constraint compiled from the spec before the agent has committed to any interpretation of what the spec means.

Tests come before code in the arrow — not because verification is nice-to-have, but because writing tests first preloads the *use* of the target system into the context window before its implementation exists. Three effects follow:

1. **Code conforms more directly to intent.** The test is the first consumer of the API; its shape enforces interface discipline before implementation details have time to distort the design.
2. **Tests read as intent documents.** They describe behavior from the outside, which matches how EARS specs are stated. Tests written after code tend to reflect what the code happens to do, not what the spec wanted — the two drift apart silently.
3. **Systems built test-first are more testable by construction.** This compounds over the life of a project — testability tomorrow is paid for by test-first today.

In LID this is not a style preference. Tests sit between EARS and Code in the arrow because they are the mechanism by which intent transfers from specification into executable form. Skip tests-first and the arrow has a gap where agents silently fill in their own interpretation of what the spec wanted, producing code that passes their interpretation instead of the human's.

**When the artifact is prose, dogfooding substitutes for tests.** Tests-first applies to behavioral artifacts — things that run, produce state changes, and can be asserted against. Pure-prose artifacts (like the `linked-intent-dev` skill itself, whose "code" is instructions to an english compiler) have no runtime to assert against. For these, continuous dogfooding takes the place of the test layer: the artifact is exercised every time the system operates on itself, and divergence between intent and effect shows up as the dogfooding failure signals defined in Goal 4.

LID does not supply a test framework — that belongs to the user's project tooling. What LID supplies is the *discipline*: the `linked-intent-dev` skill requires tests to be written before the code that satisfies them (for behavioral artifacts), and the cascade order (EARS → Tests → Code) makes skipping tests visible as a broken arrow.

## Tenets

The operating principles that tie the preceding approaches to day-to-day work:

- **Intent leads; code is compiled output.** Specs are the source of truth. Code may be regenerated from specs; the reverse is not supported.
- **Docs carry current intent, written to be read cold.** A document carries the current intent as if authored fresh today, by someone who knew only that intent and nothing of the conversations, revisions, or debates that produced it. The test for any line: would that fresh author put it on the page? Three residues fail it — narration of how the intent changed; meaning that only resolves for someone who was in the conversation; and answers or rebuttals that exist only because a past discussion raised them. The keep-side of the same test is load-bearing: rationale, considered alternatives, and constraints that a fresh author would independently write from current intent stay — they are present intent, not residue. The doc tree is what travels to the next session; nothing else does.
- **Specs are authoritative linkage; semantic legibility is cheap linkage; both compound.** Explicit linkage (EARS, `@spec`) anchors navigation; well-chosen names and types reduce how often navigation is needed.
- **Speak the project's language.** LID expresses intent in the user's and the codebase's own domain vocabulary, not in LID's; its internal structural terms serve the methodology's own reasoning and are translated or glossed before they reach a doc the user reads or a prompt they answer.
- **Tests before code.** Tests preload intent into the context window so that code conforms to specification rather than implementation accidents.
- **Verticalize intent.** Keep intent navigable along one axis — the design tree — rather than a second navigation structure (an index, tag system, or registry) parallel to it. Cross-cutting intent is legitimate: a genuinely cross-cutting concern (monitoring, security, cost) is modeled as its own recognizable node that dependent nodes reference through the dependency graph (`blocks`/`blockedBy`), not spread as labels across many nodes nor catalogued in a side structure. The guard is against a second navigation axis, not against cross-cutting intent.
- **Intent attaches at the lowest node that dominates it; cascade within a segment, pause across.** A decision lives at the lowest design node whose subtree contains everything it affects — substance that would force a sibling node to change rises to their shared parent, while an obligation that merely lands downstream stays put and cascades a note. Within a segment cascade runs freely; across a boundary into another node's territory, stop and confirm before propagating, because real LLDs are uneven.
- **Minimum surface, maximum discipline.** LID's commands and conventions stay thin; the methodology may be as thick as the project requires.
- **LID runs on the agent, not a runtime.** Deterministic work is specified in prose for the agent to perform, not shipped as tooling the project must run; helpers may accelerate but are never required.
- **The user is always right — with warning.** A user may override a phase requirement; the skill warns about the drift risk and honors the override.
- **Stop and iterate at every phase** — for *generative* multi-phase workflows. After completing each phase of the linked-intent-dev workflow (HLD, LLD, EARS, tests, code), and after each sub-step of `/map-codebase`'s brownfield flow, the skill presents its output and waits for explicit approval before proceeding. Each stop is mandatory, not optional. Command-mode skills that execute a single directed pass (for example `/arrow-maintenance`'s audit-and-update) are not phase-structured in this sense — they produce a structured report at the end and surface individual findings for user judgment, but do not interrupt the pass at synthetic phase boundaries. The tenet applies where the workflow is producing intent; it does not apply to batch audit runs whose whole point is to execute directed action without further user gating.

## Goals

1. **Keep the arrow coherent.** When one level of intent changes, downstream levels cascade. Drift is detectable and repairable rather than silently accumulated.
2. **Stay a minimum system.** LID is a blueprint-and-workbench, not a factory. Every new command or skill is challenged; absorbing behavior into existing surface is the default over adding new surface.
3. **Meet teams where they are.** Two adoption modes — Full and Scoped — let solo users, scoped subsystems, full teams, and brownfield projects use LID at proportional cost. No boiling-ocean commitment required.
4. **Dogfood itself — falsifiably.** LID describes LID using LID, and this repository is the canonical mature-project example. Two concrete failure signals test the claim **as applied to this repository** (not to every user's LID project — user projects use LID, they do not falsify it): the **process signal** — every non-trivial change to `plugins/` must trace through an LLD or spec update, so an edit to a `SKILL.md` without a corresponding upstream change is a dogfooding violation — and the **coherence signal** — every behavioral skill has a navigable chain of LLD → EARS → evals, audited periodically by the `arrow-maintenance` overlay. Both signals are live here because this repo installs the overlay; projects that adopt LID without the overlay are not inside LID's dogfooding claim. Either signal going red means dogfooding has failed and the system needs repair.
5. **Make LID's value legible to those not yet using it.** The gap between "heard of LID" and "running LID" is itself an intent gap at project scale. LID's onboarding surface — the README, the marketing site, examples, and positioning content — is load-bearing intent, not distribution overhead. It cascades from this HLD like any other segment: claims that appear on the onboarding surface trace to specific HLD and LLD sections and must stay coherent with the system they describe. A site that oversells, that names capabilities LID does not have, or that drifts from the current LLDs fails this goal as cleanly as a broken test.

## Target Users

LID is for developers using agentic coding systems — Claude Code, Cursor, Windsurf, GitHub Copilot, Aider, Continue, Codex, JetBrains Junie, Zed, and their descendants — who have noticed that English is a surprisingly imprecise programming language. A prompt that feels complete in your head emerges as something close to, but not exactly, what you meant. Most of the delta is latent intent — constraints you assumed were obvious and never wrote down. The agent fills those in plausibly, sometimes correctly, often close-but-wrong, and the gap compounds: one session's close-but-wrong becomes the next session's starting assumption.

LID treats the agent as an *english compiler* (see Glossary) and adds the minimum scaffolding for that compilation to stay faithful to the intent it was given. The target user has already noticed the compounding problem and is looking for tooling that is opinionated enough to help and small enough not to get in the way. LID does not depend on any specific agent, harness, or IDE; the plugins described here ship for the plugin-capable hosts — Claude Code (richest integration) and Cursor — and rule-file adapters for tools without a plugin system are documented in `docs/setup.md`. The methodology applies anywhere a developer is compiling English into running software.

### Adoption modes

LID recognizes two adoption postures, which we call **modes**. A project is in exactly one mode at a time; `/update-lid` is the supported path between them.

| Mode | Who it's for | Arrow rigor |
|---|---|---|
| **Full LID** (default) | Whole project, team adopted | HLD and LLDs are anchors of truth. Code disagreeing with docs is a bug; cascade is aggressive. |
| **Scoped LID** | A bounded scope inside a larger non-LID project — a single feature, a package, a subsystem, or a service | Anchors of truth within scope; outside scope is untouched. Cascade halts at scope boundaries. Coverage scales with scope: narrow scopes have narrower sets of LLDs and HLDs that declare unspecified sections explicitly; full subsystems have the standard full arrow within their boundary. |

Every phase of the arrow is present in both modes — dropping any phase breaks linkage. The HLD is required as the universal floor. LLDs are required per intent component within scope; there can be many or few, but each intent component has one. EARS specifications are required everywhere EARS is the grep anchor that makes the arrow walkable in tokens, and removing it collapses the linkage the system depends on. Tests are required per TDD discipline. What varies between modes is *coverage*, not *phase set*: in Full LID, every intent component is fully specified along standard HLD sections (problem, approach, users, goals/non-goals, tenets, system design, key decisions, success metrics, FAQ); in Scoped LID, the HLD may mark sections as "not yet specified" rather than provide placeholder prose, and only components within scope receive LLDs. Slippage inside upstream docs is expected in newly-scoped projects, and cascade is restrained across scope boundaries so agents do not propagate incoherence from the unspecified region into the specified one.

LID files live in the project itself, not in per-user directories. Developers who want their LID artifacts private rather than shared with teammates add them to `.gitignore`. LID deliberately does not provide a "personal" mode routed through `~/.claude/` or similar — mixing LID into user-level directories risks conflicts with other tools and loses per-project scoping, and the gitignore path gets the same result with none of the complexity.

Brownfield adoption cuts across modes — a brownfield project can start in Scoped or Full LID depending on how the user wants to approach it. The `arrow-maintenance` plugin supports either path, mapping existing code into the tail of the arrow and working backward to fill in the LLDs and HLD that were never written.

## Architecture

LID is three layers.

### 1. Methodology

The arrow of intent:

```
HLD → LLDs → EARS → Tests → Code
```

Intent flows in one direction. Changes originate upstream and cascade down. Docs reflect *current* intent, not the history of how intent evolved — mutation, not accumulation.

**The design layer is a tree, not a single rung.** Most projects need only one HLD above a flat set of LLDs — the shape above, read literally. Large ones need depth: a subsystem whose intent is too deep for one LLD becomes an intermediate design doc that is HLD-shaped for its own subtree (a *sub-HLD*) and parents the LLDs beneath it. "HLD" and "LLD" are therefore roles relative to a node's position, not fixed types — the root is the HLD, the leaves own EARS, and any node between groups its children. Depth-2 is simply the shallow case; a flat project carries none of the tree's machinery, and nesting is a triggered exception taken only when a component outgrows one doc. (See `docs/decisions/recursive-intent-tree.md`.)

**Where intent attaches.** A decision or piece of intent lives at the lowest design node whose subtree contains everything it affects. If its substance would force a *sibling* node to change, it belongs to their shared parent; if it merely cascades an obligation into a sibling, it stays put and the sibling gets a cascade note. This one rule places intent at every level of the tree.

**Cascade.** Within a single arrow segment (one leaf LLD and its downstream specs, tests, and code), cascade runs freely. Across arrow boundaries — from one segment into another's territory — agents pause and verify before propagating, because real LLDs are uneven and aggressive cross-boundary cascade in an under-specified project propagates incoherence. A change at any non-leaf node fans out across its descendant segments, visiting each in turn and pausing to confirm that segment can absorb it; a change at the root HLD fans out across the whole tree.

### 2. Plugins

Three first-party plugins, distributed from this repository and run by plugin-capable hosts (Claude Code — the richest integration, with auto-invoking skills and phase gates — and Cursor). Two are core, installed together by default; one is opt-in:

- **`linked-intent-dev`** — three skills under one plugin. The pure-prose **`linked-intent-dev`** workflow skill (auto-triggered on code-changing prompts in Full mode; also invokable as `/linked-intent-dev` to start a fresh project — give it a description of what you want to build and the workflow handles bootstrap as part of Phase 1) walks every change through HLD → LLD → EARS → Tests → Code with stops at every phase boundary. **`/update-lid`** is an idempotent command for reconciling an already-configured project — drift, mode transitions, convention updates — and is also reachable as a sub-step from the workflow skill (Phase 1) and from `/map-codebase` when bootstrap is needed. **`/lid-coach`** is an advisory principle-review command that reads the project's current LID artifacts and produces a prioritized report of recommendations for getting more out of the methodology — it does not edit files. Mandatory.
- **`arrow-maintenance`** — navigation overlay (`docs/arrows/index.yaml`) plus two commands: `/arrow-maintenance` (audit-and-update pass; bootstraps the overlay on existing LID projects) and `/map-codebase` (brownfield bootstrap from raw code). Installed by default, **optional at runtime** — projects that do not need the overlay carry none of its overhead.
- **`lid-experimental`** — houses novel capabilities under evaluation for promotion into core: new intent-coherence mechanisms today, other behaviors over time. **Opt-in** — not installed by default; users who want LID's minimum surface ignore it. Each experiment walks the standard arrow, rooted in the plugin's LLD. Successful experiments are promoted into `linked-intent-dev` or `arrow-maintenance`; unsuccessful ones are retired. See *Experimental features as a separate plugin* under Key Design Decisions.

All three plugins are mode-aware. A skill detects the project's mode from its state and branches its behavior accordingly. Modes are therefore both a communication framing *and* a configuration axis — but the configuration lives inside skill logic, not as flags the user has to pass.

### 3. Distribution

The plugins are authored once and delivered through each host's native mechanism. A plugin's content — its skills (`skills/<name>/SKILL.md`), commands, and reference files — sits in a layout that plugin-capable hosts read directly; the only per-host artifact is a thin **manifest** that registers the directory as a plugin, plus a repo-root catalog listing all of them. Distribution is therefore **one shared content source plus one thin manifest per host**, never a forked copy of the skill text. Adding a host later adds its manifest format and leaves the shared content untouched.

**First-class plugin hosts.** Two today, each reading the same `plugins/` content through its own manifest:

- **Claude Code** — the richest integration (auto-invoking skills, phase gates). Reads `.claude-plugin/plugin.json` per plugin and a repo-root `.claude-plugin/marketplace.json` cataloguing all three:

  ```
  /plugin marketplace add jszmajda/lid
  /plugin install linked-intent-dev@jszmajda-lid
  /plugin install arrow-maintenance@jszmajda-lid
  /plugin install lid-experimental@jszmajda-lid   # opt-in
  ```

- **Cursor** — reads `.cursor-plugin/plugin.json` per plugin and a repo-root `.cursor-plugin/marketplace.json`. Cursor discovers the same `SKILL.md` skills and `commands/` natively; once published to Cursor's marketplace the plugins install from the marketplace panel or via `/add-plugin`.

Using each host's marketplace is a technical detail of that host, not a statement that LID accepts third-party plugin submissions — every plugin is first-party. Two core plugins (`linked-intent-dev` and `arrow-maintenance`) install together by default; `lid-experimental` is opt-in for novel capabilities under evaluation.

**Rule-file adapters (hosts without a plugin system).** Tools that read project instructions but have no plugin/skill system — Windsurf, GitHub Copilot, Aider, Continue, JetBrains Junie, Zed, Codex CLI, and any tool that reads `AGENTS.md` at the project root — use LID through a small adapter file committed to the user's project. Each adapter points the agent at the `AGENTS.md` that holds the project's LID workflow; the methodology is identical, and what differs is only how the agent is *reminded* of it each turn. These adapter files (one per tool, copy-paste ready) are documented in `docs/setup.md` and are **not** distributed by this repository — each user drops the one they need into their own project. This keeps LID minimum-surface: one `AGENTS.md` source of truth, N thin adapter pointers. The brownfield `/map-codebase` flow ships for Claude Code today — its multi-phase sweep orchestrates enough reading and subagent coordination that porting it to another host is a separate step; once a project is bootstrapped by any means, the resulting artifacts work identically under any tool.

This repository is simultaneously the distribution mechanism *and* the canonical mature-project reference — the `docs/` tree here is LID applied to LID.

**Versioning.** LID is versioned with semver per plugin (`plugin.json` `version`), and `linked-intent-dev`'s version is the canonical "LID conventions" version. The CHANGELOG — canonical in the core plugin — is the release record. A project records the conventions version its docs conform to as `- Version:` in its `## LID` block, and `/update-lid` version-walks a project forward when that recorded version lags the installed plugin.

**What warrants a version change.** The version tracks what a *downstream project* must or may act on — not every change to the plugins. **Major** marks radically new or breaking behavior; **minor**, an important structural or convention change a project would adopt; **patch**, a smaller change a project may act on. A change that asks nothing of existing projects — adding a supported host or platform, internal refactors, documentation — ships with **no version change**, held in the CHANGELOG's `## [No Version Update Required]` section, which folds into the next numbered version's entry when one is cut. (Introducing an experiment is typically a patch; changing a core skill is minor or major by the extent of the change.) This rule is load-bearing because `/update-lid`'s version-walk fires whenever a project's recorded version lags the installed one: bumping for a change that requires nothing of a project would trigger a no-op walk on every project, so withholding the bump is the correct, quieter behavior.

**Third-party ecosystem.** Because the core stays minimal (Goal 2), capability LID deliberately does not build — editor integrations, language servers, CLIs, CI coherence checkers — is built by independent third-party projects. LID encourages this ecosystem and makes it discoverable while hosting and running none of it: discovery is by an open convention rather than a registry LID operates. This is distinct from the first-party marketplace above — surfacing the ecosystem is not accepting submissions into it — and from `lid-experimental` (first-party capability under evaluation). The `extensions` segment owns the convention and the curated pointer; `marketing-site` surfaces the ecosystem as a trust signal that the methodology is in real use. (Detail lives in those segments, not here.)

### 4. Rule-file adapters (other agentic coding tools)

Tools without Claude Code's skill system (Cursor, Windsurf, GitHub Copilot, Aider, Continue, JetBrains Junie, Zed, Codex CLI, and any tool that reads `AGENTS.md` at the project root) use LID through a small adapter file committed to the user's project. Each adapter points the agent at an `AGENTS.md` that holds the project's LID workflow. The methodology is identical; what differs is how the agent is *reminded* of the workflow on each turn — Claude Code uses skill auto-invocation, other tools rely on the agent reading the rule file on every task.

The adapter files (one per tool, copy-paste ready) are documented in `docs/setup.md`. They are not distributed by this repository — each user drops the appropriate adapter into their own LID project. This keeps LID itself minimum-surface: one `AGENTS.md` source of truth, N thin adapter pointers.

The brownfield `/map-codebase` flow is Claude-Code-specific today — the multi-phase codebase sweep orchestrates too much reading and subagent coordination to drive from a rule file. Once a project is bootstrapped (whether through `/map-codebase` or manually), the resulting artifacts work identically under any tool.

## Key Design Decisions

### The arrow for LID itself

LID-on-LID has a three-variant arrow depending on what kind of skill is being specified:

- **Pure-prose skills** shape how the agent approaches work without executing a definite procedure. The `linked-intent-dev` skill itself is canonical: it guides agent behavior during code changes, but has no start, end, or checkable output. Arrow: `HLD → LLD → SKILL.md + references/`. Verification is continuous dogfooding.
- **Behavioral skills** are those a user deliberately invokes (explicitly via a slash command, or implicitly when a user request matches the skill's trigger description) to execute a procedure that produces a verifiable project-state change. `/update-lid` and `/map-codebase` qualify — they create files, edit the project's agent-instructions file, or generate arrow docs. Arrow: `HLD → LLD → EARS → evals + SKILL.md + references/`. EARS specs anchor the assertions evals check.
- **Dual-mode skills** have two invocation modes with different user-intent postures:
  - *Ambient mode* — auto-triggered when a detection signal matches project state. Posture is **catch and recommend**: the agent notices relevant work, surfaces findings, and edits only as the surrounding conversation authorizes. File writes are allowed but happen opportunistically.
  - *Command mode* — the skill is explicitly invoked as a slash command. Posture is **directed action**: the user has asked for the pass, so the skill proceeds assertively through audit and update.

  The `arrow-maintenance` skill is canonical: ambient guidance when `docs/arrows/` is present, directed audit-and-update when invoked as `/arrow-maintenance`. Arrow for the command-mode assertions: `HLD → LLD → EARS → evals + SKILL.md + references/`. EARS cover command-mode behavior; ambient-mode behavior is verified by dogfooding.

The pragmatic test: does the skill support both auto-trigger and explicit slash-command invocation? If yes, dual-mode. If only auto-trigger, pure-prose. If only command invocation, behavioral. Each LLD declares which variant applies to its skill, so downstream work is unambiguous.

**Content artifacts.** Non-skill artifacts in this repository — the marketing site, examples, and similar content produced for an outside audience — follow the behavioral-skill arrow shape: `HLD → LLD → EARS → content + assets`. EARS is retained because linkage matters independent of artifact kind; spec IDs give content the same `grep`-addressable anchors that skills have, let site claims trace back to specific HLD and LLD sections, and make drift between content and current intent detectable through the same cascade mechanics as code drift. Verification substitutes content-appropriate mechanisms (build-time link and structural checks, dogfooding content review against the HLD) for test-harness evals, but the arrow is structurally identical and the content-artifact case is not a separate variant.

### Code and tests for LID

**Code = skill prompts, reference files, templates, plugin manifests.** A `SKILL.md` collapses spec and implementation into a single artifact — intent expressed as instructions to the english compiler. There is no separate translation step between "what the skill should do" and "the text the model reads," which is why EARS is unnecessary for pure-prose skills: the LLD and the SKILL.md are already adjacent levels of the same description.

**Tests = two layers:**

1. **Dogfooding** (continuous). LID-on-LID is the integration test. Every change to a LID skill is tested implicitly by the next LID operation performed in this repository. If LID cannot specify LID, LID is broken.
2. **Behavioral evals** (per-skill gate). `skill-creator`'s eval harness runs scenario-based tests on behavioral skills: with-skill vs. baseline runs, graded assertions, HTML review, and description-optimization for trigger accuracy. Evals run whenever an LLD change mutates a behavioral skill; a passing eval suite is the gate for merging the change.

### Linkage without prompt pollution (LID-on-LID only)

In LID-on-LID, the `@spec` annotation direction inverts. A SKILL.md body is prompt; the model reads it as instruction, so embedding spec IDs in its prose would bend behavior at runtime. For LID's own skills, the upstream spec owns the pointer to its downstream artifact rather than the other way around — the authoritative end holds the linkage, and the artifact stays clean.

The operational specifics — spec file header format, eval metadata schema, the clean-SKILL.md rule — live in the `linked-intent-dev` plugin LLD.

This inversion is specific to prompt artifacts. In normal user projects where code is the artifact, the convention is standard: `@spec` annotations live in the code, and spec files do not carry downstream artifact pointers.

### Minimum-system discipline — the why

LID is minimum by design, not by omission. The reasoning is pragmatic division of labor: agentic coding tools — models, harnesses, IDEs, memory systems — are evolving rapidly and continue to absorb capabilities that once required explicit tooling. LID does not compete with that evolution. It concentrates on the part of the problem that does *not* move quickly: a human user articulating their intent clearly over time and keeping that articulation coherent as the system grows.

**Minimum system applies to LID's own surface — the commands, skills, plugins, and conventions users have to learn.** It does not apply to the user's methodology. The arrow of intent is as thick as the project requires; LID simply provides the thinnest tooling layer that can support it. Planning guidance is one example: agent harnesses now generate implementation plans natively, so LID does not mandate a `docs/planning/` artifact. What LID contributes is the *discipline* (use linkage, write tests first, cascade on change), baked into the `linked-intent-dev` skill rather than carried in a separate phase document.

Every capability LID does not have is a capability delegated to the fast-moving layer. Validation, cascade enforcement, diagram rendering, code generation, test running — these belong to the agent, the user's IDE, the user's own tooling, or increasingly a third-party extension ecosystem (see *Distribution*). LID's job ends at "the intent is specified and linkable." The agent takes it from there.

This is why surface growth is aggressively resisted. A new command or skill is not just cognitive load for the user; it is LID reaching into territory the fast-moving layer will handle better next quarter. When a proposal arrives, the first question is: *can the existing surface absorb this, or is the agent about to absorb it anyway?* Only if both answers are no does a new surface get considered — and even then, the surface lands first in the `lid-experimental` plugin (see *Experimental features as a separate plugin* below), where it must earn community adoption before being promoted into core.

### Cursor as a first-class plugin host

Cursor is a first-class plugin host alongside Claude Code, not a rule-file adapter. Its native plugin marketplace reads the same `SKILL.md` format (`name`/`description` frontmatter), the same `skills/<name>/` and `commands/` layout, and the same Agent-Skills discovery LID already uses — so LID's plugins install and auto-invoke there from one shared source, differing only by a `.cursor-plugin/plugin.json` manifest beside the `.claude-plugin/` one. The cost LID accepts is a second manifest set and a marketplace-review relationship — the same cost already accepted for Claude Code, not a new class of cost.

LID adds **no host-detection machinery** — no `--host` flag, no runtime host sniffing, no mirroring between `CLAUDE.md` and `AGENTS.md`. The project's instruction file is `AGENTS.md` (the cross-tool convention; under Claude Code `CLAUDE.md` is a symlink alias), and Cursor reads `AGENTS.md` natively, so the same skills read mode, version, and workflow from whatever file the host presents without branching on host identity. A detection layer would be surface LID does not need — the kind minimum-system discipline rejects.

### Modes: detection and transitions

**Detection.** Each LID project declares its mode in its agent-instructions file under a `## LID` metadata block:

```markdown
## LID
- Mode: Full
- Version: 1.2.0
```

The skill reads the `- Mode:` bullet for the project's mode and the `- Version:` bullet for the `linked-intent-dev` conventions version the docs conform to (see *Versioning* under Architecture). The instruction file is the right location because it is already the bootstrap entry point — the host reads it unconditionally on entering a project, so detection costs zero extra file loads. That file is `AGENTS.md` (the cross-tool convention) or `CLAUDE.md` under Claude Code; in this repository `CLAUDE.md` is a symlink to `AGENTS.md`, so the two are one file. Mode is a project-global property, not a per-document one, so the instruction file is the appropriate scope rather than frontmatter on individual docs. **If the block or its `- Mode:` bullet is missing, the skill defaults to Full LID** — the more rigorous mode, erring on the side of more specification rather than less.

**Transitions.** Modes change in both directions, but the user always drives reconciliation:

- **Promotion (Scoped → Full)** migrates arrow artifacts from scope-local locations into the standard Full LID positions (the `docs/intent/` design tree and `docs/high-level-design.md`). Where multiple scoped arrows overlap — e.g., two subsystems each holding a partial HLD — the user works with the agent to reconcile the overlaps into a single coherent intent. There is no automatic merge; overlapping intents are an upstream problem the user must resolve.
- **Demotion (Full → Scoped)** is supported but unusual — typically it signals the team stepping back from LID. Arrows remain in place; the mode marker changes and cascade rigor relaxes.

`/update-lid` drives these transitions. Manual edits work, but the command also cascades file-layout and convention changes the new mode implies.

### Arrow-maintenance stays a separate plugin

Arrow-maintenance is installed alongside `linked-intent-dev` by default but remains a distinct plugin. Small projects carry zero runtime overhead from it. The core skill references arrow-maintenance without depending on it — a belt-and-suspenders relationship, where arrow-maintenance catches drift the core cascade should have caught, and becomes load-bearing only in modes where code exceeds one context window.

### Experimental features as a separate plugin

Novel capabilities — new intent-coherence mechanisms today, other behaviors over time — are housed in a third plugin, `lid-experimental`, installed opt-in alongside the core plugins. The separation is load-bearing. Minimum-system discipline (Goal 2, and the *why* above) keeps LID's core surface thin and resists speculative additions, but real progress requires somewhere to try ideas under realistic conditions. The experimental plugin is the sanctioned route. Users who want to try a candidate capability install the plugin; users who want LID's minimum surface ignore it; either choice is fine and neither imposes runtime cost on the other.

Each experiment walks the standard arrow, rooted in the experimental plugin's LLD, with EARS specs, tests or evals, and the same cascade discipline as core. Experimental status is a marker on the surface, not a relaxation of the underlying coherence requirement — experiments earn their keep by being legibly designed, not by being exempt from design.

Two outcomes are explicit at adoption time:

- **Promotion** into `linked-intent-dev` or `arrow-maintenance` when an experiment accumulates community adoption and concrete real-world value stories that make baking it into core a clear win. Promotion migrates the experiment's LLD and specs into the receiving plugin; the experimental version is removed in the same change.
- **Retirement** when an experiment fails to find adoption, or when the fast-moving tooling layer LID delegates to (per the minimum-system reasoning) absorbs the capability LID was probing. Retirement removes the artifact rather than marking it deprecated — mutation, not accumulation.

The repository publishes each experiment as it lands and actively seeks community feedback to inform the promotion-or-retirement decision. The feedback channel and cadence are aspirational at this stage and will firm up as the first experiments arrive, but the commitment to evaluating experiments in the open — rather than in private — is structural.

## Glossary

Core terms, with the meaning they carry across LID documents.

- **Arrow (of intent)** — the unidirectional chain from vision to code: HLD → LLDs → EARS → Tests → Code. Strictly speaking the arrow is a directed acyclic graph of intent (many LLDs depend on one HLD; many specs on one LLD; many tests and code files on one spec), but "arrow" captures the load-bearing property — intent flows in one direction, never upstream. A project has one arrow overall. Its design layer (HLD → LLDs) may be a single rung or a tree of nested design docs; the chain above is the shallow, common case.
- **Arrow segment** — the territory owned by one *leaf* LLD: the LLD itself and the specs, tests, and code that cite its EARS IDs. (Intermediate design nodes group segments; they do not own one.) When the docs say "within-arrow" or "within an arrow" they usually mean within a segment.
- **Arrow boundary** — the edge between two arrow segments. Defined operationally by the EARS ID's leaf prefix: two specs whose IDs resolve to different leaf segments belong to different segments. Cascade pauses at a boundary.
- **Cascade** — propagating a change downstream through the arrow (e.g., an LLD change → spec updates → test updates → code updates) within the same session so adjacent levels stay coherent.
- **Cascade rigor** — how aggressively cascade runs. Full LID cascades on any detected drift; Scoped LID cascades within a declared scope only and relaxes when upstream docs are uneven.
- **Placement rule** — intent attaches at the lowest design node whose subtree contains everything it affects; substance that would force a sibling node to change rises to their shared parent, while a mere downstream obligation stays put and cascades a note to the sibling.
- **Decision doc** — a standalone record of one design decision (context, the elements that decide it, options, selection), written to be re-run by a cold reader. Lives in its owning node's `decisions/` directory, owns no EARS, and carries no spec IDs. Reserved for the rare decision that stays *live* once it lands — one a cold reader of the result would still question or try to reverse without the full tradeoffs. A choice that reads as obvious or native once landed needs neither a doc nor a row; most decisions worth recording are a row in an LLD's Decisions & Alternatives table.
- **Coherence** — the property of each level of the arrow agreeing with its adjacent level: specs match the LLD; tests match the specs; code passes the tests. The arrow is coherent when all adjacent pairs agree.
- **Drift** — divergence between adjacent levels of the arrow that has not yet been repaired by cascade. Drift accumulates when changes are made at one level without the downstream levels being updated.
- **Edge detection** — the agent noticing where its interpretation of a spec is about to diverge from the user's latent intent, before committing to an implementation. Tests, specs, and linkage are all edge-detection mechanisms.
- **English compiler** — the agent considered as a translator from English specifications to code, analogous to a traditional language compiler translating source to machine code.
- **HLD (High-Level Design)** — the project-level design doc describing problem, approach, users, goals/non-goals, system design, key decisions, success metrics, and references. One per project; it is the **root** of the design tree.
- **Sub-HLD** — a non-root design node that is HLD-shaped for its own subtree: it carries the design framing its children inherit and parents them, but owns no EARS directly. "HLD" and "LLD" name *roles by position*, not fixed types — a sub-HLD is an LLD to the node above it and an HLD to the nodes below. A sub-HLD is earned by **shared parent intent** — a problem, approach, or decisions spanning its children that a parent design doc *should* capture; the test is whether such a doc should exist, not whether one already does. A merely categorical grouping with no such shared intent is a **taxonomy label** (cf. `docs/arrows/index.yaml`'s `taxonomy` field): it may organize nodes for navigation but is not a design node, gets no parent doc, and its members stay flat leaves.
- **Design tree** — the design layer viewed as a tree: the root HLD at top, leaf LLDs (which own EARS) at the fringe, sub-HLDs grouping children in between. Depth-2 (one HLD, flat LLDs) is the shallow, default case.
- **LLD (Low-Level Design)** — a component-level design doc; the leaf of the design tree, owning the EARS for its segment. One per intent component. A node carries the sections it needs — the HLD and LLD templates are starting points, not rigid types — and a leaf that outgrows itself promotes into a sub-HLD with leaf children.
- **EARS (Easy Approach to Requirements Syntax)** — a format for single-line, uniquely-IDed requirements optimized for `grep`-based traversal. An ID is the path from the root to the spec's segment, so its prefix locates it in the design tree.
- **Intent component** — a distinct unit of system intent that warrants its own design node. A component is what the user would describe as "a thing" — a skill, a service, a subsystem, a feature. A small component is one leaf LLD; a component whose intent has internal depth is a sub-HLD with child components beneath it.
- **Intent gap** — the delta between what the user meant and what the agent produced. LID's central problem.
- **Linkage** — explicit identifiers that let an agent walk from one level of the arrow to adjacent levels without loading the whole document — EARS IDs, `@spec` annotations, spec-file headers.
- **Orphan / reverse orphan** — an *orphan* is a code or spec artifact not referenced by any arrow segment. A *reverse orphan* is the inverse: a `@spec` annotation (in code or tests) that points to a spec ID which does not exist anywhere in the spec files. Both are drift signals surfaced by audit.
- **Behavioral skill / pure-prose skill** — a behavioral skill produces verifiable project-state changes when invoked (e.g., `/update-lid` edits files). A pure-prose skill shapes how the agent approaches work without producing a definite artifact (e.g., the `linked-intent-dev` workflow skill).
- **Experimental plugin / experiment** — `lid-experimental` is the opt-in third plugin that houses novel capabilities under evaluation for promotion into core. An *experiment* is one such capability. Experiments walk the standard arrow and are published for community feedback; successful experiments are promoted into a core plugin, unsuccessful ones are retired.
- **TDD (Test-Driven Development) / BDD (Behavior-Driven Development)** — standard acronyms retained for reference. LID adopts TDD as a load-bearing discipline; BDD is discussed only as a comparison in the Problem section.

## Non-Goals

- **Not a factory.** LID does not generate code, run pipelines, or orchestrate agents. It is a methodology plus a skill layer. The user's project retains its own build, test, and deploy tooling.
- **Not a replacement for user-project tests.** LID evals test LID skills. User projects keep their own test suites, shaped by their own EARS specs and their own domain.
- **Not a linter or validator.** LID does not enforce the arrow with pre-commit hooks, CI gates, or blocking checks. Enforcement is conversational — the agent consults the skill at authoring time, and cascade happens during the change rather than after. A user who bypasses the skill and edits code directly faces no tooling obstacle; the cost of bypass falls on them when drift accumulates. This is deliberate. Adding enforcement would undo minimum-system and put LID in competition with the fast-moving tooling layer rather than complementing it.
- **Not adversarial security review.** LID does adversarial *coherence* review — `bidirectional-differential`'s blind EARS↔code round-trip and `lid-coach`'s cold-read pass — to surface drift between intent and implementation. It does not do adversarial *security* review (threat modeling, penetration testing, or vulnerability analysis); that stays with the user's own security tooling and process.
- **Not prescriptive about existing conventions.** When a project already has diagram styles, file layouts, or doc conventions, LID detects and respects them. The defaults (Mermaid for diagrams, `docs/` for specs) apply only where no convention exists.
- **Not a migration tool.** LID is compatible with codebases that already have BDD, spec-driven-development, or other intent-tracking systems, but does not convert, consume, or replace their artifacts.
