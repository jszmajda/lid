# LID — Common adoption patterns and questions

A load-on-demand knowledge layer for the `lid-coach` skill. When the user asks how to use LID for a specific situation, draw on these framings and answer in your own voice — don't lecture from the file. The aim is to give the user the *shape* of a good answer; specific tools and filesystem layouts are theirs to decide.

The patterns below are the ones that have come up most often. If a question doesn't fit any of them, reason from LID's principles (in the SKILL.md body) and from the project under discussion. When you're genuinely unsure, say so and think through the specifics with the user.

---

## Which command do I run? `/linked-intent-dev` vs `/map-codebase` vs `/update-lid`

**The question.** "I'm starting LID on a new project / on an existing codebase / on a brownfield mess. Which command do I run?"

**The shape that works.** Three commands, three situations:

- **Greenfield** (fresh project, you want to start building something): run **`/linked-intent-dev`** with a description of what you want to build. The workflow's Phase 1 bootstraps LID configuration as a sub-step (creates `docs/`, adds CLAUDE.md directives, prompts for mode) and then walks the change forward through HLD → LLD → EARS → Tests → Code. The user invokes the workflow; setup happens as part of getting to Phase 1.

- **Brownfield, small or familiar**: run **`/linked-intent-dev`** and describe the first feature/change you want to make on the existing code. The workflow handles bootstrap as part of Phase 1 the same way, and you author the HLD and LLDs by hand as you go. Lower token cost than `/map-codebase`, and your familiarity with the system usually beats the agent's reverse-engineering — the rationale-and-intent layer lives in your head, and no reconnaissance pass will recover it.

- **Brownfield, large or unfamiliar**: run **`/map-codebase`**. The agent does the inventory and lens-based clustering, walks you through reconciliation, and produces skeleton HLD/LLDs/EARS that you flesh out. This is the right tool when the codebase is too big to hold in your head or when you've inherited code without inheriting the intent. `/map-codebase` calls `/update-lid`'s bootstrap branch at its terminal step, so LID configuration is handled.

- **Brownfield, you want skeleton docs to start from even though you know the system**: `/map-codebase` is still a legitimate choice. It costs tokens but gives you a starting point that's faster than writing from scratch. Treat the skeletons as drafts.

- **Already LID-configured and needing reconciliation**: run **`/update-lid`** to fix drift, refresh the CLAUDE.md template, change modes, or migrate scope. The skill state-dispatches; on a configured project it reconciles. (On an unconfigured one it bootstraps — same command — but greenfield users typically reach for `/linked-intent-dev` because they want the workflow, not just the directories.)

**Other commands on an already-LID-configured project:** **`/arrow-maintenance`** for structural drift (orphans, reverse orphans, adjacent-level coherence) and **`/lid-coach`** for principle-level review. `/map-codebase` is rarely the right tool on an already-configured project unless a large new chunk of un-mapped code has appeared.

**The minimum question to ask the user.** "Are you starting a code change, mapping existing code, or just updating LID config?" The answer points at one of the three commands above.

---

## Multi-repo projects with shared intent

**The question.** "My project lives in several separate git repos that share intent — a frontend, a backend, a shared library, maybe infra. How should I organize LID across them?"

**The shape that works.** A **container repo** holds the cross-repo intent (system-level HLD, per-component LLDs at the system level, maybe shared scripts). The sub-repos are cloned as children of the container directory and gitignored from it. Each sub-repo remains a normal independent git repo with its own complete arrow inside it. Sketch:

```
my-system/                              # container repo: holds cross-repo intent
├── CLAUDE.md                           # LID directives for the system
├── docs/
│   ├── high-level-design.md            # system-level HLD
│   └── intent/{frontend,backend,…}.md    # how each sub-repo fits the system
├── bin/setup                           # convenience: clones the sub-repos
├── .gitignore                          # ignores frontend/ backend/ shared/
└── (sub-repos cloned as siblings)
    frontend/                           # its own git repo with its own arrow
    backend/
    shared/
```

Each sub-repo's HLD carries a one-line upstream pointer back to the container's HLD ("this is the frontend of *my-system*; see ../docs/high-level-design.md"). The container's LLDs describe how each sub-repo fits the larger system; the sub-repo's own arrow handles the component's internals. The agent works from the container directory and reads/writes files across sub-repos as ordinary subdirectories. Commits happen per-repo as normal.

**Why not git submodules.** Submodules pin a sub-repo at a specific commit SHA in the superproject, which creates three failure modes that hurt LID specifically: (1) detached-HEAD by default — easy to commit to nothing and lose work; (2) two-step commit dance — update a submodule, then commit the pointer-SHA bump in the superproject, and forgetting the second step silently rots the superproject's view of the submodule; (3) `.gitmodules`, the superproject's pointer SHA, and the submodule's actual HEAD all drift independently. From a LID perspective the superproject pointer SHA is *exactly* the historical-narration pattern *docs carry current intent* flags — every superproject commit captures "submodule X was at SHA Y on this date," which is history pinned in the doc tree rather than in each repo's own log.

**Tooling.** Plenty of multi-repo orchestration tools exist if a hand-written `bin/setup` (a list of repos plus a clone loop) gets unwieldy. LID has no opinion on which to use; pick whatever fits the team. The pattern doesn't depend on tooling — it's a shape, not a tool stack.

**When to consider monorepo migration instead.** If the team owns all the repos, releases them together, and reviews them as a unit, a true monorepo (one repo with subdirectories) often beats the container pattern — LID then runs as in any single-repo project. Multi-repo earns its complexity when teams, release cadences, or access controls actually differ across the components.

---

## PRDs and product-requirement docs

**The question.** "Where do product requirements fit in LID? My PM writes PRDs, and I want them to be part of the arrow somehow."

**The shape that works.** PRDs naturally extend the arrow **upstream of the HLD**. Where the HLD covers *how we'll solve the problem*, a PRD covers *what the problem is and what success looks like from the user's perspective*. When a PRD is present, the arrow becomes `PRD → HLD → LLDs → EARS → Tests → Code`. The PRD's claims feed the HLD's Problem and Approach sections; HLD decisions trace back to PRD goals.

**Location.** LID doesn't prescribe one. A single `docs/product/` doc, per-feature PRDs each referenced from the HLD, a `PRD.md` at the root — all fine. The CLAUDE.md / AGENTS.md should note where they live so the agent reads them.

**Working with the PM.** The most useful adoption pattern is to **pair the engineer lead and the PM on both the PRD and the HLD**. The PRD is the PM's primary artifact, the HLD is the engineer's, and the two need to stay coherent for the arrow to walk all the way up. Pair-writing is faster than ping-ponging drafts.

**Coach behavior.** The coach treats the PRD (when present) as the upstream-most layer for intent-tree alignment. A PRD claim that doesn't flow into the HLD is an intent gap at the top of the arrow — worth surfacing as a finding.

---

## Mode fit — when to switch Full ↔ Scoped

**The question.** "I started in Scoped mode and the LID-covered area has grown — should I switch to Full?" / "I'm in Full mode but only one subsystem is really active in LID — should I scope down?"

**The shape that works.** Cues that a Scoped project should consider Full:

- The scope list in `## LID Scope` covers most of the repo.
- Out-of-scope areas are accumulating arrow artifacts anyway (LLDs, specs) without being declared in scope.
- The team is doing LID-style cascade across the whole repo regardless of the marker.

Cues that a Full project should consider Scoped:

- Most LLDs and specs are concentrated in one subsystem; the rest of the repo is visibly non-LID.
- The Full-mode rigor is producing nag-level friction for areas no one actually treats as LID.
- A new contributor would be confused by the gap between the directives and what the repo actually does.

**Mechanics.** `/update-lid` handles the transition in both directions. Scoped → Full migrates arrow artifacts from scope-local paths to the standard Full positions (the skill walks overlaps with the user). Full → Scoped is a mode-marker change plus an explicit scope declaration; arrows stay where they are.

**Coach behavior.** Mode-fit is a review dimension. The coach surfaces a recommendation when the cues above point one way clearly, but treats the declared mode as authoritative unless the gap is significant.

---

## Upstream ownership — "this feels uncomfortable"

**The question.** "Adopting LID feels like letting go of the code. I used to know my system because I'd written every line; now the agent writes most of it and I feel less in control."

**The shape of a useful answer.** The discomfort is the cue that **ownership is moving upstream**. In pre-agentic coding, developers implicitly tracked intent in the code itself — the code was both the artifact of attention and the artifact of work. With agentic coding, the agent produces the code, and the developer's attention has to attach somewhere — the natural place is upstream, at the spec layer. LID is the scaffolding that makes the new location legible.

What this means in practice: the developer's job is to write the specs, review them, and ensure the arrow stays coherent. The code is compiled output of the specs — important, reviewable, but no longer the artifact where intent lives. The discomfort that comes from "letting go of code details" is usually a misread of what's happening: you're not losing track of your system, you're moving where the system is *expressed*. Once that shift settles, the discomfort tends to subside — developers find they can reason about more of the system at a higher level than they ever could when intent lived only in the code.

This isn't a behavior to enforce; it's a reframe to offer when the discomfort comes up. The coach can name it; the user adopts (or doesn't) at their own pace.

---

## Splitting an arrow segment that grew too large

**The question.** "One of my LLDs has become a sprawl — it covers too much, the specs under it have lost focus, and I'm not sure how to break it up."

**The shape that works.** Splitting an arrow segment is a **lifecycle event** (the same family as merging or renaming). The mechanics:

1. **Identify the natural seam.** A segment that's too big almost always contains two intent components that share a prefix by accident. Find where the seam is — what behaviors group together naturally, what specs cluster around different surfaces.
2. **Create the new LLD.** Move the relevant content from the original to the new file. Update Decisions & Alternatives and Open Questions per-segment.
3. **Move or re-prefix specs.** Specs that move to the new segment get a new `{FEATURE}` prefix. **IDs do not move** — when you re-prefix, the old IDs are deleted and new IDs are issued for the new segment. (Spec ID stability is per-segment; renaming the prefix is a write of a different spec.) Walk references across code, tests, and other docs.
4. **Update cross-references.** The original LLD references the new one for the split-out behaviors; the new LLD references the original for the parent context.
5. **If the project uses arrow-maintenance,** record the split in `index.yaml` (the new segment gets its own entry; both segments reference each other in their detail docs).

**When to defer.** If the segment is in the middle of an active change, don't split mid-edit. Get to a clean cascade boundary first, then split. Splits done during ongoing work tend to leave half-migrated specs and broken references.

**Coach behavior.** A finding that an LLD has grown to cover multiple intent components is a granularity-dimension finding — surface the seam you notice and recommend a split rather than attempting the split inside the coach run (the coach is advisory; lifecycle events are user-driven).

---

## Validating a cascade with a cold-read subagent

**The question.** "I just made a cascading change — renamed a skill, restructured a section, updated several specs and their downstream artifacts. How do I know I haven't missed anything? Stale references, leftover terminology, broken cross-references?"

**The shape that works.** **Spawn a context-free subagent and have it review the cascade.** The agent that made the changes has the conversation context — it knows what the new design is *supposed* to look like, which is exactly what makes it bad at spotting where the new design didn't land. A subagent invoked fresh, with no chat history, reads the files as they actually are and is well-positioned to catch leftovers a future session would also have stumbled over.

This is the same principle as the coach's cold-read pass (*docs carry current intent, written to be read cold*), applied to the implementation layer rather than the doc-review layer. The subagent IS the future session that has to read the cascade cold; if it can read it without getting confused, the cascade is coherent.

**How to brief the subagent.**

- **Tell it what changed.** Give it a summary of the cascade: what was renamed, what was added, what was removed. The subagent needs enough context to know *what to look for* without inheriting your conversation context. Be explicit about which old-name mentions are intentional retrospective callouts (in Decisions tables, eval assertions verifying the agent doesn't recommend retired commands) so it doesn't flag them.
- **Ask it to look broadly.** Beyond the specific changes, ask it to flag *anything* that smells vestigial or inconsistent. The subagent often catches things you didn't anticipate — that's the value of a fresh context.
- **Scope it.** Name the directories to audit and the directories to skip (e.g., historical eval-output snapshots under `workspace/iteration-*/`, legacy `docs/planning/` if present).
- **Structured report, no fixes.** Ask for findings grouped by category (rename leftovers, terminology stragglers, broken cross-references, LLD/SKILL.md misalignments, spec-coverage mismatches, other) with file paths and line numbers. Do not let the subagent edit — its job is to find, yours is to triage.

**When to reach for this.**

- After a multi-file rename or refactor where ≥3 files are affected.
- After a cascade that propagates an HLD change downward through LLD → specs → SKILL.md → evals → arrow docs.
- Before declaring substantial work "complete" — equivalent to asking a colleague to look at your PR before merging.
- When you notice a single straggler and suspect there might be others — finding one inconsistency often means there's a cluster.

**Cost note.** Subagents consume tokens; this isn't a routine move for every small change. Reserve it for substantive cascades where the cost of a missed straggler is high — when the cascade touches user-facing names, public command names, or load-bearing terminology.
