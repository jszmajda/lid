# The other SDD systems (snapshot)

**Snapshot date: 2026-11-11.** These systems release often, some every few days, so check any fact here again before relying on it for a decision. Facts come from each project's own README, docs, and release notes, read as raw text through the GitHub API, unless marked otherwise. Star counts and release dates come from the GitHub API on the snapshot date.

The column that matters most for this research is the third one: when someone changes the system months after it was built, where does the agent find the intent it needs?

| System | Version and activity | Where intent lives between changes | Runs headless? | Where it expects a person |
|---|---|---|---|---|
| OpenSpec | v2.0.0, released on the snapshot date; about 75k stars | Living capability specs in `openspec/specs/`, plus an archive of per-change folders | Yes. The CLI never calls a model, and the work is done by skills | Reviewing the proposal and specs before applying them; no hard gates |
| GitHub Spec Kit | v1.4.0 (2026-11-10); releases every 1 to 3 days; about 149k stars | The team chooses one of four models; none is the default | Yes, through `specify workflow run`, with approval verdicts passed as inputs | A review after each command; workflow gates after the spec and after the plan |
| BMAD Method | Stable v6.12.4 (2026-10-14); version 7 alpha on main, due mid-November 2026; about 55k stars | Living PRD, architecture, and UX documents with `.memlog.md` change logs, plus per-story plans | Partly. Planning skills have a headless mode, and `bmad-build-auto` runs unattended | Persona conversations, elicitation menus, and checkpoints at plan and at done |
| Kiro | CLI 3.2.1 and IDE 1.4.154 (2026-11-10 and 11) | One spec folder per feature in `.kiro/specs/`, refined in place, plus steering files | The CLI has a non-interactive mode that needs a paid API key. Whether specs can be driven headless isn't documented | A review after each phase, except Quick Spec, which has no gates |
| cc-sdd | v3.1.0 (2026-09-23); about 3.8k stars | Kiro-compatible spec folders with EARS requirements; a discovery step can extend an existing spec | Partly. `/kiro-impl` runs autonomously | Phase gates on requirements, design, and tasks |
| Superpowers | v7.0.2 (2026-11-03); about 316k stars | Dated design docs and plans, one per change; no living spec | Partly. Brainstorming is interactive | Sign-off on the design and the plan, then "go" |
| Agent OS | v3.0.0 (2026-01-20); last commit 2026-10-07 | Standards and product docs persist; specs are per-change folders written through plan mode | No. It asks questions interactively | Approving the plan |
| Tessl | The platform has moved toward a skills registry; its SDD tile is at v2.0.1, and its spec-as-source framework was still in closed beta | Tile: `specs/*.spec.md` files that point to their target files and tests | Through any agent that loads skills | Approval before implementation |
| Task Master | 0.43.1 (2026-03-31); last commit 2026-04-23; its makers have moved to a commercial product | A PRD parsed into `tasks.json` | CLI and MCP server | Not checked |
| GSD | Moved to `open-gsd/gsd-core`, v1.20.1 (2026-11-05) | `STATE.md` and `CONTEXT.md` persist; each phase is archived | Through several runtimes | Discuss, plan, execute, verify, and ship phases |

## How each system handles a change after the first build

- **OpenSpec.** Each change gets a folder holding a proposal, delta specs (requirements marked as added, modified, or removed), a design, and tasks. Requirements use SHALL or MUST wording with GIVEN/WHEN/THEN scenarios, not EARS. When a change is archived, its delta specs merge into the living capability specs, and the folder moves to a dated archive. A later change reads the living spec. The design rationale survives only in the archive and is never merged into a living document. OpenSpec describes itself as built for existing codebases first.
- **Spec Kit.** It leaves the choice open on purpose. Its persistence guide describes four models and says none is the default:
  - Flow-back: any artifact may be updated, and the team reconciles them.
  - Flow-forward: completed feature folders are never changed, and each change gets a new folder.
  - Living spec: `spec.md` is the contract, and the plan and tasks are regenerated from it.
  - Constitution-only: feature artifacts are retired after delivery. Spec Kit's own repository works this way.

  Its docs also say the core has no command that reconciles differences among `spec.md`, `plan.md`, and `tasks.md` automatically.
- **BMAD.** Its PRD skill has an update mode that logs every change and reports conflicts with earlier decisions. A course-correction skill assesses the impact of a change across the PRD, epics, architecture, and UX documents. BMAD's own docs argue for writing down "intent, rationale, and what was deliberately rejected" rather than what the code already says.
- **Kiro.** Feature specs are meant to be refined continuously. A person edits the requirements and design, then syncs the task list. A later change pulls an earlier spec into context explicitly. Source: Kiro's docs, read through a fetch tool's summary.
- **cc-sdd.** A discovery command routes each request: extend an existing spec, make a new spec, split the work, or use no spec. Its README says that "code remains the source of truth."
- **Superpowers.** Every change gets its own dated design and plan, and nothing is kept as a living spec. Version 7 decides how much process a request needs: it does a quick task directly, agrees a small change in chat, or writes a design doc for larger work.

## The configuration chosen for each arm

| System | Configuration | Why |
|---|---|---|
| Spec Kit | Living-spec model | It is closest to LID's spec-anchored design, where the spec stays the contract for later changes. Flow-back is the alternative if Spec Kit's maintainers prefer it. |
| OpenSpec | Default profile at v2.x | It is the documented default, and it keeps living specs. |
| cc-sdd | Default flow | It stands in for Kiro's plan-plus-EARS approach without our having to build an imitation of Kiro. |
| BMAD | Deferred until version 7 is stable | Comparing against version 6 just before version 7 ships would date the result immediately. |
| Kiro | Not included | It runs only in its own harness and needs a paid key, so a Kiro arm would measure the product rather than the method. |

## Notes for the eval

- **OpenSpec 2.0 replaced its commands.** It shipped on the snapshot date and replaced its `/opsx:*` commands with skills. Older tutorials won't match it.
- **BMAD's timing.** BMAD version 7 changes the install path to a skills CLI and plugins, and it was due in mid-November 2026.
- **How each system handles a person differs the most.** That is the biggest fairness question. Spec Kit takes approval verdicts as inputs. BMAD's headless mode returns its open questions as data. OpenSpec has no gates. Superpowers and Agent OS ask questions interactively. Each arm's configuration says how its human touchpoints map to the user simulator.
