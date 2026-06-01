# `docs/arrows/` — Arrow of Intent Tracking

This directory tracks the arrow of intent across the project — the chain from high-level design through to realized code:

```
HLD → LLDs → EARS → Tests → Code
```

Copy this template into your project's `docs/arrows/README.md` when the overlay is installed (either via `/arrow-maintenance` or `/map-codebase`). Projects may edit it to reflect their own conventions.

---

## Files in this directory

- **`index.yaml`** — The design tree and dependency graph. Load this first to understand what's available, what's blocked, and what needs work. Where the tree nests, `parent`/`children` links let you walk a subtree rather than scanning the flat list. Schema in `plugins/arrow-maintenance/skills/arrow-maintenance/references/index-schema.md`.
- **`{segment-name}.md`** — One file per arrow segment (leaf node). Orientation page with References, Spec Coverage, and Key Findings. Template in `plugins/arrow-maintenance/skills/arrow-maintenance/references/arrow-doc-template.md`.

## Starting a session

1. Load `index.yaml`.
2. Query for unblocked segments: `yq '.arrows | to_entries | .[] | select(.value.blockedBy | length == 0) | .key' index.yaml`.
3. Load the relevant `{segment-name}.md`.
4. Follow its References to the LLD, spec file, tests, or code.

## Status enum

| Status | Meaning |
|---|---|
| UNMAPPED | Not yet explored |
| MAPPED | Structure known, specs not verified against code |
| AUDITED | Specs verified — implementation status understood |
| OK | Fully coherent — all specs implemented |
| PARTIAL | Some specs missing or partial |
| BROKEN | Code and docs have diverged significantly |
| STALE | Docs exist but outdated |
| OBSOLETE | Superseded, kept for historical reference |
| MERGED | Combined into another arrow (see `merged_into`) |

Normal progression: `UNMAPPED → MAPPED → AUDITED → OK`. `AUDITED` means "we know the state"; `OK` means "it's fixed."

## Common workflows

### Auditing a segment

1. Read the segment's arrow doc references.
2. For each EARS spec, verify the implementing code with the cited `@spec` annotation.
3. Update arrow doc coverage table and any "Key Findings."
4. Refresh `status`, `audited`, `audited_sha`, `next`, and `drift` in `index.yaml`.

### Mapping a new segment

1. Explore the code and docs for the domain.
2. Create `docs/arrows/{name}.md` from the arrow-doc template.
3. Add an entry to `index.yaml` under `arrows:`.
4. Remove from `unmapped.docs` if listed.

### Splitting a segment

1. Create the new segment's arrow doc.
2. Move relevant references from the original to the new one.
3. Update both docs to reference each other.
4. Update `index.yaml` — add the new segment, adjust the original.

### Merging segments

1. Pick the primary.
2. Move references from secondary to primary.
3. Mark secondary in `index.yaml` with `status: MERGED` and `merged_into: {primary-name}`.
4. Tombstone the secondary's arrow doc (or delete if preferred).

### Renaming a segment

A leaf segment's name is the leaf prefix of its path-concatenated EARS IDs, so a rename is a tooled, atomic operation — not just a file move.

1. Rewrite every EARS ID under the segment (e.g., `AUTH-UI-001` → `IDENTITY-UI-001`) in the spec files.
2. Rewrite every `@spec` annotation in code and tests that cites those IDs.
3. Rename the arrow-doc filename.
4. Update the `index.yaml` entry key.
5. Walk every cross-reference: `parent`/`children` links, `blocks`, `blockedBy`, `merged_into`, `taxonomy`, other arrow docs' References. Update all in the same session — all of the above land together or not at all.

### Re-parenting a subtree

Moving a node to a new parent changes the tree path, so it rewrites the moved subtree's path-concatenated IDs. Like rename, it is atomic.

1. Rewrite the path-concatenated EARS IDs of every spec in the moved subtree (e.g., `PEVAL-RUN-014` → `ORCH-RUN-014`) in the spec files.
2. Rewrite every `@spec` annotation in code and tests citing those IDs.
3. Update `parent`/`children` links in `index.yaml` for the moved node and both the old and new parents.
4. Update any cross-references (`blocks`, `blockedBy`, `taxonomy`, other docs' References) in the same session.

## Optional: coherence-check script

A reference Node implementation lives at `plugins/arrow-maintenance/skills/arrow-maintenance/references/coherence-check.mjs`. To use it in a project:

1. Copy the script to a location of your choice (e.g., `bin/coherence-check.mjs`, `scripts/check-coherence.py`, or wherever fits your project's conventions).
2. Declare the path in `CLAUDE.md` under `## LID Tooling`:

   ```markdown
   ## LID Tooling

   - **Coherence check**: `bin/coherence-check.mjs`
   ```

3. The `arrow-maintenance` skill reads the declaration during audit and invokes the declared script. Without a declaration (or with a declared path that does not resolve), the skill falls back to in-prompt audit.

Equivalent scripts in Python, bash, Ruby, Go, or any other language work identically — the script is an opt-in performance accelerator, not a dependency. The skill treats the declaration as authoritative for the deterministic checks (reference coherence, orphan and reverse-orphan detection, coverage counts).
