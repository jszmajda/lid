# Project Structure Specs

**LLD**: docs/llds/project-structure.md
**Implementing artifacts**:
- CONTRIBUTING.md
- AGENTS.md (with CLAUDE.md symlink)
- docs/setup.md
- .claude-plugin/marketplace.json
- LICENSE

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

---

## CONTRIBUTING.md: Audience and Framing

- `[x]` **PROJ-STRUCT-001**: A `CONTRIBUTING.md` file SHALL exist at the repository root.
- `[x]` **PROJ-STRUCT-002**: The first section of `CONTRIBUTING.md` SHALL be a short human preamble that names a human reader as the audience and instructs them to point their coding agent at the file before starting work, after which the document is agent-facing.
- `[x]` **PROJ-STRUCT-003**: `CONTRIBUTING.md` SHALL state that contributions follow LID and that this repository is the canonical LID-on-LID reference, with a pointer to `docs/high-level-design.md` for the methodology and `AGENTS.md` for the operating workflow.

## CONTRIBUTING.md: Trivial-Change Carve-Out

- `[x]` **PROJ-STRUCT-004**: `CONTRIBUTING.md` SHALL name an explicit trivial-change carve-out covering at minimum: typo and grammar fixes in existing prose, broken-link repairs, formatting and whitespace, and updates to stale external references.
- `[x]` **PROJ-STRUCT-005**: `CONTRIBUTING.md` SHALL state that any change which alters the meaning of intent — including a one-line edit to an EARS spec, a skill description, or an HLD principle — falls outside the trivial carve-out and walks the arrow.

## CONTRIBUTING.md: Out of Scope

- `[x]` **PROJ-STRUCT-006**: `CONTRIBUTING.md` SHALL state the out-of-scope principle: that LID's territory is the structure of intent the agent compiles from, and that proposals which sound like "LID should help me *do* X" rather than "LID should help my intent stay coherent as the system grows" are out of scope.
- `[x]` **PROJ-STRUCT-007**: `CONTRIBUTING.md` SHALL list at least the following declined categories with a one-line rationale for each: multi-agent orchestration or agent teams; personas; development styles or team ceremonies; task management or work tracking.
- `[x]` **PROJ-STRUCT-008**: `CONTRIBUTING.md` SHALL frame the declined-category list as descriptive rather than exhaustive, so future proposals are judged against the principle rather than against the literal list.

## CONTRIBUTING.md: Arrow Variants

- `[x]` **PROJ-STRUCT-009**: `CONTRIBUTING.md` SHALL present a decision tree mapping change types to the variant arrow shapes named in HLD § Key Design Decisions / *The arrow for LID itself*. The tree SHALL cover: changes to existing core plugins (with sub-cases for behavioral, pure-prose, and dual-mode skills); novel capabilities not in core; HLD or methodology changes; site/examples/positioning content changes; and new tool adapters.
- `[x]` **PROJ-STRUCT-010**: For each change type covered by PROJ-STRUCT-009, `CONTRIBUTING.md` SHALL name the arrow shape (e.g., `HLD → LLD → EARS → evals + SKILL.md + references/`) and the verification mode (eval suite, dogfooding, build-time checks).
- `[x]` **PROJ-STRUCT-011**: `CONTRIBUTING.md` SHALL state the verification principle: tests when the artifact has a runtime to assert against; dogfooding or explicit justification when it does not. The statement SHALL specify that "I could not write a test" is acceptable for pure-prose skills but not for behavioral skills or content artifacts.

## CONTRIBUTING.md: Minimum-Surface Gate

- `[x]` **PROJ-STRUCT-012**: `CONTRIBUTING.md` SHALL include the minimum-surface gate quoted from HLD § Key Design Decisions / *Minimum-system discipline — the why*: *"Can the existing surface absorb this, or is the agent about to absorb it anyway?"*
- `[x]` **PROJ-STRUCT-013**: `CONTRIBUTING.md` SHALL route novel capabilities that clear the gate at `plugins/lid-experimental/` rather than directly into core plugins, and SHALL state that promotion into core is earned through community adoption and concrete value rather than requested.
- `[x]` **PROJ-STRUCT-014**: `CONTRIBUTING.md` SHALL require PR descriptions that introduce new surface to answer both gate questions explicitly.

## CONTRIBUTING.md: Mechanics

- `[x]` **PROJ-STRUCT-015**: `CONTRIBUTING.md` SHALL state the atomic-improvement framing: one PR equals one coherent intent change, walked end-to-end through whichever arrow phases it touches; coherence rather than size is the unit.
- `[x]` **PROJ-STRUCT-016**: `CONTRIBUTING.md` SHALL provide examples that bound the size dimension on both ends — a tiny-but-coherent example (e.g., a sharpened EARS line plus its eval) and a larger-but-coherent example (e.g., an LLD section rewrite cascaded through specs and skill prose).
- `[x]` **PROJ-STRUCT-017**: `CONTRIBUTING.md` SHALL state that contributors SHOULD file an issue before walking the arrow on changes that may add new surface, and that changes fitting clearly within existing surface go straight to a PR.
- `[x]` **PROJ-STRUCT-018**: `CONTRIBUTING.md` SHALL list the items a PR description should include: arrow segments touched (LLD names, EARS IDs); arrow variant applied; minimum-surface gate answers (when introducing new surface); dogfooding scenarios exercised (for pure-prose changes); and pause points with verification (for cross-segment cascade).

## AGENTS.md and CLAUDE.md

- `[x]` **PROJ-STRUCT-019**: An `AGENTS.md` file SHALL exist at the repository root and SHALL be the canonical source of per-repo agent instructions.
- `[x]` **PROJ-STRUCT-020**: A `CLAUDE.md` file SHALL exist at the repository root as a symlink resolving to `AGENTS.md`, so Claude Code (which reads `CLAUDE.md`) and tools that honor `AGENTS.md` natively read identical content with zero drift surface.
- `[x]` **PROJ-STRUCT-021**: `AGENTS.md` SHALL describe the LID workflow (`HLD → LLDs → EARS → Tests → Code`) and SHALL point at `docs/high-level-design.md` as the canonical methodology document.
- `[x]` **PROJ-STRUCT-022**: `AGENTS.md` SHALL include the project-level LID Mode declaration heading (e.g., `## LID Mode: Full`) so the workflow skill can detect the project's mode on entry.
- `[x]` **PROJ-STRUCT-023**: `AGENTS.md` SHALL provide a navigation table or equivalent index pointing at the canonical paths for the HLD, the LLDs directory, the EARS specs directory, the arrows index, and `docs/setup.md`.

## docs/setup.md

- `[x]` **PROJ-STRUCT-024**: A `docs/setup.md` file SHALL exist describing how non-Claude-Code agents adopt LID through their tool's per-project rule mechanism.
- `[x]` **PROJ-STRUCT-025**: `docs/setup.md` SHALL include a table or equivalent listing of tools that honor a repo-root `AGENTS.md` natively without requiring an adapter.
- `[x]` **PROJ-STRUCT-026**: `docs/setup.md` SHALL provide explicit per-tool adapter snippets for tools that need or benefit from a separate rule file (Cursor, GitHub Copilot inline, and any other tool with a non-`AGENTS.md`-native path).
- `[x]` **PROJ-STRUCT-027**: This repository SHALL NOT ship per-tool adapter files of its own. Adapter files are documented in `docs/setup.md` for users to drop into their own LID projects.

## .claude-plugin/marketplace.json

- `[x]` **PROJ-STRUCT-028**: A `.claude-plugin/marketplace.json` file SHALL exist at the repository root and SHALL declare the repository as a Claude Code plugin source.
- `[x]` **PROJ-STRUCT-029**: `marketplace.json` SHALL list the three first-party plugins shipped from this repository: `linked-intent-dev`, `arrow-maintenance`, and `lid-experimental`. The `source` field for each plugin SHALL match an existing directory under `plugins/`.
- `[x]` **PROJ-STRUCT-030**: Each plugin entry in `marketplace.json` SHALL include `name`, `description`, `source`, `version`, `category`, and `license` fields.

## README pointer

- `[x]` **PROJ-STRUCT-031**: A `README.md` file SHALL exist at the repository root. Its content is owned by `docs/llds/marketing-site.md`; this segment references its existence but does not claim its content.
- `[x]` **PROJ-STRUCT-032**: `CONTRIBUTING.md` SHALL link to `docs/high-level-design.md` and `AGENTS.md` for depth rather than restating their material, so the contributor surface does not duplicate the README or the methodology doc.

## LICENSE

- `[x]` **PROJ-STRUCT-033**: A `LICENSE` file SHALL exist at the repository root containing the MIT license under which the repository is distributed.

## Cascade

- `[x]` **PROJ-STRUCT-034**: When HLD Goal 2 (minimum-system) is modified, the maintainer SHALL review `CONTRIBUTING.md`'s *Out of scope* and *Minimum-surface gate* sections for claim drift before the HLD change is considered complete.
- `[x]` **PROJ-STRUCT-035**: When HLD Goal 4 (dogfooding) is modified, the maintainer SHALL review `CONTRIBUTING.md`'s *Tests, or justify* framing and *Arrow variant by change type* section.
- `[x]` **PROJ-STRUCT-036**: When HLD § Key Design Decisions / *The arrow for LID itself* is modified — for example, a new variant is added or an existing one is revised — the maintainer SHALL update `CONTRIBUTING.md`'s arrow-variant decision tree to absorb the change.
- `[x]` **PROJ-STRUCT-037**: When a new plugin is added under `plugins/`, removed, or renamed, the maintainer SHALL update `.claude-plugin/marketplace.json` and any install commands in `README.md` and `docs/setup.md` to match.
- `[x]` **PROJ-STRUCT-038**: When a new agentic coding tool is added to the supported set, the maintainer SHALL update `docs/setup.md` with either a row in the simple-path table (if the tool honors `AGENTS.md` natively) or a per-tool section with an adapter snippet.

## Build-Time Checks

- `[ ]` **PROJ-STRUCT-039**: A repository CI workflow SHALL fail when an internal markdown link in `CONTRIBUTING.md` or `docs/setup.md` resolves to a missing file or anchor.
- `[ ]` **PROJ-STRUCT-040**: A repository CI workflow SHALL fail when `.claude-plugin/marketplace.json` is not valid JSON or when its plugin `source` paths do not resolve to existing directories under `plugins/`.
- `[ ]` **PROJ-STRUCT-041**: A repository CI workflow SHALL verify that `CLAUDE.md` resolves to `AGENTS.md` (symlink integrity) on every push.

## Arrow Registration

- `[x]` **PROJ-STRUCT-042**: Where the `docs/arrows/` overlay is present in this repository, this segment SHALL appear as a named segment in `docs/arrows/index.yaml` with the same schema as plugin segments.
