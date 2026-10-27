# Project Structure Specs

**LLD**: docs/intent/project-structure/project-structure-design.md
**Implementing artifacts**:
- CONTRIBUTING.md
- AGENTS.md (with CLAUDE.md symlink)
- docs/setup.md
- .claude-plugin/marketplace.json
- .cursor-plugin/marketplace.json
- CHANGELOG.md (canonical at plugins/linked-intent-dev/CHANGELOG.md, root symlink)
- .gitignore
- .claude/settings.json
- LICENSE
- CODE_OF_CONDUCT.md
- SECURITY.md
- CITATION.cff
- .github/ISSUE_TEMPLATE/ (issue forms + config.yml)
- .github/PULL_REQUEST_TEMPLATE.md

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

## CONTRIBUTING.md: Mechanics

- `[x]` **PROJ-STRUCT-015**: `CONTRIBUTING.md` SHALL state the atomic-improvement framing: one PR equals one coherent intent change, walked end-to-end through whichever arrow phases it touches; coherence rather than size is the unit.
- `[x]` **PROJ-STRUCT-016**: `CONTRIBUTING.md` SHALL provide examples that bound the size dimension on both ends — a tiny-but-coherent example (e.g., a sharpened EARS line plus its eval) and a larger-but-coherent example (e.g., an LLD section rewrite cascaded through specs and skill prose).
- `[x]` **PROJ-STRUCT-017**: `CONTRIBUTING.md` SHALL state that contributors SHOULD file an issue before walking the arrow on changes that may add new surface, and that changes fitting clearly within existing surface go straight to a PR.
- `[x]` **PROJ-STRUCT-018**: `CONTRIBUTING.md` SHALL describe a PR-description shape oriented to what reviewers find useful in practice: the motivation and impact, what changed, how the change was tested, and a lightweight statement of the arrow segments and EARS IDs touched (or that the change is trivial). It SHALL present the minimum-surface gate answers, cross-segment pause points, and dogfooding scenarios as items to include when the change involves them, rather than as a fixed checklist required of every PR. `.github/PULL_REQUEST_TEMPLATE.md` embodies this shape (`PROJ-STRUCT-053`).
- `[x]` **PROJ-STRUCT-070**: `CONTRIBUTING.md` SHALL give the command that runs the packaging checks and SHALL state that every pull request records, in its *Packaging checks* line, the result line of a run on its final commit, and merges only when every part of that run is *pass* or *skipped*; on a contributor's pull request the run that gates the merge is the maintainer's, after the version is raised (the run itself is specified in `PKG-CHECK`).

## AGENTS.md and CLAUDE.md

- `[x]` **PROJ-STRUCT-019**: An `AGENTS.md` file SHALL exist at the repository root and SHALL be the canonical source of per-repo agent instructions.
- `[x]` **PROJ-STRUCT-020**: A `CLAUDE.md` file SHALL exist at the repository root as a symlink resolving to `AGENTS.md`, so Claude Code (which reads `CLAUDE.md`) and tools that honor `AGENTS.md` natively read identical content with zero drift surface.
- `[x]` **PROJ-STRUCT-021**: `AGENTS.md` SHALL describe the LID workflow (`HLD → LLDs → EARS → Tests → Code`) and SHALL point at `docs/high-level-design.md` as the canonical methodology document.
- `[x]` **PROJ-STRUCT-022**: `AGENTS.md` SHALL include the project-level `## LID` block with a `- Mode:` bullet (e.g., `- Mode: Full`) so the workflow skill can detect the project's mode on entry.
- `[x]` **PROJ-STRUCT-068**: `AGENTS.md` SHALL state that the repository holds repository tooling under `tools/` — maintainer helpers such as the alternate-model eval runner — in addition to the plugins and the methodology docs, and that this tooling ships in no plugin.
- `[x]` **PROJ-STRUCT-071**: `AGENTS.md`'s editing guidelines SHALL state that a command file exists only as an alias under a name no skill in its plugin uses (`PROJ-STRUCT-073`), that each `description` is written in the preferred frontmatter form (`PROJ-STRUCT-076`), and that the packaging checks run before a pull request (`PROJ-STRUCT-070`).
- `[x]` **PROJ-STRUCT-023**: `AGENTS.md` SHALL provide a navigation table or equivalent index pointing at the canonical paths for the HLD, the LLDs directory, the EARS specs directory, the arrows index, and `docs/setup.md`.

## docs/setup.md

- `[x]` **PROJ-STRUCT-024**: A `docs/setup.md` file SHALL exist describing how non-Claude-Code agents adopt LID through their tool's per-project rule mechanism.
- `[x]` **PROJ-STRUCT-025**: `docs/setup.md` SHALL include a table or equivalent listing of tools that honor a repo-root `AGENTS.md` natively without requiring an adapter.
- `[x]` **PROJ-STRUCT-026**: `docs/setup.md` SHALL provide explicit per-tool rule-file adapter snippets for tools that need or benefit from a separate file (GitHub Copilot inline, and any other tool with a non-`AGENTS.md`-native path). The Cursor adapter snippet (`.cursor/rules/lid.mdc`) SHALL be presented as the lighter no-plugin alternative to installing the Cursor plugin, not as Cursor's only integration path.
- `[x]` **PROJ-STRUCT-027**: This repository SHALL NOT ship per-tool rule-file *adapter* files of its own (for example, it SHALL NOT contain a `.cursor/rules/lid.mdc` or `.github/copilot-instructions.md`); these are documented in `docs/setup.md` for users to drop into their own LID projects. Plugin *marketplace manifests* (`.claude-plugin/`, `.cursor-plugin/`) are NOT adapter files and ARE shipped — they register first-party plugins for a host's marketplace.
- `[x]` **PROJ-STRUCT-062**: `docs/setup.md` SHALL document the first-class plugin hosts (Claude Code and Cursor), each installing the LID plugins from its own marketplace. The Cursor section SHALL present the plugin install as the primary path and the rule-file adapter as the lighter alternative.
- `[x]` **PROJ-STRUCT-072**: `docs/setup.md` SHALL document opencode as a skills host: listing the core plugins' directories from a clone of this repository (`plugins/linked-intent-dev`, `plugins/arrow-maintenance`) under `skills.paths` in the user's opencode config, adding `plugins/lid-experimental` only to opt in, updating by pulling the clone, and stating that opencode loads no command aliases and that opencode 1.x ignores `disable-model-invocation`, so `lid-coach` and `map-codebase` are also model-invocable there.

## .claude-plugin/marketplace.json

- `[x]` **PROJ-STRUCT-028**: A `.claude-plugin/marketplace.json` file SHALL exist at the repository root and SHALL declare the repository as a Claude Code plugin source.
- `[x]` **PROJ-STRUCT-029**: `marketplace.json` SHALL list the three first-party plugins shipped from this repository: `linked-intent-dev`, `arrow-maintenance`, and `lid-experimental`. The `source` field for each plugin SHALL match an existing directory under `plugins/`.
- `[x]` **PROJ-STRUCT-030**: Each plugin entry in `marketplace.json` SHALL include `name`, `description`, `source`, `category`, and `license` fields, and SHALL NOT include `version`, which each plugin's `.claude-plugin/plugin.json` carries (`PROJ-STRUCT-046`).

## .cursor-plugin/marketplace.json

- `[x]` **PROJ-STRUCT-056**: A `.cursor-plugin/marketplace.json` file SHALL exist at the repository root declaring the repository as a Cursor plugin source, with the Cursor-required marketplace-level fields `name`, `owner`, and `plugins`.
- `[x]` **PROJ-STRUCT-057**: `.cursor-plugin/marketplace.json` SHALL list the three first-party plugins (`linked-intent-dev`, `arrow-maintenance`, `lid-experimental`). Each plugin entry SHALL include the Cursor-required `name` and `source`, plus `description`, `category`, and `license`. The `source` SHALL be the literal path `plugins/<name>` — the same directory the Claude manifest references — rather than a `pluginRoot`-relative form, so both hosts resolve plugins through one path convention.
- `[x]` **PROJ-STRUCT-058**: Each plugin directory SHALL contain a `.cursor-plugin/plugin.json` carrying at least `name` (and, for LID's plugins, `description` and `license`). The Cursor manifests (`.cursor-plugin/marketplace.json` and each `.cursor-plugin/plugin.json`) SHALL omit `version`, since `update-lid`'s version-walk reads the project `## LID` block and the CHANGELOG rather than any marketplace manifest.
- `[x]` **PROJ-STRUCT-060**: Each plugin's `name` SHALL be identical across every manifest that references it (`.claude-plugin/marketplace.json`, `.claude-plugin/plugin.json`, `.cursor-plugin/marketplace.json`, `.cursor-plugin/plugin.json`) and SHALL equal the plugin's directory name under `plugins/`, so a plugin carries one identity across both hosts.

## Repo-root file pointers

- `[x]` **PROJ-STRUCT-031**: A `README.md` file SHALL exist at the repository root. Its content is owned by `docs/intent/marketing-site/marketing-site-design.md`; this segment references its existence but does not claim its content.
- `[x]` **PROJ-STRUCT-055**: An `EXTENSIONS.md` file SHALL exist at the repository root. Its content is owned by `docs/intent/extensions/extensions-design.md`; this segment references its existence but does not claim its content.
- `[x]` **PROJ-STRUCT-032**: `CONTRIBUTING.md` SHALL link to `docs/high-level-design.md` and `AGENTS.md` for depth rather than restating their material, so the contributor surface does not duplicate the README or the methodology doc.

## LICENSE

- `[x]` **PROJ-STRUCT-033**: A `LICENSE` file SHALL exist at the repository root containing the MIT license under which the repository is distributed.

## .gitignore

- `[x]` **PROJ-STRUCT-059**: A `.gitignore` SHALL exclude the per-skill eval run-output trees (`plugins/*/skills/*-workspace/`) from version control, so these regenerable skill-creator outputs are absent from the repository and from both hosts' plugin bundles. The eval *definitions* (`plugins/*/skills/*/evals/evals.json`) SHALL NOT be ignored.

- `[x]` **PROJ-STRUCT-067**: The `.gitignore` SHALL ignore the `.claude/` directory except `.claude/settings.json`, so each contributor's `.claude/settings.local.json`, session data, and worktrees stay untracked while the shared settings file is tracked.

## .claude/settings.json

- `[x]` **PROJ-STRUCT-064**: A `.claude/settings.json` file SHALL be tracked in the repository, holding only Claude Code settings shared by everyone working in the repository.
- `[x]` **PROJ-STRUCT-065**: `.claude/settings.json` SHALL enable exactly the three first-party plugins from this repository's marketplace (`linked-intent-dev@jszmajda-lid`, `arrow-maintenance@jszmajda-lid`, `lid-experimental@jszmajda-lid`), and no other plugin.
- `[x]` **PROJ-STRUCT-066**: `.claude/settings.json` SHALL grant exactly one permission, the allow rule `Bash(tools/alt-model-evals/run_eval.py:*)` for the alternate-model eval runner, and no other.

## Cascade

- `[x]` **PROJ-STRUCT-034**: When HLD Goal 2 (minimum-system) is modified, the maintainer SHALL review `CONTRIBUTING.md`'s *Out of scope* and *Minimum-surface gate* sections for claim drift before the HLD change is considered complete.
- `[x]` **PROJ-STRUCT-035**: When HLD Goal 4 (dogfooding) is modified, the maintainer SHALL review `CONTRIBUTING.md`'s *Tests, or justify* framing and *Arrow variant by change type* section.
- `[x]` **PROJ-STRUCT-036**: When HLD § Key Design Decisions / *The arrow for LID itself* is modified — for example, a new variant is added or an existing one is revised — the maintainer SHALL update `CONTRIBUTING.md`'s arrow-variant decision tree to absorb the change.
- `[x]` **PROJ-STRUCT-037**: When a new plugin is added under `plugins/`, removed, or renamed, the maintainer SHALL update both marketplace manifests (`.claude-plugin/marketplace.json` and `.cursor-plugin/marketplace.json`), both per-plugin manifests (`.claude-plugin/plugin.json` and `.cursor-plugin/plugin.json`), and any install commands in `README.md` and `docs/setup.md` to match.
- `[x]` **PROJ-STRUCT-069**: When the alternate-model eval runner's entry point (`tools/alt-model-evals/run_eval.py`) moves or is renamed, the maintainer SHALL update the allow rule in `.claude/settings.json` in the same change.
- `[x]` **PROJ-STRUCT-038**: When a new agentic coding tool is added to the supported set, the maintainer SHALL update `docs/setup.md`; if the tool is a first-class plugin host, the maintainer SHALL additionally add its marketplace manifest, its per-plugin manifests, and a plugin-host section in `docs/setup.md`; if it is a skills host, the maintainer SHALL add a `docs/setup.md` skills-host section stating what the host does not load from the plugin layer; if it is rule-file-only, the maintainer SHALL add either a simple-path table row (native `AGENTS.md`) or a per-tool adapter section.
- `[x]` **PROJ-STRUCT-082**: When the rules for skill and command files, versions and releases, the CHANGELOG, or the marketplace manifests change, the maintainer SHALL update the packaging checks (`PKG-CHECK`) in the same change.
- `[x]` **PROJ-STRUCT-085**: When a skill gains or loses `disable-model-invocation`, the maintainer SHALL update `docs/setup.md`'s list of skills a skills host leaves model-invocable.
- `[x]` **PROJ-STRUCT-083**: When opencode changes how it finds or guards skills — a different `skills.paths` behavior, or a pinned version that honors `disable-model-invocation` — the maintainer SHALL update `docs/setup.md`'s skills-host section.

## Skill and Command Files

- `[x]` **PROJ-STRUCT-073**: Within one plugin, no command file `commands/<name>.md` SHALL share a name with a skill `skills/<name>/`; a command file SHALL exist only as an alias offering a skill under a different name.
- `[x]` **PROJ-STRUCT-074**: Each skill's frontmatter `name` SHALL equal its directory name and SHALL NOT repeat across the three plugins, and a command file's frontmatter `name`, when present, SHALL equal its filename without `.md`.
- `[x]` **PROJ-STRUCT-075**: Every skill and command `description` SHALL be at most 1,024 characters.
- `[x]` **PROJ-STRUCT-084**: Every skill and command file SHALL open with its frontmatter block (`---` on the first line, no byte-order mark or blank line before it) and use line feeds alone; its frontmatter SHALL carry no YAML comments and a non-empty `description`; and `disable-model-invocation`, where set, SHALL be written as the literal `true` or `false`.
- `[x]` **PROJ-STRUCT-076**: Every skill and command `description` SHOULD be written as a single-line double-quoted string containing no `"`, a literal `"` being reworded rather than escaped.

## CHANGELOG.md

- `[x]` **PROJ-STRUCT-043**: A `CHANGELOG.md` file SHALL exist with its canonical copy at `plugins/linked-intent-dev/CHANGELOG.md`, and the repository-root `CHANGELOG.md` SHALL be a symlink resolving to that canonical copy, so the changelog ships inside the `linked-intent-dev` plugin and `update-lid` can read it wherever the plugin is installed.
- `[x]` **PROJ-STRUCT-044**: `CHANGELOG.md` SHALL follow semantic versioning and the Keep a Changelog format. Each minor or major entry after 1.0.0 SHALL include exactly one migration section headed with the major.minor versions it moves between (`### Migration (v1.3 → v1.4)`), which `update-lid`'s version-walk reads to drive a guided upgrade; a patch entry SHALL include none. (1.4.1's entry, released before this rule, lists an optional workflow-doc refresh as a migration step; reconcile-conventions offers that refresh.)
- `[x]` **PROJ-STRUCT-045**: `CHANGELOG.md` SHALL hold only version entries, newest first: its first `## ` heading SHALL be `## [X.Y.Z]` for the current shared LID version, and no version heading SHALL repeat.
- `[x]` **PROJ-STRUCT-046**: The three plugins' `.claude-plugin/plugin.json` files SHALL carry the same `version`, the shared LID version, which is also the LID conventions version.
- `[x]` **PROJ-STRUCT-077**: When a merge changes any plugin's shipped files — its tracked files under `plugins/<plugin>/` other than any `evals/` directory, `CHANGELOG.md` included — the shared version SHALL rise to the next version after `main`'s (its next patch, minor, or major, none skipped) and `CHANGELOG.md` SHALL gain that version's entry; when no shipped file changes, the version SHALL stay equal to `main`'s.
- `[x]` **PROJ-STRUCT-078**: The size of a raise SHALL follow HLD § Architecture / Distribution / *What warrants a version change*: patch for a change that asks nothing of a project, minor or major for one a project adopts through migration steps. A patch SHALL demand no migration: optional refreshes it ships — template rewording, a changed workflow doc — reach projects through reconcile-conventions, and a change a project must make to stay correct SHALL be minor, with migration steps. For the instruction-file template, a wording fix SHALL therefore be a patch and a change to what the template tells an agent to do SHALL be minor.
- `[x]` **PROJ-STRUCT-079**: On a contributor's pull request, the maintainer SHALL raise the version, write the `CHANGELOG.md` entry, and regenerate the workflow doc before merging.
- `[x]` **PROJ-STRUCT-080**: `CHANGELOG.md` SHALL record changes to what the plugins ship, and SHALL NOT record work that ships in no plugin (the site, research, this repository's design docs and tooling).
- `[x]` **PROJ-STRUCT-081**: A release that spans several changes SHALL gather on a release branch and merge to `main` once, as one version.
- `[x]` **PROJ-STRUCT-063**: When a pull request changes shipped plugin files, the shipped workflow-doc asset (`plugins/linked-intent-dev/skills/update-lid/references/workflow-doc.md`) SHALL be regenerated with the packaging checks' assembly (`PKG-CHECK-036`), taking the new version as its stamp only when its assembled content changed.
- `[x]` **PROJ-STRUCT-054**: After each merge that raises the version, the maintainer SHALL publish a `v<version>` git tag on the merge commit and a GitHub Release with notes drawn from that version's `CHANGELOG.md` entry; a minor or major Release SHALL also create a linked discussion in the repository's Discussions **Announcements** category (`gh release create … --discussion-category Announcements`).

## Arrow Registration

- `[x]` **PROJ-STRUCT-042**: Where the `docs/arrows/` overlay is present in this repository, this segment SHALL appear as a named segment in `docs/arrows/index.yaml` with the same schema as plugin segments.

## CODE_OF_CONDUCT.md

- `[x]` **PROJ-STRUCT-047**: A `CODE_OF_CONDUCT.md` file SHALL exist at the repository root, SHALL adopt a recognized community standard (the Contributor Covenant), and SHALL name a private contact for enforcement reports.

## SECURITY.md

- `[x]` **PROJ-STRUCT-048**: A `SECURITY.md` file SHALL exist at the repository root that states LID ships no executable application code, identifies the realistic security surface (prompt content in skills and the build/tooling dependencies of `site/`), and routes reports to a private channel (GitHub's vulnerability-advisory flow or maintainer email) rather than to public issues.
- `[x]` **PROJ-STRUCT-049**: `SECURITY.md` SHALL state that vulnerabilities in a downstream project built using LID are out of scope, tying the boundary to the HLD Non-Goal *Not adversarial security review* — LID performs adversarial *coherence* review, not security review.

## CITATION.cff

- `[x]` **PROJ-STRUCT-050**: A `CITATION.cff` file SHALL exist at the repository root in the Citation File Format, carrying at minimum the project title, authorship, repository and website URLs, an abstract, and the license. It SHALL omit `version` and `date-released` so the file does not join the per-release version-sync surface defined by `PROJ-STRUCT-046`.

## Contribution Templates

- `[x]` **PROJ-STRUCT-051**: `.github/ISSUE_TEMPLATE/` SHALL provide an intent-proposal issue form whose sections are Context/Problem, Proposed change, Acceptance criteria, Scope & non-goals, Intent touchpoints (LID), and Related — where Intent touchpoints maps the change to the design docs, specs, and prefix it lands in and flags novel intent — and a separate, lighter bug/drift report form. Neither form SHALL auto-apply labels.
- `[x]` **PROJ-STRUCT-052**: `.github/ISSUE_TEMPLATE/config.yml` SHALL route open-ended questions to GitHub Discussions via a contact link rather than to issues.
- `[x]` **PROJ-STRUCT-053**: A `.github/PULL_REQUEST_TEMPLATE.md` file SHALL exist presenting, in order, the change's motivation and impact, what changed, how it was tested, a *Packaging checks* line for the result line of the run the merge rests on, a lightweight statement of the arrow segments and EARS IDs touched (or that the change is trivial), and optional reviewer notes. It SHALL NOT require the full minimum-surface / dogfooding / pause-point checklist on every PR (see `PROJ-STRUCT-018`).

## Superseded

- `[D]` **PROJ-STRUCT-039**: *Superseded by PKG-CHECK-018 — internal link integrity is a packaging check.*
- `[D]` **PROJ-STRUCT-040**: *Superseded by PKG-CHECK-019 — marketplace-manifest validity is a packaging check.*
- `[D]` **PROJ-STRUCT-041**: *Superseded by PKG-CHECK-020 — `CLAUDE.md` symlink integrity is a packaging check.*
- `[D]` **PROJ-STRUCT-061**: *Superseded by PROJ-STRUCT-045 and PROJ-STRUCT-077 — every shipped change is released as it merges, so the changelog holds only version entries.*
