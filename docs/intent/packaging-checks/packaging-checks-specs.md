# Packaging Checks Specs

**LLD**: docs/intent/packaging-checks/packaging-checks-design.md
**Implementing artifacts**:
- tools/packaging-checks/packaging_checks.py
- tools/packaging-checks/test_packaging_checks.py

Status markers: `[x]` implemented · `[ ]` active gap · `[D]` deferred

## What a Run Checks

- `[x]` **PKG-CHECK-001**: A run SHALL check an export of one named commit's tracked files into a scratch directory — by default the commit holding the current change (in a jj repository `@`, or `@-` when `@` is empty; otherwise git's `HEAD`) — SHALL run the checks from that export's copy of the tool, and SHALL NOT read any checked file from the working copy.
- `[x]` **PKG-CHECK-002**: A run SHALL fetch `main` from `github.com/jszmajda/lid`, whatever the local remotes are named, compare against the fetched tip, and read that repository's tags there. When the checked commit does not contain that tip, the static part SHALL fail, saying to bring the branch up to date, and the checks that compare against `main` SHALL NOT be evaluated. When `main` cannot be fetched, those checks SHALL report *error*.
- `[x]` **PKG-CHECK-038**: A run SHALL have three parts — static, Claude Code, and opencode — and the host parts SHALL run whatever the static part found.

## Static Checks: Frontmatter

These cover every `plugins/<plugin>/skills/<skill>/SKILL.md` and every `plugins/<plugin>/commands/<name>.md` in the export.

- `[x]` **PKG-CHECK-003**: The run SHALL fail a file with "no frontmatter block" unless its first bytes are exactly `---` followed by a line feed and a later line is exactly `---`, and SHALL fail a file any of whose lines ends in a carriage return.
- `[x]` **PKG-CHECK-004**: The run SHALL fail a file unless its frontmatter block parses to a mapping under PyYAML's safe loader extended to reject a repeated key.
- `[x]` **PKG-CHECK-005**: The run SHALL fail a `SKILL.md` unless its `name` is a non-empty string equal to its directory name, and SHALL fail a command file whose `name` is present and differs from its filename without `.md`.
- `[x]` **PKG-CHECK-006**: The run SHALL fail a file unless its `description` is a non-empty string of at most 1,024 characters.
- `[x]` **PKG-CHECK-007**: The run SHALL parse the frontmatter block a second time with every `#` replaced by a printable character with no meaning in YAML that does not otherwise occur in the file, mapped back to `#` in the parsed values, and SHALL fail the file — naming the field, or the line when no field is affected — when the second parse fails or yields different values.
- `[x]` **PKG-CHECK-008**: The run SHALL fail a file whose `disable-model-invocation` is present and written as anything other than the literal `true` or `false`.
- `[x]` **PKG-CHECK-009**: The run SHALL fail when a command file shares a name with a skill in its plugin — comparing the command's filename and frontmatter `name` with each skill's directory name and frontmatter `name` — or when a skill name repeats across the plugins.

## Static Checks: Size

- `[x]` **PKG-CHECK-010**: The run SHALL fail a `SKILL.md` whose body after the frontmatter block is 50,000 bytes or larger.
- `[x]` **PKG-CHECK-011**: The run SHALL fail any line longer than 2,000 characters in a file under a skill's directory, other than its `evals/` directory.

## Static Checks: Versions

"The version" is the `version` in `plugins/linked-intent-dev/.claude-plugin/plugin.json`, in the checked commit or on `main`, even when the plugins disagree.

- `[x]` **PKG-CHECK-012**: The run SHALL fail unless the three `.claude-plugin/plugin.json` files carry the same `version` of the form `X.Y.Z`, and SHALL fail when any `.cursor-plugin/plugin.json`, or any plugin entry in either marketplace manifest, carries a `version`.
- `[x]` **PKG-CHECK-013**: The run SHALL fail unless every `## ` heading of `plugins/linked-intent-dev/CHANGELOG.md` is `## [X.Y.Z]`, optionally followed by ` — YYYY-MM-DD`, the headings run in descending version order with none repeated, and the first is the version.
- `[x]` **PKG-CHECK-014**: When any plugin's shipped files — its tracked files under `plugins/<plugin>/` other than any `evals/` directory — differ from `main`, the run SHALL fail unless the version is the next patch, minor, or major after `main`'s; when none differ, it SHALL fail unless the version equals `main`'s.
- `[x]` **PKG-CHECK-015**: When the version's major.minor differs from `main`'s, the run SHALL fail unless the top CHANGELOG entry holds exactly one `### Migration` heading and it reads `### Migration (v<main major.minor> → v<new major.minor>)`; when only the patch differs, the run SHALL fail if the top entry holds a `### Migration` heading.
- `[x]` **PKG-CHECK-016**: The run SHALL fail unless the shipped workflow doc, apart from its stamp line, equals a fresh assembly of the current core skill source (`PKG-CHECK-036`), and unless its stamp names the new version when the assembled content differs from the doc on `main`, and `main`'s stamp otherwise.
- `[x]` **PKG-CHECK-017**: The run SHALL fail when `main`'s version has no `v<version>` tag on `github.com/jszmajda/lid`.

## Static Checks: Repository Structure

- `[x]` **PKG-CHECK-018**: The run SHALL fail when an internal markdown link in `CONTRIBUTING.md` or `docs/setup.md` resolves to a missing file or anchor.
- `[x]` **PKG-CHECK-019**: The run SHALL fail when either `.claude-plugin/marketplace.json` or `.cursor-plugin/marketplace.json` is not valid JSON, or when a plugin `source` in it does not resolve to a directory under `plugins/`.
- `[x]` **PKG-CHECK-020**: The run SHALL fail unless `CLAUDE.md` is a symlink resolving to `AGENTS.md`.

## Host Loading: Claude Code

- `[x]` **PKG-CHECK-021**: The Claude Code part SHALL run `claude -p` with every plugin from the export loaded by `--plugin-dir`, from a scratch directory outside any repository, loading no user or local settings and no other plugin, and SHALL record the Claude Code version, the model, and the number of other entries that shared the skill listing.
- `[x]` **PKG-CHECK-022**: The Claude Code part SHALL confirm that each plugin loaded at the export's version and that each skill's and each command file's namespaced name is registered exactly once.
- `[x]` **PKG-CHECK-023**: For each skill, the Claude Code part SHALL confirm that invoking it by its slash name delivers text containing its `SKILL.md` body, byte for byte through its last line.
- `[x]` **PKG-CHECK-024**: For each skill without `disable-model-invocation: true`, the Claude Code part SHALL confirm that the model's skill listing carries the skill's `SKILL.md` description.
- `[x]` **PKG-CHECK-025**: For each skill with `disable-model-invocation: true`, the Claude Code part SHALL confirm that the skill is absent from the model's listing and that a model call to it is refused.
- `[x]` **PKG-CHECK-026**: The Claude Code part SHALL read its assertions from Claude Code's own records — the session's opening event and the session transcript — and SHALL report *error* when it cannot read them. The guarded-skill call (`PKG-CHECK-025`) SHALL be *inconclusive*, never *pass*, when the model does not make it. The part SHALL remove the session transcripts its runs write.

## Host Loading: opencode

- `[x]` **PKG-CHECK-027**: The opencode part SHALL run in the alternate-model eval runner's container at the runner's pinned opencode version, with the export's `plugins/` listed under `skills.paths`, SHALL read opencode's own record of its loaded skills (`opencode debug skill`) without running a model, and SHALL record the opencode version in its result.
- `[x]` **PKG-CHECK-028**: For each skill, the opencode part SHALL confirm that the skill is discovered under its name with its full `SKILL.md` description and that the content opencode serves for it equals its `SKILL.md` body.
- `[x]` **PKG-CHECK-029**: The opencode part SHALL report its handling of `disable-model-invocation` and of command files as known host limits ("guard: not honored", "command aliases: not loaded") without failing on them, and SHALL report the guard as honored only when every skill declaring `disable-model-invocation: true` is absent from opencode's report or marked there as not model-invocable.

## Results and the Record

- `[x]` **PKG-CHECK-030**: Each part SHALL report exactly one state — *pass*, *fail*, *inconclusive*, *error*, *skipped*, or *owed* — taking *fail* if any assertion failed, otherwise *error* if anything it needed could not run or be read, otherwise *inconclusive* if any assertion was, otherwise *pass*; and the tool SHALL exit non-zero unless every part is *pass* or *skipped*.
- `[x]` **PKG-CHECK-031**: The static part SHALL always run. The host parts SHALL run when a shipped plugin file, a file under `tools/packaging-checks/`, `tools/alt-model-evals/Dockerfile`, or `tools/alt-model-evals/run_eval.py` differs from `main`, and SHALL report *skipped* otherwise.
- `[x]` **PKG-CHECK-032**: When the person running the tool passes `--no-host` and the host parts would otherwise run, they SHALL report *owed*. A host part that cannot start (no login, no container runtime) SHALL report *error* with a message suggesting `--no-host`.
- `[x]` **PKG-CHECK-033**: The tool SHALL print one result line naming the checked commit and its tree hash, the `main` commit it was compared against, each part's state with the failing check groups of a failed static part, and for each host part the host version, the model where the part runs one, and the Claude Code isolation.
- `[x]` **PKG-CHECK-034**: The tool SHALL report every failure with the file or skill it concerns and the reason.

## Workflow-Doc Assembly

- `[x]` **PKG-CHECK-036**: The tool SHALL assemble the workflow doc deterministically: a generated-file header whose stamp line names a given version, followed by the title and the repository-reference note; then the `linked-intent-dev` skill's `SKILL.md` body without its frontmatter and with its `## LID-on-LID exception` section removed; then each reference file, in the order the body's *Reference files* list names them, each preceded by a `---` rule and an `<!-- Appended reference: <file> -->` comment.

## Tests

- `[x]` **PKG-CHECK-037**: The tool's tests SHALL exercise each static failure with fixture files and a local fixture repository standing in for the GitHub remote, and the host parts with stub hosts, so they need no model, key, or network.
