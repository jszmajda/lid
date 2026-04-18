# Brownfield Bootstrap — Detailed Workflow Reference

This reference expands on each phase of the `/map-codebase` workflow. Consult it for detailed guidance on execution.

## Phase numbering

The current six-phase workflow in `SKILL.md` is the canonical phase structure. This reference maps older section numbering to the current phases:

| `SKILL.md` phase | This reference section |
|---|---|
| Phase 1: Sweep (Reconnaissance) | Phase 1 below |
| Phase 2: Seam Identification — Lens Selection | Phase 2a below (step 2a of the old "Creative Clustering") |
| Phase 3: Seam Identification — Slicing Granularity | Phase 2b below (step 2b of the old "Creative Clustering") |
| Phase 4: User Reconciliation | absorbed into Phase 2b and the start of Phase 3 below |
| Phase 5: Artifact Generation | Phases 3, 4, 5 below (per-cluster LLDs, HLD, EARS + arrows) with STOPs between each sub-step |
| Phase 6: Terminal Verification & Flesh-out Prompt | Phase 6 below, extended with an explicit flesh-out prompt as the terminal step |

Cross-reference [SKILL.md](../SKILL.md) for the canonical flow and the Five Critical Rules.

## Before Starting

Warn the user:

> "Mapping this codebase will be very token-intensive. I need to read every file to build an accurate picture — guessing from filenames leads to incorrect arrows. This is the right approach, but I want you to know upfront that it will consume significant resources. Ready to proceed?"

Check prerequisites:
- Is the linked-intent-dev plugin installed? (Needed for LLD templates and EARS syntax)
- Does `docs/` exist? If not, it will be created during the process.
- Is there an existing `docs/arrows/`? If so, this is an incremental mapping, not a fresh bootstrap — adjust accordingly.

---

## Phase 1: Deep Reconnaissance

### Goal
Build a complete, accurate inventory of every file in the codebase. No assumptions. No shortcuts.

### How to Execute

**Launch parallel subagents aggressively.** Split the codebase into directory groups and assign each group to a subagent. Each subagent reads every file in its group and reports back structured findings.

A good split depends on the project, but as a starting point:
- One subagent per top-level directory
- For very large directories (100+ files), split further by subdirectory
- Don't skip test files, config files, scripts, or infrastructure code — these reveal critical architectural decisions

**What each subagent reports per file:**

| Field | What to capture |
|-------|----------------|
| **Purpose** | What does this file do? One sentence. |
| **Exports/Interfaces** | What does it expose to other code? Functions, classes, types, endpoints. |
| **Dependencies** | What does it import or depend on? Both internal (other project files) and external (libraries). |
| **Data shapes** | What data structures does it create, consume, or transform? |
| **Side effects** | Does it write to disk, call external services, modify global state, send messages? |
| **Role** | Where does it fit? Entry point, middleware, utility, model, view, controller, config, test, script, etc. |
| **Observations** | Anything noteworthy: dead code, TODOs, hacks, unusual patterns, clever solutions. |

**Anti-patterns to avoid:**
- DO NOT skip files because they "look like" boilerplate. Read them. Boilerplate files often contain project-specific configuration that reveals architectural decisions.
- DO NOT summarize entire directories as "standard React components" or "typical Express routes." Read each file and report its specific purpose.
- DO NOT assume a file's role from its directory name. A file in `utils/` might be a critical business logic component. A file in `models/` might be a utility.

### Output Format

Compile findings into a structured inventory, organized by directory. This becomes the foundation for Phase 2.

```markdown
## /src/auth/
- `login.ts` — Handles user login via OAuth2 flow. Exports `loginHandler`. Depends on `oauth-client`, `user-store`. Writes session to Redis.
- `permissions.ts` — Role-based access control check. Exports `checkPermission(user, resource)`. Pure function, no side effects.
- ...

## /src/api/
- ...
```

---

## Phase 2: Creative Clustering

### Goal
Help the user see their codebase as a collection of independent functional systems, then choose the decomposition that best captures how the system actually works.

### What Makes a Good Component

An arrow tracks the intent chain (HLD → LLD → EARS → Tests → Code) for one component. For that to be meaningful, each component must be an **independent system that achieves an independent purpose**.

**Good components** look like:
- An authentication system
- A payment processing pipeline
- A notification engine
- A search and indexing service
- A reporting/analytics module
- A user profile management system
- A data transformation pipeline

**Bad components** look like:
- "The frontend" (too broad — what independent systems exist within it?)
- "Things that deploy together" (that's a build artifact, not a functional system)
- "Files the backend team owns" (that's organizational structure)
- "Stuff that changes often" (that's a change pattern, not a purpose)
- "The utils directory" (that's a file location, not a system)
- "Settings reset utility" (too thin — a single script isn't a system)

The test: **can you explain what this component does to a non-technical person in one sentence?** "It's the part that handles user authentication" works. "It's the stuff that gets flashed to the left half" doesn't — that describes a deployment target, not a purpose.

It's not about how much code is in a component. A component with 3 files that implements an independent system (e.g., a scoring algorithm) is a better arrow than a component with 50 files that's just "everything in the /lib directory."

### How to Execute

**Step 2a: Present 3-5 fundamentally different groupings.**

These are NOT variations on one theme. Each grouping represents a different mental model for decomposing the system. Only propose groupings where each cluster represents an independent functional system.

Good lenses for clustering:

| Grouping | Lens | Example clusters |
|----------|------|-----------------|
| **Data flow** | What independent data pipelines exist | "Ingestion pipeline", "Processing engine", "Storage layer", "API surface" |
| **User-facing capability** | What distinct things can users do | "Account management", "Search & discovery", "Checkout & payment", "Notifications" |
| **Domain concept** | What business problems does each part solve | "Users & auth", "Orders & payments", "Inventory", "Reporting" |
| **Behavioral boundary** | What independent sets of rules govern behavior | "Pricing engine", "Access control", "Workflow state machine", "Data validation layer" |

Avoid these lenses — they produce clusters that track artifacts rather than intent:

| Avoid | Why |
|-------|-----|
| Deployment boundary (what ships together) | Groups by build output, not function. A single system may span multiple deployments. |
| Hardware boundary (what runs on which device) | Groups by physical target, not purpose. The same functional system may run on multiple devices. |
| Team ownership (who maintains it) | Groups by org chart, not architecture. Teams change; functional boundaries shouldn't. |
| File proximity (what's in the same directory) | Groups by filesystem layout, not design. Directory structure often reflects history, not intent. |

For each grouping, present:
- **Name and lens**: What mental model does this use?
- **Proposed clusters**: List each cluster with the files/directories it contains
- **Pros**: When is this grouping useful? What does it make clear?
- **Cons**: What does it obscure? What awkward splits does it create?
- **Best for**: What kind of team or workflow does this suit?

**Be creative.** Think about the *functional systems* in this codebase, not its file structure. A codebase might have a "rules engine" that's scattered across 5 directories, or a "notification system" that's only 2 files but functionally independent. The goal is to surface the real architecture, which may not match the directory tree.

**STOP. Present all groupings. User picks one.**

**Step 2b: Offer 2-3 slicing variations within the chosen grouping.**

Once the user picks a grouping approach (e.g., "domain concept"), offer different granularities:

- **Coarse**: 3-4 large clusters (e.g., "Users", "Commerce", "Platform")
- **Medium**: 6-8 clusters (e.g., "Auth", "Profiles", "Orders", "Payments", "Inventory", "Notifications", "Search", "Admin")
- **Fine**: 10+ clusters (splitting further where there's natural separation)

For each slicing, show what files land where and flag any awkward boundary cases (files that could belong to multiple clusters).

**STOP. User picks a slicing.**

---

## Phase 3: Per-Cluster LLDs

### Goal
For each cluster, create a Low-Level Design document that accurately describes the current state of the code.

### How to Execute

**Before writing the first LLD**, read the LLD template reference from the linked-intent-dev skill. Either invoke `/linked-intent-dev:linked-intent-dev` to load the skill into context, or directly read `references/lld-templates.md` from the linked-intent-dev plugin. This ensures you follow the established template structure.

Follow the LLD template structure, adapted for existing code:

```markdown
# [Cluster Name]

**Created**: YYYY-MM-DD
**Status**: Mapped from existing code
**Source**: Brownfield bootstrap via /map-codebase

## Context and Current State

Why this code exists and what problem it currently solves.
How it fits into the broader system (reference the inventory from Phase 1).

## [Major Section 1]

Technical details of how this subsystem works today...

## [Major Section 2]

Technical details...

## Observed Design Decisions

For each significant design choice visible in the code, record what was chosen
and why it appears to have been chosen (based on code evidence, comments, commit
messages, or reasonable inference).

| Decision | What was chosen | Evidence | Likely rationale |
|----------|----------------|----------|-----------------|
| (decision point) | (approach in code) | (where you see it) | (why this was probably chosen) |

## Technical Debt & Inconsistencies

Things that look like they should be fixed or that contradict the apparent design:
1. Description (file:line references)
2. Description

## Behavioral Quirks

Undocumented behaviors that look intentional — things a developer should know
about that aren't obvious from the code structure:
1. Description (file:line references)
2. Description

## Open Questions

Things you couldn't determine from code alone — questions for the team:
1. Question
2. Question

## References

- Files in this cluster: list all
- Dependencies on other clusters: list with direction
- External dependencies: list libraries/services
```

### Key Principles

- **Describe what IS, not what SHOULD BE.** If the code is messy, say so. Don't clean it up in the document.
- **Use file:line references.** Every claim about the code should be traceable to a specific location.
- **Flag uncertainty.** If you're not sure why something was done a certain way, say "appears to" or "likely because" — don't state inferences as facts.
- **Be thorough.** Each LLD should be complete enough that someone unfamiliar with the code could understand how this subsystem works by reading only the LLD and the referenced files.

**STOP after each LLD. User reviews. Incorporate feedback before proceeding to the next cluster.**

---

## Phase 4: Synthesize HLD

### Goal
Write a High-Level Design that emerges from the LLDs, describing the system as a whole.

### How to Execute

The HLD should cover:

- **System purpose**: What does this system do? (One paragraph)
- **Architecture overview**: How do the clusters relate to each other? Include a data flow or dependency diagram (ASCII).
- **Cross-cutting concerns**: Patterns that span multiple clusters (auth, logging, error handling, data access)
- **Shared infrastructure**: Databases, message queues, caches, external services
- **Key architectural decisions**: The big choices that shaped the system, synthesized from the per-cluster "Observed Design Decisions"
- **Non-goals**: What this system explicitly does NOT do (inferred from its boundaries)

Place at `docs/high-level-design.md`.

**STOP. User reviews.**

---

## Phase 5: EARS Linkages & Arrow Docs

### Goal
Create the formal traceability chain: specs → code → tests → arrow docs → index.

### How to Execute

**Step 5a: Write EARS specs per cluster.**

For each cluster, create a spec file in `docs/specs/`. **Before writing the first spec file**, read the EARS syntax reference from the linked-intent-dev skill (`references/ears-syntax.md` in the linked-intent-dev plugin).

Brownfield-specific guidance:
- Most specs will be `[x]` (implemented) — the code already exists
- Mark things that are broken or incomplete as `[ ]` (active gap)
- Mark things the team explicitly doesn't want yet as `[D]` (deferred)
- Use the cluster name as the spec ID prefix (e.g., `AUTH-CORE-001`)
- Write specs that describe what the code DOES, not what it SHOULD do

**Step 5b: Add `@spec` annotations to code.**

For each spec, add `// @spec ID` comments to the implementing code and test files. This creates the traceability link.

**Step 5c: Create arrow docs.**

For each cluster, create `docs/arrows/{cluster-name}.md` using the arrow-doc-template from the arrow-maintenance skill. Populate:
- References: link to the LLD, spec file, test files, and code directories
- EARS Coverage table: summarize spec counts and status
- Key Findings: the most important things discovered during mapping
- Work Required: technical debt and gaps identified in the LLD

**Step 5d: Create `docs/arrows/index.yaml`.**

```yaml
schema_version: 1
last_updated: YYYY-MM-DD

arrows:
  cluster-name:
    status: AUDITED  # or MAPPED if specs weren't verified against code
    sampled: YYYY-MM-DD
    audited: YYYY-MM-DD  # null if only MAPPED
    blocks: []
    blockedBy: []
    detail: cluster-name.md
    next: "next action description"
    drift: null  # or description of known divergence
```

---

## After Mapping

Once the bootstrap is complete:

1. Run `/linked-intent-dev:lid-setup` if not already done, to ensure CLAUDE.md has the standard LID directives.
2. Verify the arrow index is accurate: read `docs/arrows/index.yaml` and spot-check a few arrow docs.
3. The project is now ready for normal linked-intent-dev + arrow-maintenance workflow. New features get arrows. Bug fixes check arrow coherence first.
