I ran the `/lid-coach` review. Before the report, one note on the second half of your request.

**On "fix any issues you find":** `/lid-coach` is an advisory, principle-level review. It deliberately does **not** edit project files, and that posture is load-bearing — the findings here are exactly the kind of intent decisions (what the system is, what its components are, what it should do) where silent edits would bypass the review that matters most. So I'm producing the report and pointing you at the right commands to apply the changes, rather than editing the docs myself inside the coach pass. The fastest path for this project is `/linked-intent-dev` with a description of what you're building — see "Applying these findings" at the end.

---

# LID Coach Review

## 1. Executive summary

**Posture:** *Bootstrapping — configuration in place, arrow not yet authored.*

**Scorecard**
- ✓ Configuration — `CLAUDE.md` has the LID directive block and a valid `## LID Mode: Full` marker
- ✓ Directory layout — `docs/`, `docs/llds/`, `docs/specs/` all present and correctly placed
- ✗ HLD content — present but trivial boilerplate; carries no architecture or rationale
- ✗ LLD layer — empty (only `.gitkeep`)
- ✗ EARS layer — empty (only `.gitkeep`)
- ⚠ Arrow walkability — the arrow has a shape but nothing to walk yet

**Headline:** The scaffolding is correct — the mode is declared, the directive block is in place, and the directory structure matches the canonical arrow. That's real work done and it means the project is ready to walk its first arrow. The single most valuable next step is to author a real HLD (what are we actually building, and why), because every downstream phase — LLDs, specs, tests, code — derives from it and right now there is nothing for them to derive from.

## 2. Findings inventory

**Findings (4 total · 3 high · 1 medium)**

- **F1 (high):** HLD is boilerplate ("We are building a thing.") — no problem, approach, users, goals, or design decisions · *HLD is architecture and rationale*
- **F2 (high):** `docs/llds/` is empty — no intent components defined · *one LLD per intent component*
- **F3 (high):** `docs/specs/` is empty — no EARS specs, so the arrow has nothing grep-anchored to walk · *specs are grep-anchored linkage*
- **F4 (medium):** `CLAUDE.md` directive is a one-line stub ("Consult the linked-intent-dev skill.") with no Navigation, Terminology, or Code Annotation guidance · *minimum surface, maximum discipline*

### Finding detail

**F1 — High. The HLD is a placeholder, not a design.** `docs/high-level-design.md` contains only a `## Problem` heading and the sentence "We are building a thing." The principle *HLD is architecture and rationale* says the HLD must carry the *why* — problem, approach, target users, goals and non-goals, key design decisions, success metrics — the architecture-level rationale that outlives any specific implementation. Why this matters: the HLD is the root of the arrow. LLDs decompose it, specs trace up to it, and every future agent session reloads it to understand why the system is shaped the way it is. While it says only "a thing," there is no intent for anything downstream to be coherent *with* — the arrow cannot be walked because it has no origin. Recommended action: author a real HLD via `/linked-intent-dev` with a description of what you're building (its Phase 1 walks HLD authoring as a step), or edit `docs/high-level-design.md` directly to add problem, approach, target users, goals/non-goals, and key design decisions.

**F2 — High. No LLDs exist.** `docs/llds/` holds only `.gitkeep`. The principle *one LLD per intent component* expects one design doc per "thing" a user would name — a feature, subsystem, or service. Why this matters: in Full mode the LLD layer is where the HLD's architecture is decomposed into components an agent can plan a change against. An empty LLD directory is expected at bootstrap and is not itself a defect — but it becomes a true gap the moment there is observed behavior or a real HLD with no component decomposition beneath it. Once F1 produces a real HLD, the components it names each want an LLD. Recommended action: defer until the HLD exists, then author one LLD per intent component the HLD identifies — `/linked-intent-dev` cascades into this from Phase 1.

**F3 — High. No EARS specs exist.** `docs/specs/` holds only `.gitkeep`. The principle *specs are grep-anchored linkage* makes specs the source of truth and the spine the arrow is walked along — an agent finds intent with a single grep on a stable `{FEATURE}-{TYPE}-{NNN}` ID. Why this matters: with no specs there is nothing to write tests against and nothing for `@spec` annotations to point at, so the arrow has no testable, traceable middle. This is expected at bootstrap; it becomes load-bearing as soon as the HLD and LLDs name behavior. Recommended action: author specs as the cascade reaches the EARS phase — downstream of F1 and F2, handled by `/linked-intent-dev`.

**F4 — Medium. The CLAUDE.md directive block is a one-line stub.** `CLAUDE.md` correctly carries `## LID Mode: Full` and a `## Linked-Intent Development` heading, but the body is only "Consult the linked-intent-dev skill." There is no Navigation table (where the HLD / LLDs / specs live), no Terminology, and no Code Annotation convention. The principle *minimum surface, maximum discipline* wants the methodology as thick as the project requires and no thicker — and the bootstrap minimum includes enough in-repo guidance that an agent (or a non-Claude-Code tool reading `CLAUDE.md`) can navigate the arrow without the skill loaded. Why this matters: tools that read `CLAUDE.md` directly (and fresh sessions in any tool) rely on that block to find the arrow; a bare stub leaves them without the map. This is configuration, so the right tool is `/update-lid`, which state-dispatches to reconcile the directive block. Recommended action: run `/update-lid` to flesh out the CLAUDE.md directive block (Navigation, Terminology, Code Annotation sections).

## 3. What was audited

- Read fully: `CLAUDE.md` (5 lines), `docs/high-level-design.md` (5 lines)
- Enumerated: `docs/llds/` (empty — `.gitkeep` only), `docs/specs/` (empty — `.gitkeep` only)
- Overlay: no `docs/arrows/` directory present (arrow-maintenance overlay not installed) — structural enumeration not applicable
- Code/tests: none present in project — `@spec` annotation and tests-first dimensions not applicable at this stage
- Detection signals: LID directive present (`grep` hit on "Linked-Intent Development"); mode marker present and valid (`## LID Mode: Full`); Full mode so no `## LID Scope` expected

## 4. Offer to help

Want me to walk through any finding in more detail, or sketch what a real HLD for this project might cover so you have a starting point? Pick a finding and we can work it through together.

If you have broader questions about using LID for this project — how thick the HLD should be at this stage, when LLDs are worth authoring versus deferring, mode fit, or how the bootstrap cascade flows — I'm happy to talk through those too.

## Applying these findings (since you asked me to fix them)

I have not edited any project files, by design — `/lid-coach` is advisory and these are intent decisions that want your review. To apply:

- **F1 / F2 / F3** are one connected cascade, not three separate edits: run **`/linked-intent-dev`** with a description of what you're actually building. Its Phase 1 bootstraps the HLD, then walks HLD → LLDs → EARS → tests → code with stops between phases. That is the intended path for a fresh project with a change in mind, and it produces F1–F3's content coherently rather than as disconnected files.
- **F4** is a configuration reconciliation: run **`/update-lid`**, which will flesh out the CLAUDE.md directive block (Navigation, Terminology, Code Annotation).

If you'd like, tell me what you're building and I can help you think through the HLD content before you run `/linked-intent-dev` — but I'll leave the actual file authoring to that workflow so the phase gates and your review stay intact.
