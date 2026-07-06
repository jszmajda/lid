---
parent: arrow-maintenance
prefix: SCALE-MAINT
---

# LLD: arrow-maintenance maintenance Skill

## Context and Design Philosophy

The `maintenance` skill is the navigation and audit half of the `arrow-maintenance` plugin. It is the skill invoked as `/arrow-maintenance` and the one that runs ambiently when a project carries the `docs/arrows/` overlay. Its job is to keep that overlay legible and honest: orient the agent through it, audit it for drift, repair the unambiguous parts in place, and execute the lifecycle operations that restructure it.

The shared design this skill rides on — the `docs/arrows/` overlay, the `index.yaml` schema, the progressive-disclosure navigation model, the arrow-doc format, the lifecycle-event mechanics, and the coordination/authority rules with `linked-intent-dev` — is specified in the parent sub-HLD at `docs/intent/arrow-maintenance/arrow-maintenance-design.md`. This LLD does not re-specify them; it describes how *this skill* uses them across its two modes. Terms like *arrow*, *segment*, *drift*, *coherence*, and *cascade* are defined in the HLD's Glossary section.

This LLD owns the `SCALE-MAINT` segment and its specs at `docs/intent/arrow-maintenance/maintenance/maintenance-specs.md`. The specs cover the command-mode behavior (which produces verifiable project-state changes); ambient-mode behavior is pure prose guidance verified by dogfooding.

**A note on actors.** "The skill" refers to the prose guidance; the agent is the actor. All surfacing, audit-running, and file-writing happens through the agent acting on skill guidance.

## The Two Modes

The skill operates in two modes that share the same audit semantics but differ in what they are permitted to write.

### Intent (ambient mode)

When a project uses the `docs/arrows/` overlay, shape the agent's work on arrow-adjacent tasks so that:

- navigation starts from `index.yaml` rather than from file listings (per the parent sub-HLD's progressive-disclosure navigation model);
- cascade and audit findings update `index.yaml` and per-segment arrow docs in place;
- drift is surfaced explicitly, not silently corrected;
- arrow lifecycle events (split, merge, rename, re-parent, status transitions) are recorded, not erased.

In ambient mode the skill is pure prose guidance — it biases how the agent uses the overlay without executing a procedure. File modifications are not forbidden in ambient mode; they happen opportunistically when the surrounding conversation authorizes them (for example, when the user has asked for a change and `linked-intent-dev` is already editing a segment, the ambient guidance tells the agent to update the arrow doc in the same cascade). What ambient mode does *not* do is initiate a systematic audit-and-update pass on its own — that is command-mode behavior. Projects without `docs/arrows/` see no ambient behavior.

### Intent (command mode)

When invoked explicitly as `/arrow-maintenance`, the skill runs an audit-and-update pass. The implied user intent is "audit my arrows and update what you find." The skill then:

- fixes any broken state in `docs/arrows/` (malformed `index.yaml`, missing per-segment docs referenced by the index, stale schema versions) — these are the skill's domain, so they are always repaired when the command runs;
- runs the audit checks described below;
- updates each affected arrow doc's `## Spec Coverage` table and `index.yaml` `status` / `next` / `drift` / `audited` / `audited_sha` fields in place;
- cleans up `unmapped.docs` by assigning entries to segments where it can, and flagging the rest for user assignment;
- produces a structured report of findings that could not be resolved automatically.

Command-mode behavior produces verifiable project-state changes and is therefore behavioral — EARS specs cover its assertions and the eval suite gates changes to its prompt.

### State dispatch (command mode)

`/arrow-maintenance` dispatches on the project's LID state:

- **Overlay present.** Run the audit-and-update pass described above.
- **LID docs but no `docs/arrows/`.** Create the overlay from existing LLDs and specs — one arrow doc per leaf LLD (the EARS-owning nodes), the design tree's nesting recorded in `index.yaml` via `parent`/`children` links, no upstream skeleton generation (LLDs already exist).
- **No LID docs at all.** Describe what was found and offer to dispatch inline to `/linked-intent-dev` (greenfield — invoke with a description of what to build; the workflow bootstraps LID as part of Phase 1) or `/map-codebase` (brownfield) rather than asking the user to re-invoke. The user's answer proceeds directly into the chosen command without requiring a second manual invocation. The skill does not silently run the audit-and-update pass on such a project.

### Triggering (ambient mode)

Ambient triggering is on prompts that touch arrow-adjacent work — navigating the codebase, auditing specs, investigating drift — in projects where `docs/arrows/` exists. Presence of the directory is the sole detection signal. If the directory is absent, the ambient skill does not trigger; the core `linked-intent-dev` skill alone is sufficient for projects that do not need the overlay.

## Navigation and Session Startup

The skill drives the index-first, detail-on-demand loading order specified in the parent sub-HLD. At the start of any session where the agent will touch arrow-adjacent work in a project that has `docs/arrows/`, it guides the agent through a consistent startup sequence:

1. Load `docs/arrows/index.yaml`.
2. Query for segments whose `blockedBy` list is empty and whose `status` is not `OK` or `OBSOLETE` — these are candidates for active work.
3. When the user names a segment or the conversation implies one, load only that segment's arrow doc (`docs/arrows/{segment-path}.md`).
4. Follow the arrow doc's `## References` section to the LLD, spec file, tests, or code as needed for the current task.
5. If no specific segment is implied and the user is orienting broadly, summarize the `next` and `drift` fields from the index for in-flight segments rather than loading every arrow doc. Where the tree nests, walk `parent`→`children` to summarize a subtree under a grouping node rather than the whole project.

This sequence exists because loading the full project is often infeasible at this scale; the index-first pattern is the ambient-mode user experience that makes the overlay worthwhile.

## Audit

Audit runs in both modes — ambiently when the skill notices drift during other work, and explicitly when invoked as `/arrow-maintenance`. The semantics are identical across modes; only the write authority differs.

### Audit checklist

The core audit checks:

1. **Reference coherence** — do the pointers in the arrow doc still point to real files? Are the EARS specs cited still present? Are the LLD section headings named as referenced?
2. **Coverage** — for each behavioral spec, does an eval assertion cite its ID?
3. **Staleness** — how long since the segment was last audited? Measured by two fields in `index.yaml`: `audited` (calendar date) and `audited_sha` (git commit SHA at time of audit). The SHA enables incremental audit — on subsequent runs the skill checks only segments whose files changed since `audited_sha`, rather than re-auditing the whole project.
4. **Drift signals** — code files modified since `audited_sha`; specs changed without corresponding test updates; tests passing but missing `@spec` annotations; `@spec` annotations pointing to IDs not present in any spec file (*reverse orphans* — the spec ID is referenced but doesn't exist). For reverse orphans the skill asks the user how to resolve: create the missing spec, delete the annotation, or treat as an alias of an existing spec.
5. **Orphan artifacts** — LLDs, specs, or code files not listed in any arrow doc's References section.
6. **Misplaced EARS** — every `-design.md` in the intent tree (sub-HLDs and the root HLD included) is scanned for EARS-labeled intent the design doc itself *defines* rather than references. The full-form violation is mechanically detectable: a requirement line with status marker, bold spec ID, and requirement text. The subtler form drops the marker: a spec-ID-labeled statement that introduces or extends normative content in place — behavior the system shall exhibit — instead of pointing at a line in a specs file. The test is **definition versus reference**: a reference adds no normative content beyond what the cited specs-file line carries; a definition does. Findings carry the suggested resolution — extract the content to the owning `{node}-specs.md` (creating or narrowing the spec line there) and leave a reference behind — and are never auto-repaired. Bare spec-ID mentions, within or across segments, are navigation, not ownership, and are not flagged.

The overlay is uniquely positioned to catch six classes of drift: reference rot (arrow-doc pointers to files/sections that no longer exist), spec-to-code drift (specs whose cited `@spec` annotations have disappeared), uncovered behavioral specs (no eval assertion citing them), stale segments (`audited`/`audited_sha` lagging current work), orphan artifacts (files not listed in any arrow doc), and misplaced EARS (requirement content defined in design docs). The reserved underscore subtrees are excluded from all of these — `_experiments/` (owned by `lid-experimental`) and `_map-codebase/` (the brownfield bootstrap's transient sweep files); see the parent sub-HLD.

### What the skill writes per mode

Surfacing is structured: the skill produces a report naming each finding and its location.

- **Ambient mode.** The skill surfaces findings but does not *initiate* file writes. It may *participate* in writes the surrounding conversation is already doing — for instance, updating an arrow doc's coverage table alongside a `linked-intent-dev` edit on the same segment. Systematic corrective writes — touching files the user hasn't asked about — are reserved for command mode.
- **Command mode.** The skill updates arrow docs and `index.yaml` in place for findings that have unambiguous resolutions (coverage-table regeneration, status transitions, `audited` / `audited_sha` refresh, `unmapped.docs` cleanup), and surfaces the rest for user decision.

The skill does not prescribe an audit cadence. "Run audit every N commits" or "run weekly" is surface growth — users decide when the staleness signal is worth acting on. The skill emits the signal when consulted; the user chooses the rhythm.

### Reference tooling

The audit checks above are expensive when performed by the agent via `Read`/`Grep` — enumerating every `@spec` annotation, comparing to every spec file, walking every `index.yaml` entry, checking every referenced file path. For projects large enough to need the overlay, the cost becomes real.

The skill therefore delegates deterministic checks to a project-local coherence script when one is **declared** in the project's `CLAUDE.md` under a `## LID Tooling` section. Declaration format:

```markdown
## LID Tooling

- **Coherence check**: `bin/coherence-check.mjs`
```

Language and path are the user's choice; the declaration is authoritative. The plugin ships a reference implementation in Node at `plugins/arrow-maintenance/skills/arrow-maintenance/references/coherence-check.mjs`; users may copy it, adapt it, or write their own in Python, bash, or any other language.

When the declaration is missing or the declared path does not resolve, the skill falls back to in-prompt audit. A coherence script is not required and not installed by default. It is an opt-in performance accelerator. The audit's *semantics* (what checks are run, what findings mean) live in the skill; the script is one implementation of those checks.

## Lifecycle Execution

The five lifecycle events (split, merge, rename, re-parent, status transition) and their atomicity guarantees are specified in the parent sub-HLD's *Lifecycle Events* section. This skill is the owner that executes them on an existing overlay — it has the richest guidance for multi-segment events and owns the atomic rename/re-parent operation that rewrites path-concatenated EARS IDs and their `@spec` annotations across spec files, docs, `index.yaml`, and code in one session.

`linked-intent-dev` recognizes a lifecycle event mid-change (for example, an HLD change that dissolves a segment boundary) and hands off to this skill rather than re-specifying the mechanics. When a split is detected while `linked-intent-dev` is mid-change on the affected segment, the skill asks whether to split now or defer; deferring is preferred — split at a clean break, not mid-edit.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Dual-mode (ambient prose + behavioral command) | One skill, two modes | Separate ambient skill and audit command; ambient-only | Ambient guidance and a directed audit pass are the same audit semantics applied with different write authority. One skill keeps the surface minimal; users with a naive mental model reach for a command when they want to update arrow state, and command mode respects that. Keeping command mode behavioral (verifiable outputs) makes it eval-gateable. |
| `/arrow-maintenance` state dispatch | Audit when overlay present; bootstrap-from-docs when LID docs but no overlay; redirect when no LID | Always require `/map-codebase` for any direct invocation; error when no overlay | Users reach for the command in different project states. Dispatching on state lets one command serve all three without a second manual invocation. Bootstrap-from-docs needs no brownfield sweep because the LLDs already exist. |
| Repair broken overlay state on every command run | Always repaired | Report-only; ask before repairing | Malformed `index.yaml`, missing referenced docs, and stale schema versions are the skill's own domain — there is no user-intent ambiguity in fixing them, unlike spec/code drift. Always repairing them keeps the overlay self-consistent without prompting. |
| Reverse orphans | Surfaced for user resolution | Auto-create the missing spec; auto-delete the annotation | A `@spec` pointing at a missing ID could mean any of three things (spec to be written, dead annotation, alias); the skill cannot know which. Auto-resolving would guess wrong some of the time and erase signal. |
| Misplaced EARS | Surfaced for user resolution | Auto-extract the content to the specs file | Definition versus reference is a judgment; the right fix could be extraction, deletion, or rewording the design prose, and auto-moving content would relocate errors along with the intent. |
| Audited state tracking | `audited` (date) + `audited_sha` (git SHA) | Date only; SHA only | Date is human-readable for staleness judgment; SHA enables incremental audit on subsequent runs, a large performance win on big projects. (Schema home is the parent sub-HLD.) |
| Audit cadence | No prescribed cadence; staleness signal surfaced when consulted | Every N commits; scheduled; CI-enforced | Prescribing cadence is surface growth. Projects have different rhythms; LID emits the signal and lets the user choose when to act. |
| Coherence-check script | Ship optional reference implementation; delegate when declared, fall back to in-prompt | Require script; never ship one; bake checks into skill always | Real-world use (Threadkeeper) shows agents reach for such scripts constantly because in-prompt checks are expensive. Shipping an optional reference acknowledges the pattern without imposing a runtime dependency. Language-neutral — any equivalent script works. |

## Open Questions

### Resolved

1. ✅ Dual-mode: ambient (pure-prose) navigation/audit guidance and a behavioral `/arrow-maintenance` audit-and-update command. No separate audit command.
2. ✅ `/arrow-maintenance` always repairs broken `docs/arrows/` state when it runs.
3. ✅ `/arrow-maintenance` state-dispatches: audit when the overlay is present, bootstrap-from-docs when LID docs exist but no overlay, redirect to `/map-codebase` (brownfield) or `/linked-intent-dev` (greenfield) when no LID docs exist.
4. ✅ Reverse orphans are surfaced for user resolution, not auto-repaired.
5. ✅ `audited_sha` tracks git head at last audit; enables incremental audit on subsequent runs.
6. ✅ No prescribed audit cadence; the skill emits staleness signals when consulted.
7. ✅ Split detected mid-change asks the user and prefers deferral.
8. ✅ Coherence-check script shipped as an optional reference implementation; the skill delegates when one is declared under `## LID Tooling`.

### Deferred to implementation

1. **Orphan artifact handling at scale.** Bulk reporting is the direction, but sizing (how many orphans before the report needs pagination or grouping) matters. To be refined on a real mid-sized project. (Shared with the parent sub-HLD.)
2. **Status enum extension surfacing.** How the skill surfaces a project-local status-enum customization is TBD. (Schema-level question lives in the parent sub-HLD.)

## References

- `docs/intent/arrow-maintenance/arrow-maintenance-design.md` — parent sub-HLD; authoritative for the `docs/arrows/` overlay, `index.yaml` schema, navigation model, arrow-doc format, lifecycle-event mechanics, the coordination/authority split with `linked-intent-dev`, and the reserved `_experiments/` namespace.
- `docs/intent/arrow-maintenance/maintenance/maintenance-specs.md` — the `SCALE-MAINT` command-mode specs this LLD owns.
- `docs/intent/arrow-maintenance/map-codebase/map-codebase-design.md` — sibling leaf; the brownfield-bootstrap skill that produces the overlay this skill maintains.
- `docs/intent/linked-intent-dev/linked-intent-dev-design.md` — core plugin LLD; authoritative for the spec-file header format and `@spec` placement rule this skill's reference-coherence audit relies on.
- `plugins/arrow-maintenance/skills/arrow-maintenance/` — the compiled skill (`SKILL.md` + `references/`).
- `/Users/jess/src/personal-log/docs/arrows/` — the working reference implementation this design is modeled on.
