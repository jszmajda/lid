---
parent: high-level-design
prefix: PKG-CHECK
---

# Packaging Checks

## Context and Design Philosophy

Users install LID's plugins from `main`, so a merge to `main` ships (HLD § Key Design Decisions / *Code and tests for LID*, test layer 3). The packaging checks confirm, before each merge, that what the plugins ship is well-formed and loads whole on a host that reads it.

They enforce rules other segments own, and leave those rules with their owners:
- the skill and command layout, the frontmatter form, the version and CHANGELOG rules, and the marketplace manifests, in `project-structure`;
- the skill size limits, in the `linked-intent-dev` core design.

The tool also assembles the shipped workflow doc, so the release step and the check use one recipe.

The tool lives at `tools/packaging-checks/`. It is ordinary code: it walks the standard arrow (`HLD → LLD → EARS → tests → code`) and carries `@spec` annotations. It ships in no plugin and is never installed into a user's project.

Three principles shape it:

- **Checks inspect this repository, not users' projects.** The checks verify what this repository ships, for the hosts that read it. They ask nothing of a project that installs LID, so they are distinct from enforcing the arrow in a user's project, which the HLD Non-Goal *Not a linter or validator* rules out.
- **Check exactly what merges.** A run checks one commit's tracked files against the current `main`, so its result speaks for the files that merge and for nothing else.
- **Observe the host, not the model.** The host-loading check reads what the host recorded about the session, not the model's account of what it was shown. Its result then describes the host's configuration, not the capability of the model that happened to run.

## What a run checks

A run names one commit: the commit the pull request will merge. By default it is the commit holding the current change — in a jj repository `@`, or `@-` when `@` is empty; otherwise git's `HEAD` — and any commit can be named instead. The run checks an export of that commit's tracked files into a scratch directory and reads no checked file from the working copy, so uncommitted edits and the gitignored eval run-output trees cannot reach the result. (Under jj every file not ignored belongs to `@`, so the run checks what a push of that commit would carry.) The tool itself runs from the same export, so a pull request that changes a rule and its check is checked by its own version of the check; the recorded tree hash covers the tool too.

The run fetches `main` from `github.com/jszmajda/lid`, whatever the local remotes are named, and compares against that, never against a local copy; it reads that repository's tags there too. The checked commit must contain `main`'s tip; otherwise the static part fails, saying to bring the branch up to date, and the checks that compare against `main` are not evaluated. So the files that merge are the files that were checked. When `main` cannot be fetched, the checks that compare against it report *error*.

A run has three parts — **static**, **Claude Code**, and **opencode** — and each reports one state (see *Result states*). The host parts run whatever the static part found, since what a host loads is useful even from a tree with a known fault.

## Static checks

The static checks read files and need no model. They enforce the rules in `project-structure` § *Skill and command files*, § *Versions and releases*, and § *`CHANGELOG.md`*, and the core design's size limits.

**Frontmatter.** These cover every file a plugin host reads to register a skill or command: each `plugins/<plugin>/skills/<skill>/SKILL.md` and each `plugins/<plugin>/commands/<name>.md`.

Hosts differ in how they read frontmatter:
- A lenient reader may recover a value a strict parser rejects. A strict reader may reject what a lenient one recovers: PyYAML keeps the last of two repeated keys, while opencode's parser throws and drops the skill. So a file can load in the author's host and fail in another.
- A YAML reader treats ` #` in an unquoted value as the start of a comment and drops the rest of the value. The result is still valid YAML, so it parses, and the host loads a truncated description that has lost its trigger text.

The checks therefore test outcomes, whatever scalar form a value is written in:

- **A frontmatter block opens the file.** The file's first bytes are exactly `---` and a line feed, with no byte-order mark and no leading blank line or whitespace, and a later line is exactly `---`. The file's lines end in a line feed alone. Otherwise the file fails with "no frontmatter block" (or "line endings"). A host that misses the opening sees no frontmatter and loads the file with no name, description, or invocation guard.
- **Parses to a mapping, with no repeated key.** The block parses to a mapping under PyYAML's safe loader, extended to reject a repeated key.
- **Names and descriptions.**
  - A `SKILL.md` has a non-empty `name` equal to its directory name.
  - A command file's `name`, when present, equals its filename without `.md`.
  - Every file has a non-empty `description` of at most 1,024 characters.
- **No `#` is read as a comment.** The block is parsed a second time with every `#` replaced by a printable character with no meaning in YAML that does not otherwise occur in the file, and that character is mapped back to `#` in the parsed values. If the second parse fails or yields different values, a `#` was read as a comment, and the check fails naming the field, or the line when the first parse already dropped it. Frontmatter therefore carries no YAML comments: every `#` in it is part of a value.
- **The guard is a literal boolean.** `disable-model-invocation`, when present, is written as the literal `true` or `false`. PyYAML reads `yes` as true, while opencode's parser reads it as the string "yes", so any other spelling means different things on different hosts.
- **Names are unique.**
  - No command file shares a name with a skill in its plugin (`project-structure` § *Skill and command files*: one file per invocable name).
  - No skill name repeats across the three plugins, because a host that loads them into one namespace keeps whichever loads last.

**Size.** Each `SKILL.md` body is under 50,000 bytes, and no line in a file under a skill's directory (its `evals/` aside) runs past 2,000 characters. These are the limits the `linked-intent-dev` core design sets so every harness loads a skill whole. The byte limit sits below opencode's 51,200-byte cut on a tool's output, leaving room for the wrapper a host puts around the body.

**Versions.** "The version" below is the shared version, read from `linked-intent-dev`'s `plugin.json` even when the plugins disagree.

- The three `.claude-plugin/plugin.json` files carry the same `version`, of the form `X.Y.Z`. No Cursor manifest and no entry in either marketplace manifest carries one.
- Every `## ` heading in the CHANGELOG is a version heading, `## [X.Y.Z]` optionally followed by ` — YYYY-MM-DD`, in descending order with none repeated, and the first is the version.
- When any plugin's shipped files differ from `main`, the version is the next one after `main`'s: its next patch (`X.Y.Z+1`), next minor (`X.Y+1.0`), or next major (`X+1.0.0`). When none differ, it equals `main`'s.
- When the major.minor rises, the top entry holds exactly one `### Migration` heading, and it reads `### Migration (v<main's major.minor> → v<new major.minor>)`. A patch entry holds none.
- The shipped workflow doc, apart from its stamp line, equals a fresh assembly of the current core skill source (see *Workflow-doc assembly*). Its stamp names the version in which that content last changed: the new version when the assembled content differs from the doc on `main`, otherwise `main`'s stamp.
- `main`'s version has a `v<version>` tag, so a forgotten tag is caught by the next pull request's run.

**Repository structure:**
- internal markdown links in `CONTRIBUTING.md` and `docs/setup.md` resolve to existing files and anchors;
- both marketplace manifests are valid JSON whose plugin `source` paths resolve to directories under `plugins/`;
- `CLAUDE.md` is a symlink resolving to `AGENTS.md`.

## Host-loading check

The host-loading check loads each plugin the way a host does and observes what the host delivers to the model. It tests host configuration, not model capability: a host that can report its loaded skills without a model is read directly, and a host that cannot runs one model, named in the tool and printed with its result.

**Observation.** Each assertion is read from the host's own record of the session, not from the model's account of it. The one assertion that needs the model to act — calling a guarded skill, to see the host refuse — gets a prompt asking for that single action, and a model that does not take it leaves the assertion *inconclusive*, never passed.

**Claude Code.** The check runs `claude -p` with each plugin loaded from the export (`--plugin-dir`). It runs in a scratch directory outside any repository, loading no user or local settings and no other plugin, so the plugins' skills share the listing only with Claude Code's own bundled skills and the user's personal skills, which no setting excludes without also losing the login; the result records how many such entries shared it. The listing has a size budget and settings can trim its entries, so a run in the maintainer's own environment would vary from person to person. Claude Code records what it did in two places the check reads: the session's opening event, which names each loaded plugin with its version and each registered skill and command; and the session transcript, which holds the skill listing shown to the model and the text an invocation delivered. The transcript's format is Claude Code's own and undocumented, so a version that changes it makes this part report *error*, never *pass*; the check removes the transcripts its runs write. The check confirms that:
- each plugin loaded at the export's version;
- each skill's and each command file's name is registered exactly once;
- invoking each skill by its slash name delivers text containing its `SKILL.md` body, byte for byte through its last line (Claude Code puts a base-directory line before it);
- each skill the model may invoke is listed with its `SKILL.md` description;
- each skill whose frontmatter sets `disable-model-invocation: true` is absent from the model's listing, and a model call to it is refused.

**opencode.** The check runs in the alternate-model eval runner's container, at the runner's pinned opencode version, with the export's `plugins/` listed under `skills.paths`, which loads all three plugins. opencode reports the skills it has loaded, with each one's name, description, and the content its skill tool serves (`opencode debug skill`), so this part reads that record and runs no model. For each skill the check confirms that:
- it is discovered under its name with its full `SKILL.md` description;
- the content opencode serves for it is its `SKILL.md` body, whole.

opencode 1.x ignores `disable-model-invocation` and loads no command files. The result reports both as known host limits ("guard: not honored", "command aliases: not loaded"), not as failures. It reports the guard as honored only when every guarded skill is absent from opencode's report or marked there as not model-invocable — as opencode's v2 line may do — so a pinned version that starts honoring the guard visibly changes the result, and the limit stated in `docs/setup.md` is revisited.

**Other hosts.** Cursor, and the tools that read only `AGENTS.md`, have no harness in this repository. Their documentation and users' bug reports cover them.

## Result states

Each part of a run reports one state:

- **pass** — every assertion held.
- **fail** — a file or host loaded something wrong. The report names the file or skill and the assertion.
- **inconclusive** — the model did not take an action an assertion needed. This says nothing about the plugins either way.
- **error** — something the part needs could not run or be read (no login, a container or network failure, a fetch of `main`, a host record in a format the check does not know). This is not a statement about the plugins.
- **skipped** — a host part found nothing that could change what it loads, so there was nothing new to check.
- **owed** — the person running the tool opted out of the host parts (`--no-host`), and the maintainer runs them before merge.

A part with mixed outcomes reports *fail* if any assertion failed; otherwise *error* if anything could not run or be read; otherwise *inconclusive* if any assertion was; otherwise *pass*. A host part that cannot start at all, such as one run without a Claude Code login, reports *error*, and the message suggests `--no-host`. A pull request merges only when every part is *pass* or *skipped* (`project-structure` § *Versions and releases*). The tool reports every failure with its file or skill and reason, and exits non-zero unless every part is *pass* or *skipped*.

## When it runs, and the record

Every pull request records a run before it merges. There is no hosted CI: whoever prepares the pull request runs the tool and pastes the one-line result it prints into the pull request's *Packaging checks* line. The line records:
- the checked commit and its tree hash;
- the `main` commit it was compared against;
- each part's state, naming for a static failure which check groups failed (frontmatter, size, versions, structure);
- for each host part, the host version, the model where the part runs one, and for Claude Code the isolation used.

A push after the run therefore visibly needs a new one.

The static part always runs. The host parts run when anything that could change what a host loads differs from `main` — a shipped plugin file, the tool itself, or the alternate-model runner's Dockerfile or harness pin (`tools/alt-model-evals/Dockerfile`, `tools/alt-model-evals/run_eval.py`) — and report *skipped* otherwise.

On a contributor's pull request, the maintainer owns raising the version, writing the CHANGELOG entry, and regenerating the workflow doc (`project-structure` § *Versions and releases*). A contributor's run may therefore fail only the version checks, and its host parts may be *owed*. The run that gates the merge is the maintainer's, on the final commit, after the version is raised.

The tool's tests run the static checks against fixture files that exercise each failure, with a local fixture repository standing in for the GitHub remote. They run the host parts against stub hosts, as the alternate-model runner's tests do, so the tests need no model, key, or network.

## Workflow-doc assembly

The tool assembles the shipped workflow doc (`plugins/linked-intent-dev/skills/update-lid/references/workflow-doc.md`) from the core skill source, deterministically, so the same source always yields the same doc:

1. A generated-file header: an HTML comment whose stamp line names the version (`Assembled from the linked-intent-dev plugin (version X.Y.Z) at release.`), the title, and the repository-reference note that tells a harness without the plugins how to read the doc.
2. The `linked-intent-dev` skill's `SKILL.md` body, without its frontmatter, with its `## LID-on-LID exception` section removed (the heading through the line before the blank line that precedes the next `## ` heading).
3. Each reference file, in the order the body's *Reference files* list names them, preceded by a `---` rule and an `<!-- Appended reference: <file> -->` comment.

The release step runs it (`project-structure` § *Versions and releases*), and the version checks compare the shipped doc against a fresh assembly. A doc left stale after a later source edit therefore fails, and an edit that leaves the assembled content unchanged, such as one inside the removed section, needs no new stamp.

## Cascade

- **`project-structure`'s rules change** (*Skill and command files*, *Versions and releases*, *`CHANGELOG.md`*, the marketplace manifests) → the static checks update in the same change.
- **The `linked-intent-dev` core design's size limits change** → the size check updates in the same change.
- **Where a host reads skills or commands changes** → the checks' file discovery updates in the same change.
- **A host is found to misread frontmatter in a way the checks do not cover** → the checks gain a rule, and `project-structure`'s preferred form is re-examined against it.
- **A host's loading behavior changes** (a Claude Code or opencode upgrade, or a bug report from another host) → the host-loading check reruns. A new failure walks the arrow like any bug. A rule the design depends on (which of a same-named command and skill wins; whether opencode honors the guard) is re-measured.
- **The alternate-model eval runner's container, pinned opencode version, or staging changes** → the opencode part updates with it, and `docs/setup.md`'s opencode section is checked against the new staging.
- **The core skill source's layout changes** (a reference file added or renamed, the exception section renamed) → the workflow-doc assembly updates in the same change.
- **The tool's entry point moves or is renamed** → `CONTRIBUTING.md`, `AGENTS.md`, and the pull-request template update in the same change.

## Decisions & Alternatives

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Home for the packaging checks | A segment of its own | Inside `project-structure`, beside the rules it enforces; each rule restated in the design doc of each plugin it protects | The rules stay with their owners. The tool carries design decisions of its own beyond them: what a run checks, how hosts are observed, result states, isolation, host coverage, the contributor flow, and workflow-doc assembly. That is the same reason the alternate-model eval runner is a segment. Per-plugin ownership would triplicate each rule. |
| Shipped-frontmatter verification | A static check run before every merge, plus `project-structure`'s preferred form | A convention in `AGENTS.md` alone; reviewer attention | The failure is invisible where the edit is made: the author's host may read the file leniently, and a comment-truncated description is valid YAML that loads. A convention alone depends on the same attention that misses it. The check inspects only this repository's shipped files and asks nothing of a user's project, so it is not the arrow enforcement the HLD Non-Goal *Not a linter or validator* rules out. |
| What the frontmatter checks enforce | Outcomes in any scalar form: an opening block, a strict parse with no repeated key, names and descriptions, no `#` read as a comment, a literal-boolean guard, unique names | Enforce the preferred form; flag only comments that truncate a value, allowing full-line comments; rely on PyYAML's defaults | A value in any form that parses whole is correct for every YAML reader, so failing it on form would block a correct file. To a parser a full-line comment and a truncating ` #` are the same token, so allowing no comments keeps the rule exact, and frontmatter has no use for them. PyYAML's defaults are the lenient reader on repeated keys and on `yes`/`no`, where opencode's parser rejects or reads differently, so the check tightens them. |
| Frontmatter parser | PyYAML's safe loader, extended to reject repeated keys, with the tool's own tests | `claude plugin validate`; the Agent Skills reference validator (`skills-ref`) | `claude plugin validate` checks manifests and passes a skill file whose frontmatter a strict parser rejects. `skills-ref` covers `SKILL.md` but not command files, and cannot see truncation, since a truncated value is still valid YAML. One common dependency covers every rule and both file kinds. |
| What a run checks | An export of one named commit's tracked files, checked by the tool from that same export, compared against `main` fetched from `github.com/jszmajda/lid` at run time, which the commit must contain | The working copy; the local `main`, or `main` from whichever remote is named `origin`; the point where the branch left `main`; the tool from the working copy or from `main` | Claude Code loads a `--plugin-dir` plugin in place, so a working-copy run includes uncommitted edits, untracked files, and gitignored eval trees, and can certify files that never merge. A stale local `main` lets two pull requests each pass while shipping different files as the same version. The branch point misses versions merged since. Requiring the checked commit to contain `main`'s tip makes the merged files the checked files. A contributor's `origin` is their fork, whose `main` may be stale, so the canonical repository is named outright. Running the commit's own copy of the tool lets a change to a rule and its check land together, as the cascade requires; a pull request that loosened its own check would show it in the diff under review. |
| How the host is observed | The host's own records: Claude Code's opening event and session transcript; opencode's report of its loaded skills | The model's own account of its listing; a verbatim repeat by a model with no file-reading tools | A check resting on the model's account tests the model, and the host-loading check exists to test the host. Both hosts record what they loaded and showed the model, so only the guard's refusal needs a model action. Claude Code's transcript format is undocumented, which the check accepts by reporting a format it cannot read as *error*: an upgrade then needs the check updated, never silently passes. |
| Isolation for the Claude Code run | A scratch directory outside any repository, no user or local settings, no other plugins; the bundled and personal skills that still share the listing are counted in the result | The maintainer's usual environment; a throwaway configuration directory | The skill listing has a size budget, beyond which descriptions are dropped, and settings can trim or override entries. A run in a full environment could pass for one person and fail for another. A throwaway configuration directory would remove the personal skills too, but it also drops the login the run needs. |
| Host-loading coverage | Claude Code, with one model; opencode, read from its own skill record with no model | Claude Code only; every host LID documents; several models per host | A loading failure is a fact about host configuration — which file supplies a name, whether a description and body arrive whole, whether a guard holds — not about the model reading it, so one model exposes it, and a host that reports its loaded skills needs none. Claude Code is the richest plugin host and the one the plugins are written against. opencode is a supported skills host and the harness LID's alternate-model evals run on, so the check reuses that runner's container and staging. Cursor and the `AGENTS.md`-reading tools have no harness here, so their documentation and users' bug reports cover them. |
| Result states | pass, fail, inconclusive, error, skipped, owed, with fail taking precedence in a part, then error, then inconclusive; only pass and skipped allow a merge; *owed* only by opting out with `--no-host` | Pass and fail only; *owed* inferred whenever a host part cannot start | An infrastructure failure or a model that did not act says nothing about the plugins. Reporting either as a failure sends people chasing bugs that do not exist; reporting either as a pass lets a broken plugin merge. A real failure is the most useful thing a part can report, so it outranks an infrastructure problem in the same part. An explicit opt-out keeps a missing login from silently becoming someone else's job: without the flag, the run says what went wrong and how to opt out. |
| Where the checks run | On the machine of whoever prepares a pull request, before it merges, with the result line recorded in the pull request; the maintainer's final run gates the merge | A hosted CI workflow on each pull request; a run only when a version is cut | The repository has one maintainer and runs no hosted CI. The host-loading check needs a Claude Code login and a container runtime, which hosted CI would have to provide, holding the login as a secret and paying for model use on every run. Every merge to `main` ships, so a run only at version cuts would miss what merges between them. The result line names the commit and tree it checked, so a reviewer can see whether the run covers the final commit. The checks are one command, so moving them into hosted CI later takes only a workflow file. |
| Workflow-doc assembly | A deterministic assembly in this tool, run by the release step and re-run by the check | Assembly by hand at release, following a prose recipe | A hand assembly cannot be checked: a doc left stale after a later source edit still differs from `main` and carries the new stamp. One assembly serves both the release step and the check. It is repository tooling that ships in no plugin. |
| Untagged version | The static checks fail when `main`'s version has no `v<version>` tag | Rely on the release step alone | A project's instruction file links to the workflow doc at the tag of its recorded version, so a missing tag is a broken link for every project recorded at that version. The next pull request's run is the first point a check can see it. |
| Host parts after a static failure | Run anyway | Stop after the static part, with a state for "not run" | What a host loads from a tree with a known fault still tells the author something — often the same fault, seen from the host's side — and the host parts are cheap. Stopping early would need a seventh state for little gain. |
| Size limit in bytes | A `SKILL.md` body under 50,000 bytes | 51,200 bytes (opencode's cut) | The hazard is opencode cutting a tool's output past 51,200 bytes, and that output wraps the body in the host's own text, so a body just under the cut would still lose its tail. 50,000 bytes reads the core design's "under 50 KB" in the way that leaves room for the wrapper. |
| Line endings in frontmatter files | A line feed alone | Line feed or carriage return plus line feed | The check exists so a file loads the same on every host. A file saved with carriage returns is a host-by-host risk for no benefit, and every file in the repository uses line feeds. |

## Open Questions & Future Decisions

### Deferred

1. **Host upgrades between pull requests.** Nothing triggers the host-loading check when only Claude Code or opencode is upgraded and no pull request is open. The maintainer reruns it by hand after an upgrade. A scheduled run would need the hosted CI this repository does not run.

## References

- `docs/high-level-design.md` — § Key Design Decisions / *Code and tests for LID* (test layer 3); Non-Goal *Not a linter or validator*; § Architecture / Distribution.
- `docs/intent/project-structure/project-structure-design.md` — the layout, frontmatter, version, CHANGELOG, and manifest rules these checks enforce; `docs/setup.md`, which states opencode's setup and limits.
- `docs/intent/linked-intent-dev/linked-intent-dev-design.md` — the skill size limits; the core skill source the workflow doc is assembled from.
- `docs/intent/linked-intent-dev/update-lid/update-lid-design.md` — how projects vendor and re-sync the workflow doc; the version-walk that reads the CHANGELOG's migration sections.
- `docs/intent/alt-model-evals/alt-model-evals-design.md` — the runner whose container and skill staging the opencode part reuses.
- `tools/packaging-checks/` — the tool.
