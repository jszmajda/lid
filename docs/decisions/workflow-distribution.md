---
node: high-level-design
---

# Decision: How the workflow reaches hosts without a plugin system

## Context

Plugin hosts (Claude Code, Cursor) load the `linked-intent-dev` skill on demand — the full workflow arrives only when a change is in flight. Every other host reads exactly one thing: the project's instruction file. That file is paid for on every turn of every session, and some hosts enforce hard budgets on it (Codex silently truncates combined AGENTS.md content at 32 KiB by default — configurable, but silent). The distribution question: in what form does the full workflow reach instruction-file-only hosts, without taxing every session's context and without maintaining a second, drift-prone copy of the methodology? Evidence base: `docs/research/harness-instruction-idioms.md` (verified survey of the target harnesses' idioms, 2026-07-05).

## Decision Elements

- **Gate — fits the hard budgets.** Whatever lands in the instruction file must sit well inside Codex's combined cap (32 KiB by default) alongside the user's own content; silent truncation is invisible failure.
- **One source, no paraphrase (major).** A hand-maintained summary of the workflow is a drift class: a paraphrase falls behind its source and freezes judgments the source has since revised. Whatever ships must be derived from the skill source, not authored beside it. (*Intent leads*; *docs carry current intent*.)
- **Survives unreliable pointers (major).** Prose "read this file first" pointers are model-dependent on most target harnesses (deterministic imports exist only on Amp and Claude Code), with a documented failure and no systematic reliability evidence. Load-bearing guarantees cannot live solely behind a pointer.
- **Footprint tidiness (moderate).** Communities accept vendored files; they push back on sprawl ("makes it look like the framework is the project"). LID already owns a `docs/` presence — additions should ride it, not add root directories.
- **User choice (moderate).** Minimal-harness users are intentional about their repos and context windows; distribution is offered, not imposed. (*The user is always right — with warning*.)

## Options in the Domain

### Compressed summary in the instruction file (status quo)

A hand-written digest of the workflow inside AGENTS.md; no other artifact.

- Budget gate: **passes** (small).
- One source: **weak** — the summary is a paraphrase, maintained by cascade discipline and historically behind it.
- Pointer resilience: **strong** — nothing depends on a pointer.
- Footprint: **strong** — no files.
- Choice: **weak** — one shape for everyone; instruction-file-only hosts never see the full methodology.

### Full workflow inside the instruction file

Move the entire workflow text into AGENTS.md; no pointer, no second artifact.

- Budget gate: **eliminated** — the full workflow plus user content approaches or exceeds hard caps, and pays full token cost on every turn of every session, including non-change tasks.

### Version-pinned URL pointer

The instruction file points at the canonical workflow doc in the LID repository at a version-pinned URL.

- Budget gate: passes.
- One source: strong.
- Pointer resilience: **weak** — doubly dependent: model compliance plus network availability; fails offline and in restricted environments.
- Footprint: strong.
- Choice: **eliminated in practice** — no surveyed community distributes methodology by URL; the shape matches no host's idiom, and the project no longer contains what its agents follow.

### Vendored generated workflow doc + invariant floor + bootstrap offer (selected)

The plugin ships a workflow doc assembled from the core skill source at release. Bootstrap offers to vendor it (committed, generated-file header, version stamp) into the project's existing `docs/` tree; `/update-lid`'s version-walk re-syncs it. The instruction file carries a compact core — `## LID` block, navigation, arrow mandate, inspection invariant — plus a capability-conditional pointer to the doc. Declining the offer keeps the compressed-summary shape.

- Budget gate: **passes** — the always-loaded core shrinks; the doc is read on demand.
- One source: **strong** — the doc is release-assembled from the skill, never authored separately.
- Pointer resilience: **strong** — the **invariant floor** — the arrow mandate and inspection invariant kept in the instruction file's compact core — stays in place, so an ignored pointer degrades to today's guarantees, not to nothing.
- Footprint: **strong** — one committed file inside `docs/`, no new root directories.
- Choice: **strong** — offered at bootstrap with the tradeoff stated; per-tool deterministic loading (Aider's committed `.aider.conf.yml` `read:` entry, Amp `@`-mention) documented in `docs/setup.md`.

## Selection

The vendored generated doc with invariant floor and bootstrap offer. It is the only option that is strong on both major criteria — the doc is derived, so the paraphrase-drift class closes, and the floor makes pointer failure non-catastrophic — while matching the surveyed communities' own idioms (vendored-but-tidy, committed, token-frugal instruction files, choice at init).

Implications: the release ritual gains an assembly step (the doc is regenerated from the skill source each release); `/update-lid` gains sync and hand-edit detection (a hand-edited generated doc is surfaced, never silently overwritten); `docs/setup.md` reorganizes around the offer plus per-tool loading notes. Instruction-file-only hosts get more methodology than the status quo gave them, at lower always-loaded cost.

Turns on *minimum surface, maximum discipline* and *LID runs on the agent, not a runtime*; the floor enforces *Every phase is inspected* even where pointers fail.
