# /arrow-maintenance audit-and-update pass — 2026-04-18

## Files modified

- `docs/arrows/index.yaml` — refreshed `last_updated`, `audited`, `audited_sha` on the `auth` segment; populated `next` and `drift` to reflect the missing eval coverage.
- `docs/arrows/auth.md` — brought the arrow doc in line with the template: Status line now carries last-audited date + SHA, added HLD / Tests / Code subsections (Tests and Code explicitly empty since none exist yet), added a Spec Coverage table and Key Findings / Work Required sections derived from the current source scan.

No other files were modified — this was a pure overlay-maintenance pass.

## Audit report

### 1. Reference coherence
- `auth`: all cited paths resolve — `docs/llds/auth.md` exists, `docs/specs/auth-specs.md` exists. No EARS IDs or LLD section headings were cited in the arrow doc prior to this pass, so nothing to invalidate.

### 2. Coverage
- `auth`: spec **AUTH-001** has no eval assertion citing it — no `tests/` directory, no eval files, no `@spec` annotations exist in the project. The spec is marked `[x]` (implemented) in `docs/specs/auth-specs.md` but nothing substantiates that marker. Surfaced to user (see decisions below).

### 3. Staleness
- `auth`: was previously unaudited (`audited: null`, `audited_sha: null`). First audit completed on this pass, timestamps now set to `2026-04-18` / `efa20068050b7dd75b8eedf5a8cb84d12570f9e2`.

### 4. Drift signals
- No code files, no `@spec` annotations anywhere in the project — no reverse orphans, no code/spec drift detectable. One soft signal: AUTH-001's `[x]` marker is aspirational rather than evidence-backed (same finding as coverage).

### 5. Orphan artifacts
- `docs/llds/auth.md` — referenced from `auth` arrow doc. OK.
- `docs/specs/auth-specs.md` — referenced from `auth` arrow doc. OK.
- `index.yaml`'s `unmapped.docs` was already empty; stays empty.
- No orphan LLDs, specs, or code files found.

### Automatically resolved
- Refreshed `audited` / `audited_sha` on `auth` segment (`index.yaml`).
- Updated `last_updated` in `index.yaml` to today.
- Regenerated the `auth.md` arrow doc's Status / References / Spec Coverage sections from a source scan — this is the derived-view regeneration the audit-checklist specifies.
- Set `next` and `drift` on the `auth` segment in `index.yaml` to reflect the coverage gap (state is unambiguous: exactly one spec, zero eval assertions).

## Findings requiring user decision

1. **AUTH-001 marker vs. reality.** `docs/specs/auth-specs.md` marks AUTH-001 as `[x]` (implemented) but no code, tests, or eval assertions exist. This is effectively a reverse-coverage question: the user should either (a) add the eval + implementation so the marker is honest, (b) demote the marker to `[ ]` (active gap) or `[D]` (deferred) until work begins, or (c) confirm the implementation lives outside this project and link it from the arrow doc's Code / Tests references. I did not auto-downgrade the marker because the right answer depends on intent.

2. **HLD stub.** `docs/high-level-design.md` contains only `# HLD` — no auth section. The arrow doc currently cites it as "(stub — no section for auth yet)". Not an audit failure, but worth flagging: a meaningful HLD reference requires a real section. Decision: expand the HLD, or leave the arrow doc's HLD reference explicitly marked as stub-pending.

No lifecycle events (splits, merges, renames) detected. No ambiguous `unmapped.docs` entries to assign. No reverse orphans (no `@spec` annotations exist in the project at all).
