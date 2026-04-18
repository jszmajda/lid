# Audit Checklist

Run these five checks every time you audit — whether as part of a `/arrow-maintenance` command run or when the ambient skill notices something worth surfacing. When a project-local coherence script is declared under `## LID Tooling` in `CLAUDE.md`, invoke it for the deterministic checks and treat its output as authoritative; otherwise perform in-prompt.

**Incremental mode.** When `audited_sha` is populated for a segment and git history is available, the discovery step (which segments need re-auditing this run) is *project-wide*: `git diff --name-only {min(audited_sha across segments)} HEAD` → map each changed file to its segment via arrow docs' References — only audit those segments. The per-check scoping below applies *within* each segment selected for audit; it does not replace the top-level incremental discovery.

## 1. Reference coherence

For each per-segment arrow doc, verify:

- Every file path in `## References` (HLD section, LLD, EARS spec file, tests, code) resolves to an existing file.
- Every EARS spec ID cited in the arrow doc exists in the referenced spec file.
- Every LLD section heading referenced in the arrow doc appears in the LLD.

**Finding format**: `{segment}: reference rot — {path} (cited in {arrow-doc-line}) no longer exists`.

## 2. Coverage

For each behavioral EARS spec in the project, verify at least one eval assertion cites the spec ID (via `spec_ids` in the eval's assertions array).

**Finding format**: `{segment}: spec {ID} has no eval assertion citing it`.

Scope: only behavioral-skill specs. Pure-prose skills have no eval coverage by design.

## 3. Staleness

For each segment with `status` in `{MAPPED, PARTIAL, BROKEN}`:

- Compare `audited` date against today.
- When `audited_sha` is populated and git history is available, list files modified since `audited_sha` in the segment's territory.

**Finding format**: `{segment}: last audited {date} ({N} days ago), {M} files modified since audit`.

Scope: not a failure — a signal. `OK` and `OBSOLETE` segments are not flagged for staleness.

## 4. Drift signals

Scan across the project:

- Code files modified since `audited_sha` in segments not marked `OK` and not currently in active work (no pending PR / uncommitted changes).
- EARS specs whose text was revised but whose cited tests have not been touched in the same commit range.
- Tests that pass but have no `@spec` annotation, suggesting the behavior is tested but unlinked to intent.
- **Reverse orphans** — `@spec` annotations in code or tests that reference spec IDs not present in any spec file. These are *asks*, not fixes: surface for user decision (create the spec, delete the annotation, or treat as alias of an existing spec). Do not auto-resolve.

**Finding format**: `{segment}: drift signal — {description} ({location})`.

## 5. Orphan artifacts

Enumerate:

- LLD files in `docs/llds/` not listed as `detail` or referenced from any arrow doc's `## References`.
- Spec files in `docs/specs/` not referenced from any arrow doc.
- Code files containing `@spec` annotations but not in any arrow doc's `## References`.
- Entries in `index.yaml`'s `unmapped.docs` list — these are the trackable orphans; bulk-assign where clear, flag where ambiguous.

**Finding format**: `orphan: {path} — not referenced from any arrow segment`.

## After the checks

In command mode (`/arrow-maintenance`):

- Apply unambiguous fixes in place (regenerate coverage tables, refresh `audited`/`audited_sha`, clean assignable `unmapped.docs` entries, update status transitions where clear).
- Produce a structured report: findings resolved, findings requiring user decision.
- The report distinguishes the two categories and lists each finding with its location.

In ambient mode: surface findings as a report, do not modify files (except opportunistically in changes the surrounding conversation is already performing).
