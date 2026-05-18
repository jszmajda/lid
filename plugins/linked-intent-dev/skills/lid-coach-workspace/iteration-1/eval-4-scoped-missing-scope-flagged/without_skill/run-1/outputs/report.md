# LID Coach Review

## 1. Executive summary

**Posture:** *Bootstrapping — Scoped declared, scope undeclared; arrow not yet authored.*

This project has made the foundational moves: it declares LID directives in `CLAUDE.md`, picks a mode explicitly, and has the `docs/` skeleton (`high-level-design.md`, `docs/llds/`, `docs/specs/`) in place. The thing holding it back from delivering LID's value is that **Scoped mode is declared without a `## LID Scope` section** — so the mode's central control input is missing. Everything else is early-stage rather than drifted, which is the good news: there's almost no accumulated debt to unwind, just structure to fill in.

**Scorecard**

- ✗ Configuration — Scoped mode declared, but no `## LID Scope` section in `CLAUDE.md`
- ⚠ Mode fit — Scoped is plausible for a low-priority feature in a non-LID monorepo, but unverifiable until scope is declared
- ⚠ HLD discipline — HLD exists but is a one-line stub; not yet load-bearing
- ⚠ Arrow completeness — only HLD (stub) exists; no LLDs, specs, tests, or code yet
- ✓ Mutation hygiene — no accumulation residue (nothing has accumulated yet; clean slate)
- ✓ Minimum system — no custom conventions; standard layout, thin surface

**Headline:** The directive block and mode declaration are in place and the layout is standard — the single most valuable next step is declaring the `## LID Scope` section so Scoped mode actually has the input it runs on, then growing the stub HLD into real architecture-and-rationale before LLDs are authored.

## 2. Findings inventory

**Findings (4 total · 1 high · 3 medium · 0 low)**

- **F1 (high):** `CLAUDE.md` declares `## LID Mode: Scoped` but has no `## LID Scope` section · *modes are declared, not inferred*
- **F2 (medium):** `docs/high-level-design.md` is a one-line stub — Problem only, no approach/goals/non-goals/decisions · *HLD is architecture and rationale*
- **F3 (medium):** Arrow is HLD-only — no LLDs, specs, tests, or code yet · *canonical arrow shape*
- **F4 (medium):** Mode fit unverifiable — Scoped is plausible but cannot be confirmed without a declared scope · *mode fit*

## 3. What was audited

- Read fully: `CLAUDE.md`, `docs/high-level-design.md`
- Enumerated: `docs/` tree (HLD + empty `docs/llds/` and `docs/specs/`, each holding only `.gitkeep`)
- Detection grep: LID directives present (`## Linked-Intent Development`, "Consult the linked-intent-dev skill"); `## LID Mode: Scoped` present; `## LID Scope` **absent**
- Overlay: no `docs/arrows/` — arrow-maintenance overlay not installed
- Code/tests: none present in the project
- Dispatch path taken: *Scoped mode with missing `## LID Scope`* → misconfiguration surfaced as a high-priority finding; conservative project-wide review run treating all paths as in-scope

## 4. Out-of-scope note

Because `## LID Scope` is undeclared, this review could not honor a scope boundary. Per the coach's dispatch rule for this state, the review was run **conservatively project-wide, treating all paths as in-scope**, rather than guessing at an intended scope. Once F1 is resolved by declaring the scope, a re-run will respect that boundary and this section will list anything deliberately excluded.

## 5. Findings — detail

**F1 — High. `CLAUDE.md` declares `## LID Mode: Scoped` but contains no `## LID Scope` section.** Line 1 of `CLAUDE.md` reads `## LID Mode: Scoped`, and a grep for `## LID Scope` returns nothing. Under *modes are declared, not inferred* — a project is in exactly one mode at a time, and Scoped projects additionally declare their scope so cascade rigor and scope triggering have a boundary to key off — Scoped mode without a scope declaration is a mode running blind. Why this matters: in Scoped mode the scope list is the control input that decides which paths LID enforces and which it leaves to the surrounding non-LID monorepo. With it missing, every downstream tool (including this coach) has to fall back to a conservative whole-project assumption, which is exactly the friction Scoped mode exists to remove — and it gets worse, not better, as the feature grows and more of the monorepo becomes ambiguously in-or-out. Recommended action: run `/update-lid` to add a `## LID Scope` section to `CLAUDE.md` with an include list (and optional exclude list) naming the directories/paths this low-priority feature actually owns.

**F2 — Medium. `docs/high-level-design.md` is a one-line stub.** The entire HLD is a `# HLD` heading, a `## Problem` section reading "Low-priority feature in a larger non-LID monorepo," and nothing else — no approach, target users, goals/non-goals, key design decisions, or success metrics. Under *HLD is architecture and rationale* — the HLD carries the architecture-level *why* that outlives any specific implementation — a stub HLD means there is no anchor for LLDs to trace up to. Why this matters: LLDs and specs derive their legitimacy from tracing to an HLD concept; if LLDs are authored against a one-line HLD, the *why* lives only in whoever's chat session produced them, and future agents inherit decisions with no rationale to check them against. This is cheap to fix now and expensive to retrofit once the arrow has length. Recommended action: before authoring LLDs, grow the HLD to carry at least the approach, goals/non-goals, and the key design decisions for this feature — keep implementation detail (schemas, signatures) out; that belongs in LLDs.

**F3 — Medium. The arrow is HLD-only.** `docs/llds/` and `docs/specs/` contain only `.gitkeep`; there are no tests or code in the project. Under *canonical arrow shape* — `HLD → LLDs → EARS → Tests → Code` — only the first (stub) node exists, so there is no walkable arrow yet. Why this matters: this is expected for a project at bootstrap and is not drift — flagging it only because directories are empty would be nagging a deliberate early state. It is surfaced as medium (not high) because there is no *observed behavior* lacking an LLD; it is simply a not-yet-built arrow. The reason to name it at all: the natural next move after declaring scope (F1) and fleshing the HLD (F2) is to walk the first real change through `/linked-intent-dev`, which authors the LLD → EARS → tests → code chain in order rather than backfilling later. Recommended action: once F1 and F2 are addressed, start the first feature change with `/linked-intent-dev` and a description of what to build — let the workflow author the downstream arrow nodes in sequence.

**F4 — Medium. Mode fit cannot be confirmed.** "Low-priority feature in a larger non-LID monorepo" (the HLD Problem statement) is a textbook case *for* Scoped mode — you want LID rigor on one feature, not the whole monorepo. Under *mode fit* — the declared mode should match project reality so friction lands on real decisions rather than configuration mismatch — the choice of Scoped looks correct in spirit. Why this matters: the fit cannot actually be verified until F1 is resolved, because "does the declared scope match reality?" has no scope to check against. This finding is really a corollary of F1 and resolves with it; it is listed separately so that when scope is declared, the re-run explicitly confirms the include list is genuinely a subset of the monorepo (Scoped whose scope is most of the repo would itself be a mode-fit signal). Recommended action: when adding the `## LID Scope` section per F1, keep the include list tight to the feature's own paths; a re-run of `/lid-coach` will then confirm mode fit.

## 6. Offer to help

Want me to walk through any of these findings in more detail, focus on the high-priority configuration fix, or work through the scope declaration and HLD fleshing-out together? You can also pick a specific finding to dig into.

If you have broader questions about using LID for this situation — how to scope a feature inside a non-LID monorepo, what belongs in the HLD vs. the LLDs, or when Scoped should become Full as the feature grows — I can help think those through too.

---

*Advisory note: this skill does not edit project files. The recommendations above are surfaced for you to apply — configuration changes (F1, and F4 with it) go through `/update-lid`; the first feature build goes through `/linked-intent-dev`.*
