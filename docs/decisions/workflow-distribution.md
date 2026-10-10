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
- **Stays on the upgrade path (major).** A vendored copy pins its project to the release that wrote it until someone re-syncs it, while plugin hosts pick up each release as it ships. Every project vendored without needing the doc is a project that silently stops receiving LID's improvements.
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

### Vendored doc offered at bootstrap

The plugin ships a workflow doc assembled from the core skill source at release, and bootstrap offers every project to vendor it; declining keeps a compressed summary in the instruction file.

- Budget gate: passes.
- One source: moderate — two instruction-file shapes (with and without the doc) to keep in step.
- Pointer resilience: strong (the invariant floor stays in the instruction file).
- Upgrade path: **weak** — bootstrap runs on plugin hosts, where the doc adds nothing, so most vendored copies pin projects that never needed them.
- Choice: strong, but asked of users with no stake in the answer.

### Vendored generated workflow doc + invariant floor + on-demand offer (selected)

The plugin ships a workflow doc assembled from the core skill source at release. Every project's instruction file carries a compact core — `## LID` block, navigation, arrow mandate, inspection invariant — plus one conditional line: a harness without the `linked-intent-dev` skill reads `docs/lid/workflow.md`, and when the doc is absent offers to vendor it (committed, generated-file header, version stamp), fetched from the LID release matching the project's recorded version. A decline is recorded in the `## LID` block so the offer is made once. `/update-lid`'s version-walk re-syncs a vendored doc.

- Budget gate: **passes** — the always-loaded core is the smallest of the options; the doc is read on demand.
- One source: **strong** — the doc is release-assembled from the skill, and every project's instruction file has the same shape: the compact core with the workflow in one line, no separate summary variant.
- Pointer resilience: **strong** — the **invariant floor** — the arrow mandate and inspection invariant in the compact core — stays in place, so an ignored pointer, or a declined offer, degrades to those guarantees, not to nothing.
- Upgrade path: **strong** — only projects a harness without plugins works in are vendored; projects on plugin hosts follow the plugin's releases.
- Footprint: **strong** — one committed file inside `docs/`, only where needed.
- Choice: **strong** — the offer reaches the user whose harness needs the doc, with the tradeoff stated; per-tool deterministic loading (Aider's committed `.aider.conf.yml` `read:` entry, Amp `@`-mention) documented in `docs/setup.md`.

## Selection

The vendored generated doc with invariant floor, offered on demand. It is the only option strong on all three major criteria: the doc is derived, so the paraphrase-drift class closes; the floor makes pointer failure, or a declined offer, non-catastrophic; and vendoring happens only where a harness needs it, so projects on plugin hosts stay on the release path.

Implications: the release ritual gains an assembly step (the doc is regenerated from the skill source each release); the instruction file has one shape for every project; `/update-lid` re-syncs an existing doc and detects hand-edits (surfaced, never silently overwritten), but makes no offer of its own; `docs/setup.md` reorganizes around the on-demand offer plus per-tool loading notes.

Turns on *minimum surface, maximum discipline* and *LID runs on the agent, not a runtime*; the floor enforces *Every phase is inspected* even where pointers fail.
