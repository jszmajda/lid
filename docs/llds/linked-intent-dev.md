# LLD: linked-intent-dev Plugin

**Created**: 2026-04-18
**Status**: Design Phase

## Context and Design Philosophy

The `linked-intent-dev` plugin is the mandatory core of LID. It translates the methodology described in the High-Level Design (HLD) into two artifacts: a pure-prose skill that shapes how the agent approaches code changes, and a behavioral skill that bootstraps and maintains project state. This Low-Level Design (LLD) describes intent; the `SKILL.md` files and references under `plugins/linked-intent-dev/` are the compiled outcome. Terms like *arrow*, *segment*, *drift*, *coherence*, and *cascade* are defined in the HLD's Glossary section.

**A note on actors.** Throughout this document, "the skill" refers to the prose guidance contained in a `SKILL.md`. The skill does not act on its own — it is content the agent consults. When this LLD says "the skill surfaces X" or "the skill warns," the mechanism is: the agent, after consulting the skill, performs the surfacing or warning in the assistant turn it produces. The skill is the instruction; the agent is the actor.

Two design constraints shape the plugin:

- **Minimum surface.** The plugin exposes one pure-prose skill and one behavioral skill (with an alias). Any capability that can live inside those two is absorbed into them rather than given its own entry point.
- **Describe, do not dictate.** This LLD describes the *behavior* each skill should produce. It does not prescribe the exact wording of skill prompts. The prompt is the implementation; its phrasing is free to change as long as the described behavior is preserved and the EARS specs pass.

## Plugin Structure

The plugin lives at `plugins/linked-intent-dev/` with this shape:

- `.claude-plugin/plugin.json` — Claude Code plugin manifest (name, version, skills listing).
- `skills/linked-intent-dev/` — the pure-prose workflow skill.
  - `SKILL.md`
  - `references/` — supporting reference docs (EARS syntax, LLD template, HLD template).
- `skills/lid-setup/` — the behavioral bootstrap/update skill.
  - `SKILL.md`
  - `references/` — CLAUDE.md template fragments keyed by mode.
- `commands/` — command stubs that route `/lid-setup` and `/update-lid` to the `lid-setup` skill.

The plugin intentionally does not bundle scripts. Everything the skills do is expressed in prompts and references; there is no code layer between the skill and the agent's tool use.

## The `linked-intent-dev` Skill (pure-prose)

### Intent

Shape the agent's approach to every code change in a LID project so that intent flows HLD → LLD → EARS → Tests → Code, and so that drift is caught at the earliest level where it originates. This skill does not execute a procedure; it guides the agent's workflow through a sequence of checkpoints and reminds it of cascade discipline at arrow boundaries.

### Triggering

The skill declares itself relevant for all prompts that propose changes to project code or specifications. Triggering is *mode-aware*:

- **In Full LID**, the skill triggers broadly — any prompt that could result in a code change is in scope.
- **In Scoped LID**, the skill additionally checks whether the files or subsystems the prompt touches fall within the declared scope. If the prompt is entirely outside scope, the skill does not trigger. If any touched area is in scope, the skill triggers. For prompts that do not reference any specific file paths, the skill defaults to triggering (benefit of doubt) and asks the user to confirm scope applicability when the situation is ambiguous.

### Scope declaration format (Scoped mode)

A Scoped-LID project declares its scope in `CLAUDE.md` immediately after the `## LID Mode:` heading, in a `## LID Scope` section:

```markdown
## LID Mode: Scoped

## LID Scope

Paths in scope:
- `src/auth/**`
- `packages/billing/**`
- `apps/mobile/src/services/auth/**`

Paths explicitly excluded (even within in-scope roots):
- `src/auth/legacy/**`
- `**/*.test.ts`
```

Rules:

- Patterns follow gitignore-style glob semantics. A trailing `/**` matches any path under the directory; a leading `**/` matches at any depth.
- A file path is "in scope" when it matches at least one pattern in *Paths in scope* and matches no pattern in *Paths explicitly excluded*. Exclude wins when both match.
- The "Paths explicitly excluded" list is optional; when absent, only the include list governs.
- When the mode is Full, the `## LID Scope` section is **omitted entirely** from CLAUDE.md. The skill treats a missing `## LID Scope` as "entire project is in scope."
- A Scoped-mode project with a missing or empty `## LID Scope` section is a misconfiguration: the skill defaults to triggering on all prompts and surfaces a one-line warning that scope has not been declared (same fallback as before the format was finalized). The user should run `/update-lid` to declare scope.

The skill errs toward over-triggering rather than under-triggering. An over-triggered consult costs a handful of tokens; an under-triggered one lets drift accumulate silently. To keep over-triggering cheap, the SKILL.md body contains only guidance universal to every consult — the mode-aware dispatch, the phase list, the cascade rule. Per-phase and per-mode expansions (EARS syntax, LLD template, HLD template, cascade edge cases) live under `references/` and are loaded only when the relevant phase is entered. This keeps the always-loaded surface small enough that the skill can trigger liberally without burdening the user's context window. Description optimization via `skill-creator`'s `run_loop.py` remains available for calibrating trigger accuracy over time.

### Workflow checkpoints

Two rules govern every phase below.

**Stop and iterate at every phase boundary.** After completing each phase, the agent presents its output to the user, incorporates numbered feedback, and proceeds only on explicit approval. Each stop is mandatory, not optional. Skipping stops is the single most common way this workflow degrades into a rush — the discipline is non-optional. This matches the HLD tenet of the same name.

**Before starting (or resuming) implementation, run a coherence pre-flight.** Verify that the current state of HLD, LLDs, EARS specs, and tests are mutually coherent for the segment about to be touched — do EARS specs trace to the current LLD? Do tests trace to current EARS? Does the LLD still reflect the HLD's architecture? If drift is detected, fix the docs first and only then implement. A resumption check prevents one session's drift from being compounded into the next session's change.

When the skill triggers, it guides the agent through six phases:

1. **HLD check** — does a top-level HLD exist? Does it cover the domain of the change? If the change alters the project's architecture, the HLD is updated first. For consequential architectural changes (new approach, significant trade-off, new mode), the agent first **sketches 2–3 competing options** (~200 words each, naming downstream consequences) and presents them for user selection before committing to a full HLD draft. Surfacing decisions as *choices among alternatives* — rather than as the agent's best guess — is the primary edge-detection mechanism at the HLD level.
2. **LLD check or draft** — does an LLD exist for the intent component being changed? If not, draft one before downstream work. In complex projects multiple LLDs may look semantically relevant; the skill helps the user select the correct one by surfacing candidates and their scopes rather than silently picking. If an LLD exists, confirm coherence with the change and update as needed. After drafting or substantially revising an LLD, the agent runs an **LLD-level edge-case probe** — a list of "what happens when..." questions pointed at *this LLD's own gaps*: missing state transitions, unstated invariants, unspecified API error shapes, ordering assumptions inside the component. Cross-component interactions and cross-spec ambiguities are the target of Phase 4, not here. When a subagent is available the probe is delegated to it for cleaner, less-biased coverage. The user triages the gap list and decides which gaps to fix in the LLD vs. defer as open questions.
3. **EARS spec draft or update** — every LLD change produces a corresponding EARS update (new specs, revised specs, or deleted specs). Spec IDs are stable; revisions mutate text, not IDs, unless scope genuinely changes. Deleted IDs are not reused — "what is currently here is the truth," and git preserves the history. After drafting or revising specs, the agent runs **post-draft consistency verification**:
   - **Coverage** — are there behaviors described in the LLD that have no corresponding EARS spec?
   - **Contradiction** — do any specs say different things about the same behavior?
   - **Implicit scoping** — are any specs phrased as universal when they actually apply only to one context? When the current change adds a new mode or variant, audit sibling specs for scope that was implicit when only one variant existed (see `ears-syntax.md § Scope Disambiguation` for the full litmus).
   The agent presents a brief consistency report alongside the specs; the user resolves issues before approval.
4. **Intent-narrowing edge audit** — distinct from the LLD-level probe in Phase 2 in what it targets. Phase 2 looked inside one LLD for its own gaps; Phase 4 looks across LLD + specs together for cross-spec and cross-segment divergence:
   - Interactions between this LLD's specs and a sibling segment's specs (who owns what state?).
   - Specs that read cleanly in isolation but admit two different behaviors when composed with another spec in the same segment.
   - Namespace or feature-prefix ambiguity (does spec X apply to mode A, mode B, or both?).
   - Sequencing ambiguity across specs (if A and B are both required, does order matter?).
   - Places where the user's latent intent is probably narrower than what the specs literally allow.

   The skill surfaces these and asks the user to resolve them before tests are written. LID's fundamental purpose — narrowing the agent's output distribution to the user's latent intent — is carried by this step more than any other.
5. **Tests-first** — tests are written *before* the code that satisfies them, per the HLD's intent-preloading rationale. Tests carry `@spec` annotations citing the EARS IDs they verify. The skill does not proceed to code until tests exist and fail in the expected way.
6. **Code** — implementation follows. Code carries `@spec` annotations placed at the *entry point of the behavior's implementation graph* — the topmost function or module that owns the specified behavior, not every helper in its subtree. When a behavior spans multiple subsystems (e.g., UI + API + database), annotate at the entry point in each subsystem. Tests follow the same rule: annotate the test that directly exercises the spec, not every assertion. On completion, the skill runs **coherence verification** (see below).

### Coherence verification

Phase 6 ends with a two-layer coherence pass.

**Structural checks (deterministic; soft-block completion):**

1. All tests pass.
2. Every `@spec` annotation in the changed files points to a spec ID that exists in a spec file.
3. Every behavioral EARS spec cited by the LLD has at least one test citing it.
4. No spec file references a deleted spec ID (either in headers or in cross-references).

*Soft-block* means the skill will not consider the change "complete" until these pass, and surfaces the failure clearly. The user can override per the user-is-always-right tenet — this is not a CI gate or a linter, consistent with the HLD's "not a linter or validator" non-goal. The skill makes the cost visible; the user decides. When the project declares a coherence script under `## LID Tooling` in `CLAUDE.md`, these structural checks may be delegated to that script (see `docs/llds/arrow-maintenance.md § Reference tooling`); without a declaration, they are performed in-prompt.

**Semantic checks (agent judgment; surfaced, do not block):**

1. Do the updated specs describe behavior consistent with the LLD?
2. Does the updated LLD match the HLD's architecture?

The agent re-reads each adjacent level of the arrow for the changed segment and produces a short narrative report: for each spec/LLD/HLD pair, either "consistent" with a one-line justification or "needs review" with a specific point of tension. Semantic findings are surfaced for user review but do not block the change, because "match" at the prose level is judgment, not a theorem.

If the user overrides a phase ("skip EARS here", "skip tests for this change"), the skill warns about the drift risk and honors the override. The user is always right; the skill's job is to make the cost visible, not to block.

### Cascade discipline

**Cascade** is this: when a change is made at one level of the arrow (HLD, LLD, EARS, tests, or code), the levels *downstream* of that change are reviewed and updated in the same session so the arrow stays coherent. A spec change implies potential test and code changes; an LLD change implies potential spec/test/code changes; an HLD change implies potential LLD/spec/test/code changes. Cascade is the mechanism by which intent changes propagate to implementation without manual follow-up, and its absence is what lets drift accumulate silently.

The skill enforces cascade at arrow boundaries. *Within* one segment — one LLD and the specs, tests, and code that cite its EARS IDs — cascade is free: the agent updates downstream levels in the same session without further confirmation. *Across* segment boundaries, the skill pauses. A change whose effect crosses from one LLD's territory into another's is flagged to the user; the agent asks before propagating into the adjacent segment, because real LLDs are uneven and aggressive cross-boundary cascade propagates incoherence from under-specified regions into well-specified ones.

Arrow boundaries are defined by the EARS spec ID prefix convention: specs sharing a `{FEATURE}` prefix are in the same segment; specs with a different prefix belong to a different segment. This makes the boundary check a simple prefix comparison rather than a structural analysis. When two segments would naturally collide on a prefix (two unrelated features both named, say, `USER`), the skill asks the user to supply a disambiguating namespace prefix rather than silently coalescing them.

**Cascade and uncommitted work.** When cascade would touch files the user has uncommitted changes in, the skill warns with a description of the intended changes and proceeds only after confirmation. It does not silently edit over pending work.

**Cascade and inconsistent arrows.** Arrows are often inconsistent — mid-transition aborts, overlapping scoped arrows, partial cascades from prior sessions. When the skill notices an inconsistency it surfaces it with a description of what it found. Resolving inconsistency is a userland decision, assisted by the agent; the skill does not auto-repair. The `arrow-maintenance` overlay is where systematic inconsistency-hunting lives — this skill only flags what it notices along the way.

**HLD-originating cascade.** Changes that start at the HLD level fan out across *every* segment of the arrow by construction — an HLD change is a new architectural stance that each LLD has to be reviewed against. In that case "within-segment free, across-segment pauses" cannot apply uniformly; the skill walks the affected LLDs in turn, pausing at each segment to confirm the change lands cleanly before cascading to that segment's specs, tests, and code. The user sees one pause per affected segment, not one grand pause at the start.

**Lifecycle events.** When a cascade implies a split, merge, or rename of a segment (for example, an HLD change that dissolves a segment's boundary with another), the skill defers to the mechanics described in the `arrow-maintenance` LLD's Lifecycle Events section rather than re-specifying them here. Lifecycle events are first-class there; this skill recognizes them and hands off.

### Bug fixes

Bug fixes are not a special case. They walk the arrow like any other change: find where the behavior diverged from intent, determine whether intent needs to change, is already expressed but wrong, or was never expressed at all, and cascade from there. Fixing code without walking the arrow is a bypass — the skill warns but does not block, per the user-is-always-right tenet.

### Brownfield LLD content

LLDs for reverse-engineered components start with incomplete or inferred content. They use the **same template and same section structure** as greenfield LLDs — there is no separate brownfield LLD format. What varies is the content's starting state:

- **Decisions & Alternatives** table entries carry `[inferred]` in the Rationale column when a decision was observed in code rather than authored by the user. As the user confirms or refutes the inference in subsequent sessions, the `[inferred]` marker is removed and the rationale is written out, or the decision is revised.
- **Open Questions & Future Decisions** holds observed-but-unexplained behaviors and technical debt discovered during reconnaissance. These migrate out (into Decisions, into specs, or into a planned remediation) as the user engages with the code.
- **Major sections** may describe current state alongside intended behavior when the two differ; flag the divergence explicitly rather than pretending the code matches intent.

As a brownfield LLD matures through normal LID cascades — each change triggers the skill's phased workflow — inferred content becomes authored content. No migration command is needed and no "graduation" step is triggered; the LLD simply evolves in place under the standard cascade discipline. This matches the HLD-level convention for Scoped LID (HLD sections may be marked "not yet specified" and filled in over time).

## The `lid-setup` Skill (behavioral)

### Intent

Put a project into a LID-ready state. On first run, bootstrap the required directory structure and inject LID directives into `CLAUDE.md`. On subsequent runs, reconcile the project's current state with the conventions LID expects and, if requested, migrate between modes.

### Invocation

The skill is invoked as either `/lid-setup` (primary) or `/update-lid` (alias). Both names route to the same skill; the alias exists because "setup" and "update" are distinct mental models even though the underlying behavior dispatches on state. Users who have never heard of LID reach for `/lid-setup`; users who know the project is already configured reach for `/update-lid`.

### State dispatch

On invocation, the skill inspects the project:

| Detected state | Action |
|---|---|
| No `CLAUDE.md`, no `docs/` | Full bootstrap — create directories, create `CLAUDE.md` with LID directives and mode marker. |
| `CLAUDE.md` exists, no LID directives | Append LID directives to existing `CLAUDE.md`; create `docs/` if missing. |
| LID directives present, no mode marker | Add mode marker (default: Full). |
| LID directives present, mode marker present, no mode change requested | Reconcile conventions — check for convention drift (e.g., missing directories, outdated CLAUDE.md template sections) and offer targeted updates. |
| Fully configured, no drift, no mode change | Inform the user what was detected and exit without changes. |
| Mode change requested | Run mode transition (see below). |

### Detection signals

The skill detects state via specific signals rather than heuristics:

- **LID directives present** — `grep` for the literal strings `"linked-intent-dev"` or `"Linked-Intent Development"` in `CLAUDE.md`. Either string matches; both indicate directives already present.
- **Mode marker present** — `grep` for a line matching `## LID Mode:` in `CLAUDE.md`, followed by one of `Full` or `Scoped`. Case-insensitive on the mode name; whitespace around the heading tolerated.
- **Arrow-maintenance overlay present** — `docs/arrows/` directory exists in the project root.
- **Convention drift** — required directories missing (`docs/llds/`, `docs/specs/`, `docs/high-level-design.md`), or CLAUDE.md template sections do not match the current template version.

These signals are the authoritative detection rules. The skill does not guess or use fuzzy matching.

### Arrow-maintenance coordination

When the arrow-maintenance overlay is present (detected by `docs/arrows/` directory), the skill includes additional arrow-navigation rows in the CLAUDE.md directives template — pointing at `docs/arrows/index.yaml` and the per-segment arrow docs as part of the project's navigation table. When arrow-maintenance is absent, these rows are omitted. The skill re-checks this signal on every invocation, so installing arrow-maintenance later triggers the corresponding CLAUDE.md update on the next `/update-lid` run.

### Mode interaction

The skill prompts the user for the intended mode when bootstrapping, with Full LID as the default. For projects where the mode is ambiguous, the skill explains the difference and lets the user choose.

**Caller-provided mode.** When this skill is invoked by another skill (for example, `/map-codebase` at terminal verification) that has already determined the mode — typically from its own upstream scope question — the caller passes the mode through and this skill honors it without re-prompting. Re-prompting at the end of a long caller-driven flow would be a bad user experience; the caller's scope question is the mode decision.

Mode is persisted in `CLAUDE.md` under the `## LID Mode: {Full|Scoped}` heading; this is the sole source of truth for mode detection.

### Mode transitions

- **Full → Scoped (demotion).** Mode marker updates; no file migration required. Cascade rigor relaxes on the next `linked-intent-dev` skill run.
- **Scoped → Full (promotion).** Arrow artifacts migrate from scope-local paths into the standard Full LID positions (`docs/llds/`, `docs/specs/`, `docs/high-level-design.md`). Where multiple scoped arrows have overlapping components, the skill surfaces the overlaps to the user one pair at a time and asks for reconciliation. There is no automatic merge.

### Idempotency and inform-and-skip

The skill is idempotent. Running it twice on a well-configured project produces no changes. This is important because the alias invites repeat invocation, and because users may run it to confirm their project is still correctly configured.

When the skill detects that the project is already fully configured (LID directives present, mode marker valid, all required directories exist, no convention drift), it **informs the user what it detected and exits without making changes**. The user sees a brief summary — detected mode, presence of arrow-maintenance overlay, directory structure status — rather than a silent no-op. Silent no-ops are confusing; an explicit "nothing to do; here is what I saw" avoids the user wondering whether the skill ran at all.

### Verification and show-what-changed

After making any file changes (bootstrap, append directives, mode transition, drift reconciliation), the skill reads back the modified files — primarily `CLAUDE.md` — and produces a short summary of what was added or modified. The user should never have to diff the repo manually to understand what the skill just did. Summaries name the files changed and the sections added/modified, with the actual content elided unless it is a single line.

### Directory structure

The skill creates (or verifies) this layout in the project root:

- `docs/high-level-design.md`
- `docs/llds/`
- `docs/specs/`

Notably, `docs/planning/` is **not** created. Plans are agent-native; LID does not require the directory. When invoked as `/update-lid` against a project that contains a legacy `docs/planning/` from an earlier LID era, the skill flags the directory as obsolete, describes what it contains, and offers to remove it after explicit user confirmation. It never removes without confirmation. The `linked-intent-dev` skill itself ignores the directory — it is not part of the required arrow.

## Mode Detection Mechanics

Mode is detected by a single parse of `CLAUDE.md`. The skill looks for a line matching `## LID Mode: {mode}` where `{mode}` is one of `Full` or `Scoped`. Matching is case-insensitive on the mode name; whitespace around the heading is tolerated.

If the marker is missing, malformed, or names an unrecognized mode value, the skill defaults to Full LID and surfaces a one-line warning during the next `linked-intent-dev` consult asking the user to add a valid marker explicitly. Full and Scoped are close enough in behavior that defaulting to the more rigorous one carries negligible cost. The skill does not silently write a marker — doing so would let a misconfigured project drift for sessions before anyone notices.

**Multiple `CLAUDE.md` files.** In monorepos or nested projects, the agent's harness typically resolves which `CLAUDE.md` is in scope. The skill trusts that resolution. Absent harness guidance, the skill uses the `CLAUDE.md` nearest to the files under review — walking up from the file's directory until a `CLAUDE.md` is found.

## Spec ID Format

EARS spec IDs are globally unique across the project and structured to be grep-friendly. The default shape is `{FEATURE}-{TYPE}-{NNN}` (e.g., `LID-SETUP-003`), but longer forms are permitted for namespacing — `AUTH-LOGIN-UI-001` distinguishes login-UI specs from login-API specs; `BILLING-INVOICE-RENDERING-004` disambiguates nested features. Format rules:

- **Global uniqueness.** Two specs cannot share an ID anywhere in the project, including across different LLDs.
- **Grep-friendliness.** IDs use uppercase letters, digits, and hyphens only — no other characters — so `grep "FEATURE-TYPE-003"` across the repo finds every annotation, test, and spec file that references it.
- **ID stability.** Once assigned, an ID does not move. Text revisions do not change the ID. Deletion is permanent; the number is not recycled into a future spec, because doing so would collide with git-history references to the old ID.
- **Namespacing on conflict.** When the skill is about to draft a new spec whose natural prefix already exists for an unrelated feature, it surfaces the collision and asks the user which namespacing segment to add rather than silently picking.

## Phase-Requirement Policy

The skill enforces this phase set per mode. This table is the reference the `linked-intent-dev` skill uses when prompting for missing phases:

| Phase | Full LID | Scoped LID |
|---|---|---|
| HLD | Required, all standard HLD sections filled | Required, sections may be marked "not yet specified" |
| LLD per intent component | Required for all components | Required for components in scope only |
| EARS spec file per behavioral component | Required | Required (linkage is not optional) |
| Tests before code | Required | Required (TDD is not optional) |
| `@spec` annotations on code and tests | Required | Required (linkage is not optional) |

## Spec-File Header Format (LID-on-LID Linkage Inversion)

In LID-on-LID, EARS spec files carry the downstream artifact pointer, because `SKILL.md` bodies cannot host `@spec` annotations without bending runtime behavior. Spec file header format:

```markdown
# {Feature} Specs

**LLD**: docs/llds/{plugin-name}.md
**Implementing artifacts**:
- plugins/{plugin}/skills/{skill}/SKILL.md
- plugins/{plugin}/skills/{skill}/references/{file}.md

---

## {FEATURE}-{TYPE}-001

WHEN {condition} THEN the system SHALL {behavior}. [x]

...
```

The `LLD` line points upstream to the authoritative design doc. The `Implementing artifacts` list points downstream to the compiled prompt files. An agent walking from a SKILL.md file to its specs does so by consulting this list in the relevant spec file, not by reading the SKILL.md body.

This inversion applies **only** to LID-on-LID. Normal LID projects — where code is the artifact — follow the standard convention: `@spec` annotations live in code and tests, and spec files do not carry downstream artifact pointers.

## `index.yaml` Updates during Changes

When a change is made inside an arrow segment (phases 2–6 above), this skill updates the segment's entry in `docs/arrows/index.yaml` (if the overlay is present) — status transitions, `next`, `drift`, `audited_sha` on completion. The schema is defined authoritatively in `docs/llds/arrow-maintenance.md`; this skill writes to fields already specified there. When the two disagree, the arrow-maintenance LLD is the authority.

Authority between artifacts: `index.yaml` holds the source of truth for per-segment status and timestamps. The per-segment arrow doc's References and Spec Coverage sections are *derived views* — they are regenerated from source scans (grep for `@spec`, file existence checks, eval-citation checks) during audit, not hand-maintained in ways that can diverge from source.

## Eval Metadata Conventions

For behavioral skills, `evals/evals.json` and per-eval `eval_metadata.json` carry spec linkage at the assertion level. Schema extension beyond skill-creator's defaults:

```json
{
  "eval_id": 0,
  "eval_name": "bootstraps-fresh-project",
  "prompt": "Set up LID in this empty directory",
  "assertions": [
    {
      "text": "docs/llds/ directory exists",
      "spec_ids": ["LID-SETUP-002"]
    },
    {
      "text": "CLAUDE.md contains '## LID Mode: Full'",
      "spec_ids": ["LID-SETUP-004", "LID-SETUP-007"]
    }
  ]
}
```

`spec_ids` is per-assertion, not per-eval — different assertions in one eval typically verify different specs. The grader produces `grading.json` with the standard `text`/`passed`/`evidence` fields; `spec_ids` travels with the assertion through grading so the benchmark viewer can display which specs an eval actually exercised.

Coverage audit: every behavioral EARS spec should appear in at least one assertion's `spec_ids` across the eval suite. The `arrow-maintenance` overlay runs this audit when present.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Single behavioral skill vs. separate setup/update skills | Single skill with state dispatch, two command names | Separate `/lid-setup` and `/update-lid` skills; one skill with one name only | Minimum-system: one skill behavior, two entry points for user mental models. State dispatch is trivial; maintaining two skills with overlapping logic is not. |
| Mode detection source | `CLAUDE.md` heading (`## LID Mode: ...`) | Per-doc frontmatter; dedicated config file; directory convention | CLAUDE.md is already the bootstrap entry point and is read on every session. Mode is project-global, not per-doc. |
| Missing/malformed mode fallback | Default to Full, surface warning | Default to Scoped; fail loudly; prompt for mode | Full is the more rigorous mode; defaulting there errs toward more specification. Full and Scoped are close enough that the cost of the wrong default is small. Failing loudly would block harmless sessions; prompting interrupts the user unnecessarily. |
| `docs/planning/` creation | Do not create; flag obsolete if present | Create empty; create with README; create conditionally | Plans are agent-native now. Creating an unused directory is clutter; creating a README is surface growth. Flagging legacy directories respects existing user content. |
| EARS spec linkage direction for LID-on-LID | Spec file header points to artifacts (inverted) | `@spec` annotations in SKILL.md body; frontmatter `specs:` field | Prompt bodies cannot host annotations without instruction contamination. Spec-as-authoritative-end is philosophically cleaner than either alternative. |
| Arrow boundary definition | EARS spec ID prefix (`{FEATURE}-*`) | LLD file identity; directory membership; manual tagging | Prefix comparison is cheap and already present in the ID format. LLD file identity couples boundaries to file organization; manual tagging is surface growth. |
| Bug-fix workflow | Walk the arrow like any other change | Short-circuit to coherence check; dedicated bug-fix path | Bugs are intent gaps — either the spec was wrong or never existed. Treating them as a special case lets the agent "fix" code while the upstream intent stays unexpressed, which is exactly the rot LID is designed to prevent. |
| Spec ID format | Extensible prefix chain with global uniqueness | Fixed two-segment format (`FEATURE-TYPE-NNN`); GUID; hierarchical numeric only | Longer prefixes are necessary for namespacing in large projects. Fixed segments force collisions that have no good resolution. GUIDs break grep-friendliness. |
| Phase override by user | Allowed, with warning | Blocked; allowed silently | The user is always right; the skill's job is to make the cost visible. Blocking would compete with the agent's authority to judge local context. Silent allow forfeits the drift signal. |

## Open Questions & Future Decisions

### Resolved

1. ✅ One plugin, two skills (prose + behavioral). Commands are entry points to the behavioral skill.
2. ✅ Mode lives in `CLAUDE.md`, single source; defaults to Full when missing or malformed.
3. ✅ Plans are not a required artifact; legacy `docs/planning/` is flagged but not auto-removed.
4. ✅ Tests-first is methodological law, not user preference.
5. ✅ Multiple `CLAUDE.md` files resolved by harness first, nearest-to-file-under-review second.
6. ✅ Mid-transition or otherwise inconsistent arrows are surfaced to the user; resolving inconsistency is a userland decision, not an auto-repair.
7. ✅ Cascade touching uncommitted work warns and requires confirmation before proceeding.
8. ✅ Bug fixes walk the arrow like any other change — no short-circuit path.
9. ✅ Deleted spec IDs are not reused; git history preserves the old ID's meaning.
10. ✅ Spec ID format is extensible; the skill asks for a namespacing segment when two arrows would collide on a prefix.
11. ✅ User phase overrides are honored, with a warning that describes the drift risk.
12. ✅ `@spec` annotations go at the entry point of the behavior's implementation graph, not on every helper.

### Deferred to implementation

1. ~~**Scope declaration format**~~ — *Resolved*. Declared in `## LID Scope` section of `CLAUDE.md` with bulleted include/exclude globs; section omitted when mode is Full. See the Scope declaration format section above. Original candidates (dedicated `docs/scope.yaml`, inferred from `docs/llds/`) were rejected because CLAUDE.md is already read unconditionally and the section-in-a-file form matches the `## LID Mode:` precedent.
2. **HLD template file format** — referenced by the `lid-setup` skill for bootstraps in either mode. The standard section list (problem / approach / users / goals-and-non-goals / system design / key decisions / success metrics / FAQ / references) is the intended baseline; exact headings and commentary prose to be drafted during implementation.
3. **Description-optimization cadence** — when is `run_loop.py` run against the `linked-intent-dev` skill's description to keep trigger accuracy calibrated. Candidates: every skill-body change; periodic; on-demand only.
4. **Cross-scope change surfacing UX** — when a change touches multiple arrow boundaries, does the skill list all affected arrows up front, walk one at a time, or produce a structured confirmation? To be refined after running the skill on real changes.

## References

- `docs/high-level-design.md` — the HLD this LLD traces from.
- `docs/llds/arrow-maintenance.md` — sibling plugin LLD; the coherence-audit behavior lives there.
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/ears-syntax.md` — EARS syntax reference.
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md` — LLD structure template.
- `skill-creator` plugin — eval harness used for behavioral-skill evals.
