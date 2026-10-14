# Arrow: packaging-checks

The packaging checks — a maintainer tool, run before every merge to `main`, that confirms what the plugins ship is well-formed and loads whole on a host: static checks on frontmatter, sizes, versions, the CHANGELOG, the workflow doc, links, manifests, and the `CLAUDE.md` symlink, and host-loading checks that load the plugins into Claude Code and opencode and read what each host recorded. The pull request records the tool's one-line result. It also assembles the shipped workflow doc.

## Status

**MAPPED** — new leaf segment (#86, #87), sampled 2026-10-24, not yet audited. Tool and tests built; the specs are implemented apart from the pull-request process the tool cannot itself verify.

## References

### HLD
- `docs/high-level-design.md` § *Code and tests for LID* — test layer 3, *Packaging checks* (merge gate); Non-Goal *Not a linter or validator* (scoped to users' projects)

### LLD
- `docs/intent/packaging-checks/packaging-checks-design.md`

### EARS
- `docs/intent/packaging-checks/packaging-checks-specs.md` (prefix `PKG-CHECK-*`)

### Tests
- `tools/packaging-checks/test_packaging_checks.py` — fixture trees for every static failure, stub Claude Code and opencode hosts, and a local git repository with a bare remote standing in for GitHub. Run: `python3 tools/packaging-checks/test_packaging_checks.py`.

### Code
- `tools/packaging-checks/packaging_checks.py` — the tool (Python 3.9+, PyYAML)

## Architecture

**Purpose:** Make "a merge to `main` ships" safe without hosted CI: the person preparing a pull request runs one command and records its result.

**Key Components:**
1. **Run target** — an export of one commit's tracked files (jj `@`/`@-` or git `HEAD` by default), checked by that export's copy of the tool against `main` fetched from `github.com/jszmajda/lid`.
2. **Static part** — frontmatter outcomes under a strict parser (opening block, repeated keys, names, description length, `#` read as a comment, literal-boolean guard, name collisions), size limits, the shared version and its CHANGELOG entry and migration heading, the workflow doc against a fresh assembly, the tag for `main`'s version, links, manifests, symlink.
3. **Claude Code part** — `claude -p` with the plugins loaded by `--plugin-dir` in an isolated scratch directory; reads the session's opening event and transcript for registration, plugin versions, the model's skill listing, delivered bodies, and the refusal of guarded skills; removes the transcripts it writes.
4. **opencode part** — the alternate-model runner's container and staging; reads `opencode debug skill`, with no model.
5. **Result line** — commit and tree, `main`, each part's state (pass, fail, inconclusive, error, skipped, owed), host versions and model.

## Key Findings

1. **The Claude Code part catches #86 on `main`.** Run against `main` before this change, it fails with the stub's description in the model's listing, the guarded `map-codebase` listed and not refused, and both slash invocations delivering the stub's body.
2. **Both hosts record what they loaded.** Claude Code's session transcript holds the skill listing and the delivered skill text; opencode reports its loaded skills with their content. Only the guard's refusal needs a model to act.
3. **Claude Code's transcript format is undocumented.** A Claude Code version that changes it makes the part report *error*, not *pass*; the check is updated then.

## Work Required

### Must Fix
- None.

### Should Fix
- None.

### Nice to Have
- A scheduled host-loading run, if the repository ever gains hosted CI (host upgrades between pull requests are otherwise caught only by a manual rerun).
