# LID Coach Review

## Executive summary

**Posture: Bootstrapping — scope misconfigured, content not yet authored.**

You've made the right opening moves: the project is LID-configured, the mode is declared explicitly rather than left to default, and the standard directory skeleton is in place. The single most valuable next step is fixing the Scoped-mode configuration so the methodology has a boundary to operate within — without a declared scope, Scoped mode has nothing to scope.

Because `## LID Scope` is missing, I ran a conservative project-wide review treating every path as in-scope (per the coach's dispatch rule for this state).

**Scorecard**
- ✗ Configuration — Scoped mode declared with no `## LID Scope` section
- ⚠ Directive block — present but minimal; no mode/scope guidance for agents
- ⚠ HLD discipline — HLD exists but is a one-line stub
- ⚠ Arrow completeness — LLD and spec layers not yet authored
- ✓ Mode declaration — mode is explicitly declared, not inferred
- ✓ Minimum system — no custom conventions or surface bloat

**Headline:** The LID skeleton is in place and the mode is declared deliberately — the fastest win is declaring `## LID Scope` so Scoped mode is actually operable, after which the HLD can grow past its stub.

## Findings (4 total · 2 high · 2 medium · 0 low)

- **F1 (high):** `## LID Mode: Scoped` declared but no `## LID Scope` section exists · *modes are declared, not inferred*
- **F2 (high):** HLD is a single-line stub with no architecture or rationale · *HLD is architecture and rationale*
- **F3 (medium):** Directive block names the skill but carries no mode/scope orientation for agents · *minimum surface, maximum discipline*
- **F4 (medium):** LLD and spec layers unauthored — arrow cannot yet be walked end-to-end · *canonical arrow shape*

## What was audited

- Read fully: `CLAUDE.md`, `docs/high-level-design.md`
- Enumerated: `docs/llds/` (empty — `.gitkeep` only), `docs/specs/` (empty — `.gitkeep` only)
- Checked for: `docs/arrows/` overlay (absent), `@spec` annotations anywhere in the tree (none found)
- Scope of review: conservative project-wide (Scoped mode with no `## LID Scope` — all paths treated as in-scope for this pass)

## Detail — F1 through F4

**F1 — High. `CLAUDE.md` declares `## LID Mode: Scoped` but there is no `## LID Scope` section.** Scoped mode's entire job is to confine LID rigor — cascade discipline, scope-trigger warnings, and coach dispatch — to a declared set of paths inside a larger non-LID repo (which the HLD's one line confirms this is: "low-priority feature in a larger non-LID monorepo"). This relates to *modes are declared, not inferred* — a project is in exactly one mode, and a Scoped project must additionally declare `## LID Scope` with its include (and optional exclude) bullets. Why this matters: a Scoped declaration with no scope is the worst of both configurations. Agents can't tell which paths LID governs, so either everything gets treated as in-scope (Full rigor under a Scoped label — disproportionate overhead for a low-priority feature) or nothing does (LID silently no-ops). The ambiguity compounds: every future session has to re-derive the boundary from context that isn't on the page. Recommended action: run `/update-lid` to add a `## LID Scope` section enumerating the include path(s) for this feature (and any excludes); that one change makes Scoped mode operable.

**F2 — High. `docs/high-level-design.md` contains only a Problem heading with one sentence.** The HLD reads, in full, "Low-priority feature in a larger non-LID monorepo." This relates to *HLD is architecture and rationale* — the HLD carries the architecture-level *why*: problem, approach, target users, goals and non-goals, key design decisions, success metrics. Why this matters: with no approach, goals, or non-goals captured, the LLD and spec layers downstream have nothing to trace up to, and *effective intent-tree alignment* (specs → LLDs → HLD) can't hold because the top of the tree is empty. For a deliberately low-priority feature this doesn't need to be elaborate — but it needs enough that a fresh agent can answer "what is this feature for and what is explicitly out of bounds" without the conversation that produced it. Recommended action: expand the HLD to at least name the approach, the goals, and the non-goals for this feature; keep it proportionate to the feature's low priority — a few short sections, not a full architecture document.

**F3 — Medium. The directive block names the skill but gives agents no mode-aware orientation.** `CLAUDE.md`'s LID section is just "Consult the linked-intent-dev skill." This relates to *minimum surface, maximum discipline* — the directive block is thin by design, but a Scoped project benefits from the scope being visible at the point an agent reads instructions, not buried. Why this matters: in Scoped mode the most common friction is an agent touching out-of-scope paths or applying Full-mode rigor by default; a directive block that points at the scope declaration heads that off before it happens. This finding largely resolves itself once F1 is fixed (the `## LID Scope` section becomes the orientation), so treat it as a reason to fix F1 well rather than a separate task. Recommended action: when you run `/update-lid` for F1, let it reconcile the directive block alongside the scope section.

**F4 — Medium. The LLD and spec layers are unauthored, so the arrow has no middle.** `docs/llds/` and `docs/specs/` contain only `.gitkeep`; there are no `@spec` annotations anywhere and no `docs/arrows/` overlay. This relates to *canonical arrow shape* (HLD → LLDs → EARS → Tests → Code). This is *not* a defect on its own — an empty LLD directory in a freshly bootstrapped project simply means no LLDs have been authored yet, and the coach does not flag empty directories as gaps absent observed behavior that should have a spec. I surface it only so the path forward is explicit: once F1 and F2 land, the natural next step is to walk the actual feature change through `/linked-intent-dev` (with a description of what you're building), which authors the LLD and EARS layers as part of its workflow rather than as standalone busywork. Recommended action: after fixing scope and the HLD, invoke `/linked-intent-dev` with a description of the feature when you're ready to build it — the workflow will populate the LLD and spec layers in order.

---

Want me to walk through any of these findings in more depth, focus on the scope-configuration fix, or work through the `## LID Scope` content with you? You can also pick a single finding to dig into.

If you have broader questions about using LID — how Scoped mode behaves inside a larger non-LID monorepo, where a PRD would fit ahead of this HLD, or when it's worth promoting this feature from Scoped to Full — I'm happy to think through those with you too.
