# `docs/arrows/` — Arrow of Intent Tracking

This directory tracks the arrow of intent across the project — the chain from high-level design through to realized code:

```
HLD → LLDs → EARS → Tests → Code
```

## Files in this directory

- **`index.yaml`** — The dependency graph. Load this first to understand what's available, what's blocked, and what needs work.
- **`{segment-name}.md`** — One file per arrow segment. Orientation page with References, Spec Coverage, and Key Findings.

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

Normal progression: `UNMAPPED → MAPPED → AUDITED → OK`.
