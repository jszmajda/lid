---
parent: high-level-design
prefix: LID
---

# Sub-HLD: linked-intent-dev Plugin

## Context and Design Philosophy

The `linked-intent-dev` plugin is the mandatory core of LID. It translates the methodology described in the High-Level Design (HLD) into three skills: a pure-prose workflow skill (`linked-intent-dev`) that shapes how the agent approaches code changes, a behavioral skill (`update-lid`) that bootstraps and maintains project state, and a behavioral skill (`lid-coach`) that reviews a project's LID usage against LID's principles and produces improvement recommendations.

This is the `LID` sub-HLD: it owns no EARS itself and parents three leaf LLDs, one per skill —

| Leaf | Segment | Skill |
|---|---|---|
| [`core/core-design.md`](core/core-design.md) | `LID-CORE` | the pure-prose workflow skill |
| [`update-lid/update-lid-design.md`](update-lid/update-lid-design.md) | `LID-UPDATE` | the behavioral bootstrap/maintenance skill |
| [`lid-coach/lid-coach-design.md`](lid-coach/lid-coach-design.md) | `LID-COACH` | the behavioral principle-review skill |

The three skills share a body of plugin-level design — mode detection, spec-ID format, the LID-on-LID linkage inversion, `index.yaml` update mechanics, and the eval-metadata schema. Those concerns live in this sub-HLD and are referenced from the leaves rather than restated in each. Skill-specific design lives in the corresponding leaf.

**A note on actors.** Throughout this plugin's docs, "the skill" refers to the prose guidance contained in a `SKILL.md`. The skill does not act on its own — it is content the agent consults. When a doc says "the skill surfaces X" or "the skill warns," the mechanism is: the agent, after consulting the skill, performs the surfacing or warning in the assistant turn it produces. The skill is the instruction; the agent is the actor.

Two design constraints shape the plugin:

- **Minimum surface.** The plugin exposes one pure-prose skill (`linked-intent-dev`) and two behavioral skills (`update-lid`, `lid-coach`). Any capability that can live inside those three is absorbed into them rather than given its own entry point. Each skill's separation rationale is documented in its leaf LLD.
- **Describe, do not dictate.** The leaf LLDs describe the *behavior* each skill should produce. They do not prescribe the exact wording of skill prompts. The prompt is the implementation; its phrasing is free to change as long as the described behavior is preserved and the EARS specs pass.

This sub-HLD describes intent; the `SKILL.md` files and references under `plugins/linked-intent-dev/` are the compiled outcome. Terms like *arrow*, *segment*, *drift*, *coherence*, and *cascade* are defined in the HLD's Glossary section.

## Plugin Structure

The plugin lives at `plugins/linked-intent-dev/` with this shape:

- `.claude-plugin/plugin.json` — Claude Code plugin manifest (name, version, skills listing). Its `version` is the canonical LID conventions version (see the HLD's Versioning note).
- `skills/linked-intent-dev/` — the pure-prose workflow skill. Specified in `docs/intent/linked-intent-dev/core/core-design.md`.
  - `SKILL.md`
  - `references/` — supporting reference docs (EARS syntax, LLD template, HLD template).
- `skills/update-lid/` — the behavioral bootstrap/update skill. Specified in `docs/intent/linked-intent-dev/update-lid/update-lid-design.md`.
  - `SKILL.md`
  - `references/` — CLAUDE.md template fragments keyed by mode.
- `skills/lid-coach/` — the behavioral principle-review skill. Specified in `docs/intent/linked-intent-dev/lid-coach/lid-coach-design.md`.
  - `SKILL.md`

No `commands/` directory. Per Claude Code's skills model, an identically-named skill is already directly invokable as `/skill-name`, so a separate command stub would be redundant surface (and would be shadowed by the skill anyway). Users invoke `/linked-intent-dev`, `/update-lid`, and `/lid-coach` directly against their skills.

The plugin intentionally does not bundle scripts. Everything the skills do is expressed in prompts and references; there is no code layer between the skill and the agent's tool use.

## Mode Detection Mechanics

Mode is detected by a single parse of `CLAUDE.md`. The skill reads the `## LID` block and takes the value of its `- Mode:` bullet, which is one of `Full` or `Scoped`. Matching is case-insensitive on the mode name; whitespace around the bullet is tolerated.

If the `## LID` block or its `- Mode:` bullet is missing, malformed, or names an unrecognized mode value, the skill defaults to Full LID and surfaces a one-line warning during the next `linked-intent-dev` consult asking the user to add a valid `- Mode:` bullet explicitly. Full and Scoped are close enough in behavior that defaulting to the more rigorous one carries negligible cost. The skill does not silently write a marker — doing so would let a misconfigured project drift for sessions before anyone notices.

**Multiple `CLAUDE.md` files.** In monorepos or nested projects, the agent's harness typically resolves which `CLAUDE.md` is in scope. The skill trusts that resolution. Absent harness guidance, the skill uses the `CLAUDE.md` nearest to the files under review — walking up from the file's directory until a `CLAUDE.md` is found.

## Spec ID Format

An EARS spec ID is the path from the root of the design tree to the leaf segment that owns the spec, concatenated segment-by-segment and ending in a number. A flat project is `FEATURE-NNN` (e.g., `LID-UPDATE-003`). Each level of nesting prepends one more segment of the path: `PEVAL-RUN-014` is spec 14 of the `run` leaf under the `peval` root; `PEVAL-PERF-LOAD-003` adds another level for a `load` leaf under a `perf` sub-HLD. A leaf MAY append one within-leaf type/area facet before the number (`AUTH-UI-001`, `ENGINE-LEDGER-001`); the facet groups specs inside a leaf and is not a tree boundary. (`LID-CORE-001` is path-concatenation — the `core` leaf under the `LID` sub-HLD — not a facet.) The prefix *is* the spec's position in the tree, so `grep PEVAL-PERF` gathers that whole subtree by construction. Format rules:

- **Position-encoding prefix.** The ID's prefix is the root-to-leaf path; a prefix grep gathers every spec in the named subtree, and one `prefix:`/`index.yaml` lookup resolves an ID to its owning design doc.
- **Global uniqueness.** Two specs cannot share an ID anywhere in the project. Path-concatenation gives this for free — two leaves at different positions necessarily have different prefixes.
- **Grep-friendliness.** IDs use uppercase letters, digits, and hyphens only — no other characters — so `grep "PEVAL-RUN-014"` across the repo finds every annotation, test, and spec file that references it.
- **ID stability.** Once assigned, an ID does not move under ordinary growth — adding or refining specs within a segment never renames existing IDs. The prefix changes only under a deliberate, tooled re-parent or rename of a segment, which rewrites the affected IDs and their annotations together. Deletion is permanent; the number is not recycled into a future spec, because doing so would collide with git-history references to the old ID.
- **Disambiguation on conflict.** When the skill is about to draft a new spec whose natural path prefix already exists for an unrelated segment, it surfaces the collision and asks the user how to disambiguate the position rather than silently picking.

## Spec-File Header Format (LID-on-LID Linkage Inversion)

In LID-on-LID, EARS spec files carry the downstream artifact pointer, because `SKILL.md` bodies cannot host `@spec` annotations without bending runtime behavior. Spec file header format:

```markdown
# {Feature} Specs

**LLD**: docs/intent/{path-to-leaf}.md
**Implementing artifacts**:
- plugins/{plugin}/skills/{skill}/SKILL.md
- plugins/{plugin}/skills/{skill}/references/{file}.md

---

## {ROOT-TO-LEAF-PATH}-001

WHEN {condition} THEN the system SHALL {behavior}. [x]

...
```

The `LLD` line points upstream to the authoritative design doc. The `Implementing artifacts` list points downstream to the compiled prompt files. An agent walking from a SKILL.md file to its specs does so by consulting this list in the relevant spec file, not by reading the SKILL.md body.

This inversion applies **only** to LID-on-LID. Normal LID projects — where code is the artifact — follow the standard convention: `@spec` annotations live in code and tests, and spec files do not carry downstream artifact pointers.

## Eval Metadata Conventions

For behavioral skills, `evals/evals.json` and per-eval `eval_metadata.json` carry spec linkage at the assertion level. Schema extension beyond skill-creator's defaults:

```json
{
  "eval_id": 0,
  "eval_name": "bootstraps-fresh-project",
  "prompt": "Set up LID in this empty directory",
  "assertions": [
    {
      "text": "docs/intent/ directory exists",
      "spec_ids": ["LID-UPDATE-002"]
    },
    {
      "text": "CLAUDE.md contains a '## LID' block with '- Mode: Full'",
      "spec_ids": ["LID-UPDATE-004", "LID-UPDATE-007"]
    }
  ]
}
```

`spec_ids` is per-assertion, not per-eval — different assertions in one eval typically verify different specs. The grader produces `grading.json` with the standard `text`/`passed`/`evidence` fields; `spec_ids` travels with the assertion through grading so the benchmark viewer can display which specs an eval actually exercised.

Coverage audit: every behavioral EARS spec should appear in at least one assertion's `spec_ids` across the eval suite. The `arrow-maintenance` overlay runs this audit when present. The pure-prose `linked-intent-dev` workflow skill (`LID-CORE`) has no eval suite — its behaviors are guidance the agent consults, not a deterministic harness run — so the coverage audit applies only to the behavioral leaves (`LID-UPDATE`, `LID-COACH`).

## Decisions & Alternatives

These are the decisions shared across the plugin's three skills. Skill-specific decisions live in each leaf LLD's own Decisions & Alternatives section.

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Spec ID format | Path-concatenated prefix — the root-to-leaf path of the owning segment, one segment per tree level, with an optional within-leaf type facet | Fixed two-segment format (`FEATURE-TYPE-NNN`); loose namespaces decoupled from position; GUID; hierarchical numeric only | The prefix encodes position, so a single grep gathers a subtree and an agent can place any ID from the ID alone. Fixed segments cannot express depth. Position-decoupled prefixes need a second structure (frontmatter) to locate a spec. GUIDs break grep-friendliness. (See `docs/decisions/namespace-structure.md`.) |
| EARS spec linkage direction for LID-on-LID | Spec file header points to artifacts (inverted) | `@spec` annotations in SKILL.md body; frontmatter `specs:` field | Prompt bodies cannot host annotations without instruction contamination. Spec-as-authoritative-end is philosophically cleaner than either alternative. |

## Open Questions & Future Decisions

Skill-specific open questions live in each leaf LLD. Plugin-wide:

1. ✅ One plugin, three skills (one prose + two behavioral); commands are entry points to the behavioral skills, the workflow skill is invoked directly.
2. ✅ Deleted spec IDs are not reused; git history preserves the old ID's meaning.
3. ✅ Spec IDs are path-concatenated — the root-to-leaf path of the owning segment; the skill asks how to disambiguate when two segments would collide on a path prefix.

## References

- `docs/high-level-design.md` — the HLD this sub-HLD traces from.
- `docs/intent/linked-intent-dev/core/core-design.md` — leaf LLD for the `linked-intent-dev` workflow skill (`LID-CORE`).
- `docs/intent/linked-intent-dev/update-lid/update-lid-design.md` — leaf LLD for the `update-lid` skill (`LID-UPDATE`).
- `docs/intent/linked-intent-dev/lid-coach/lid-coach-design.md` — leaf LLD for the `lid-coach` skill (`LID-COACH`).
- `docs/intent/arrow-maintenance/arrow-maintenance-design.md` — sibling plugin sub-HLD; the coherence-audit behavior lives there.
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/ears-syntax.md` — EARS syntax reference.
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md` — LLD structure template.
- `skill-creator` plugin — eval harness used for behavioral-skill evals.
