# `docs/arrows/` — Arrow of Intent Tracking

This directory tracks the arrow of intent across the project — the chain from high-level design through to realized code:

```
HLD → LLDs → EARS → Tests → Code
```

## Files in this directory

- **`index.yaml`** — The dependency graph. Load this first to understand what's available, what's blocked, and what needs work. Schema in `plugins/arrow-maintenance/skills/arrow-maintenance/references/index-schema.md`.
- **`{segment-name}.md`** — One file per arrow segment. Orientation page with References, Spec Coverage, and Key Findings. Template in `plugins/arrow-maintenance/skills/arrow-maintenance/references/arrow-doc-template.md`.
- **`experiments/`** — Reserved subtree for `lid-experimental` plugin artifacts. Each experiment owns a subdirectory (e.g., `experiments/bidirectional-differential/`); audit ignores this subtree.

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
2. For each EARS spec, verify the implementing code with the cited `@spec` annotation (or, in LID-on-LID, the spec-file's `**Implementing artifacts**:` header).
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

1. Rename the arrow-doc filename.
2. Update the `index.yaml` entry key.
3. Walk every cross-reference: `blocks`, `blockedBy`, `merged_into`, `taxonomy`, other arrow docs' References. Update all in the same session.

## Optional: coherence-check script

A reference Node implementation lives at `plugins/arrow-maintenance/skills/arrow-maintenance/references/coherence-check.mjs`. To use it in this project:

1. Copy the script to a location of your choice (e.g., `bin/coherence-check.mjs`).
2. Declare the path in `CLAUDE.md` under `## LID Tooling`:

   ```markdown
   ## LID Tooling

   - **Coherence check**: `bin/coherence-check.mjs`
   ```

3. The `arrow-maintenance` skill reads the declaration during audit and invokes the declared script. Without a declaration, the skill falls back to in-prompt audit.

Equivalent scripts in any language work identically — the script is an opt-in performance accelerator, not a dependency.

## LID-on-LID note

This repository is itself a LID project. The plugins under `plugins/` are written using LID; their specs follow the LID-on-LID **linkage inversion** — `@spec` annotations live in the spec file headers (`**Implementing artifacts**:` lists), not embedded in `SKILL.md` prose, because prompt bodies cannot host annotations without bending runtime behavior. Audit the linkage at the spec-file header level, not by grepping for `@spec` in prompt bodies.
