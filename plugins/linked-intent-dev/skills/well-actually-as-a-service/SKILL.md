---
name: well-actually-as-a-service
description: A human-in-the-loop iteration loop where the agent's ONLY job is to refine intent — extract and confirm a precise intent with the user (menu-driven, concept by concept), record it into the LID arrow, then DELEGATE the compile (cascade → EARS → tests-first → code → build → demo) to a subagent. The human gates the intent before any code, evaluates the demo, and either accepts or feeds back a new intent. A zero-context haterbot (an adversarial reviewer) hardens the intent (and dedups/flags conflicts) before recording and refutes the compiled work before the demo. Loops until the user exits. Use when iterating a feature/behavior tightly with a user who wants to drive — especially UI/feel work where the result must be seen to be judged.
disable-model-invocation: true
---

# well-actually-as-a-service

*The "well, actually" reflex, productized. Before any code, your intent gets
pedantically interrogated until it's airtight; a subagent then compiles it; and a
zero-context haterbot "well, actually"s both the intent and the result. A LID loop.*

A tight iteration loop for building *with* a user, not ahead of them. The core
inversion: **the driving agent never writes code.** Its sole purpose is to refine
the user's intent into a precise, confirmed statement and record it in the arrow.
The arrow is then *compiled* — cascaded into EARS, tests, code, a build, and a
running demo — by a **subagent**. The user gates the **intent** before any code
exists, and gates the **demo** to confirm the compile was faithful.

This exists because the common failure is the agent inferring intent from a
one-liner and racing to code, so the user only ever gets to approve the *built
behavior* and must correct interpretation gaps post-hoc, every cycle. Moving the
gate to the intent — and keeping the refiner's hands off the keyboard — kills that.

## Roles

- **Human** — states a want; gates the intent phrasing; evaluates the demo;
  accepts or feeds back. The only one who says "yes, that's the intent" and
  "yes, that's the behavior."
- **Refiner** (the agent running this skill) — extracts + confirms intent
  (menu-driven), records it into the arrow, dispatches the compiler subagent,
  presents the demo. **Writes no code on the full loop** (may type an
  objectively-trivial, arrow-recorded fast-path edit — see *Routing the want*).
- **Compiler** (a subagent, spawned per accepted intent) — cascades the recorded
  intent through the LID arrow: LLD → EARS → **tests-first** → code → build →
  launch the demo. Reports back. Implements *exactly* the intent — no more.
- **Haterbot** (a **zero-context** subagent) — gets **no conversation history**;
  it reads the *arrow*, never the chat. Runs twice per cycle: once to attack the
  proposed intent (pre-record), once to refute the compiled work (post-compile).
  Skeptical by default; a pass means "no counterexample found this pass," not proof.

## The loop

Repeat until the user exits. Immediately after the **Want**, **route** the change
(see *Routing the want* below) into the **full loop** that follows or the **fast
path** — the fast path keeps every gate that matters (the intent confirmation, the
arrow-first record, Pass II, the demo) but drops Pass I — and, for a trivial
value/string edit, the compiler hand-off — for changes that stay inside the existing
spec envelope (below); a large but envelope-clean change keeps the fast route yet still
delegates typing to the compiler. The full loop:

1. **Want.** The user states what they want different ("I want X to be Y").
2. **Refine the intent.** Extract it **concept by concept**, using
   `AskUserQuestion` menus to verify and whittle it down. State your current
   understanding concisely; offer the real forks as options; surface tensions
   *with evidence* (the substrate, the spikes, prior decisions); prefer terse
   pushback to compliant motion. Iterate until the **user passes the intent
   phrasing** — an explicit, single, unambiguous statement of the intended
   behavior. *This is the gate. Do not proceed without it.*
3. **Haterbot I — harden + coherence-check the intent** (pre-record). Spawn a
   zero-context haterbot with *only* the proposed intent phrasing + the existing
   arrow. It attacks the phrasing (ambiguity, contradiction, missed edge cases)
   **and** checks it against already-recorded intents for **duplicates** (already
   captured — don't re-record) and **conflicts** (contradicts a recorded
   decision/spec — resolve with the user first). The refiner dedups, resolves, or
   sharpens accordingly. (Pass I is the **only** skippable pass — fast path only, and
   the skip must be disclosed; see *Routing the want*.)
4. **Record the intent in the arrow.** Write the confirmed intent into the LID
   source: the relevant `docs/llds/<segment>.md` (the design decision) and an
   `docs/specs/<segment>-specs.md` EARS line (the testable behavior, `[ ]`). The
   LLD/EARS — not the binary — is the artifact the user approved.
5. **Compile (delegate).** Spawn a **subagent** (the compiler) with the recorded
   intent + the arrow context. It does the whole cascade: confirm/extend the
   LLD, write the EARS, write the **failing test first**, implement the code,
   build, and **launch the demo**. See *Compiler contract* below. The refiner
   does not implement.
6. **Haterbot II — refute the work** (post-compile, pre-demo). Spawn a zero-context
   haterbot with *only* the recorded intent + the compiler's diff/arrow. It tries
   to **refute** that the code faithfully and correctly realizes the intent —
   bugs, untested paths, drift, scope creep, lies. The refiner resolves the
   findings (loop the compiler) or surfaces them to the human before acceptance.
   **Pass II is never skipped** — on the fast path it also **audits the route**
   (does it stay inside the spec envelope; do cumulative edits escape it).
7. **Demo.** The compiler launches the result for the user to evaluate (for a UI,
   it runs the app on the user's display; for logic, it surfaces the passing
   tests + any state dump). The demo is *confirmation that the compile matched
   the intent*, not the first sight of the agent's interpretation.
8. **Gate the behavior.** The user either:
   - **Accepts** — the behavior matches the intent. The arrow is coherent (spec
     `[x]`, test green, no drift). Move to the next want.
   - **Clarifies / feeds back** — the behavior is off, or the intent evolved.
     The feedback becomes a **new intent** → back to step 2.
9. **Exit** when the user signals done.

## Routing the want — fast path vs full loop

Pick the path from the **EARS spec envelope**, never from how risky the change feels.
This skill exists because agents systematically **under-rate interpretation-risk**
("I'll just infer it from the one-liner") — so **interpretation-risk is never a
routing input.** Any uncertainty about what the want *means* routes to the full loop;
that is what the menu is for. **When in doubt, full loop.**

The routing oracle is the spec, because the spec *is* the recorded intent. A change
**stays inside the envelope** — and may take the fast path — only when **all** hold:

1. **It breaks no existing spec — cleared only by a real green from a real test.**
   Run the relevant spec's tests against the change; if any goes **red**, that is the
   fault line — **break there**: stop and cascade from the broken spec (full loop).
   **"Relevant" is every spec whose test this change could turn red, across segment
   boundaries** — not just the touched segment's; if you can't bound the blast radius,
   full loop. The gate's oracle is the test, so **no-oracle is not a pass**: when a **relevant**
   spec — one you cannot show the change leaves untouched, by a real green test or by
   **structural non-overlap** (different module, no shared state or output) — is backed
   only by an **absent, inspection-exit / proxy-only, or deleted-or-loosened** test,
   that spec **counts as red**: a proxy is no oracle and **cannot *clear* a route** (you
   can't prove you didn't break it). **Affectedness for a no-oracle spec is *shown*, not
   *asserted*** — you may not scope a spec out of the relevant set by *judging* it
   unaffected; show non-overlap or treat it as red. An inspection-exit stays valid
   *coverage* for a new surface property (fast-path step 4); it just can't *clear* a
   route. A red test routes full-loop **regardless of cause**
   — "the test was stale / over-specified" is itself a spec-level change (the recorded
   behavior was wrong) and cascades from the spec; never silently loosen or delete a
   test to clear the gate (editing a test's assertion is a spec change, not a route
   input). The gate is *executable*, not a judgment — the test, not the agent, rules
   on "did this change recorded intent," which is exactly why a weak or proxy-seam test
   corrupts the route (see *Test-first, honestly*). Evaluate by reasoning at spec level
   before code, or by probing in a throwaway worktree — never commit code ahead of the
   arrow to decide a route.
2. **It needs no new spec, and sits behind a spec already `[x]` with a real test.** It
   adds no observable behavior that no spec covers — a change can break *zero* specs
   yet still change behavior the specs are simply silent on; that behavior is **new
   intent** and must be recorded, so it takes the full loop. A spec marked `[ ]`
   (active gap, unimplemented) is **new behavior for routing**: first-realizing it is
   full loop even though the spec line already exists — gate 2 clears only for a change
   behind an already-`[x]`, test-covered spec. This is the one residual judgment in the
   router, backstopped by Pass II's route-audit and a bidirectional-differential audit
   over the arrow-maintenance overlay ("intent the code encodes that no EARS states"). *(The labels change broke no spec,
   yet needed `HOME-UI-008` — gate 2 is what catches that.)*
3. **It touches no safety/invariant spec** (no `*-SAFE-*`, nothing tagged invariant).
   Those take the full loop and real test-backed code regardless of size — a green
   test on a safety-critical change isn't enough when the test could be weak. A
   one-line change to a write-arming default is one line and still full-loop.

Changes that usually clear gates 1–3 are value-edits behind an existing `[x]` spec (a
label, a keybind, a duration, an already-enumerated enum), pure deletions with no
remaining referents (but a deletion that removes behavior an `[x]` spec covers is a
spec change, not a fast-path deletion), and doc-only edits — but the **trigger is the
envelope, not the shape**. If the change **breaks a spec, needs a new spec, or touches a SAFE/invariant
spec, it is not fast-path — full stop.** Everything else, and the default, is the
**full loop** (steps 2–8).

**On the fast path** the steps collapse but the discipline does not:
1. State the one-line intent; get a single confirmation (the menu may be one
   question — the intent gate is never skipped).
2. **Record the value/prose in the arrow first** — before or atomically with the
   edit. "No code ahead of the arrow" is the skill's definition, not ceremony.
3. The refiner **may type the edit itself** — an arrow-recorded change inside the
   envelope is not the race-to-code the no-code rule guards against — **but only when
   the edit is a value/string substitution with no change to control flow, types, or
   call graph**. A rename or constant-bump touching many files, or any
   behavior-preserving change that is large or spans many physical sites, still
   **delegates to the compiler**: the envelope clears the route, but size still governs
   who types it and whether the hand-off pays for itself.
4. **Cover the touched spec** — a test, a snapshot, or a declared inspection-exit
   (see *Test-first, honestly* in the Compiler contract). A fast-path edit may not
   leave a spec uncovered.
5. **Pass I may be skipped; Pass II never.** Disclose the skip: state which fast-path
   criterion matched, the arrow location of the record, and **name the exact `[x]`
   spec ID the change sits behind, asserting it adds no output or state that spec's
   text doesn't already describe** (a falsifiable claim, not "it's covered"). Pass II
   additionally **audits the route**, and its **verdict is recorded in the arrow**: a
   fast-path change may not reach the demo/accept gate until that Pass II verdict
   artifact exists — **no verdict, no route** (it reverts to the full loop). The fast
   path has no other mandatory subagent, so this artifact is the human's one
   independent check that the route was audited.
6. Demo + gate as in the full loop.

**Salami-slicing guard.** If a fast-path edit is the **Nth edit to the same segment —
within one want *or across wants since that segment's last full-loop touch or
reconciliation*** — or the cumulative fast-path edits would change a spec's meaning,
the change retroactively requires the **full loop**. Pass II catches the within-want
case ("these three label edits together change the behavior the spec describes"); the
**reconciliation sweep** (Notes) is the cross-want backstop — treat it as a gate, not
just cleanup.

## Intent-refinement discipline (step 2)

- One concept per turn: a concise understanding statement, then one menu.
- Menus present the genuine forks; recommend when you have a basis; never invent
  options to pad. The user's *choice* reveals latent intent.
- Ground every read in evidence (code, substrate contracts, the spike lineage,
  prior arrow decisions). If the user's framing conflicts with the evidence,
  surface the tension — don't silently go along.
- Whittle, don't expand: each round should narrow to a sharper, smaller intent.
- Stop when the user passes the phrasing. Capture it verbatim.

## Compiler contract (step 5 — the subagent)

Hand the subagent a self-contained brief:

- **The confirmed intent**, verbatim, and the EARS ID(s) it realizes.
- **The arrow context**: which LLD/segment, the relevant code files, the
  project's CLAUDE.md conventions.
- **The cascade order**, non-negotiable: confirm/extend the LLD → write/adjust the
  EARS spec → write the **failing test first** → implement → build → launch the
  demo → report (files changed, specs flipped `[x]`, test result, how to see it).
- **Bounds**: implement *exactly* the intent; do not add scope; flag anything the
  intent didn't cover as an Open Question rather than guessing.
- **Honesty**: "untested = broken"; a passing test is "no counterexample this
  pass," not proof. No code ahead of the arrow.
- **Test-first, honestly**: do not manufacture a proxy *seam* purely to make a
  property assertable. For anything the code **computes or decides** (a branch, a
  write, a value derivation, a state machine, error handling) — and for **every
  SAFE/invariant spec regardless of difficulty** — write a real test against the
  behavior. For a **user-visible surface** property the human judges at the demo
  (render presence/absence, layout, feel, timing) with no deterministic programmatic
  assertion: try a **snapshot first**; only if that fails, declare a **"verified by
  inspection"** exit **in the spec**, naming the proxy and stating the weakness
  plainly ("asserts a proxy the code controls, not the user-visible surface"). **If the
  surface (presence, layout, value shown) is conditioned on or derived from anything the
  code computes or decides, that decision is logic** — give it a real test; the
  inspection-exit covers only the *unconditioned* surface. Never inspect away logic;
  never ship a green test that asserts a proxy you control — that is the "green test
  that asserts the wrong thing" Pass II hunts.

Run one compiler per accepted intent (use `isolation: worktree` if compiles may
run concurrently). The refiner relays the compiler's report + the demo to the user.

## Haterbot contract (steps 3 & 6)

The haterbot is a **zero-context** subagent: it receives no conversation history.
It reads the **arrow** (recorded intents, LLDs, specs) and the artifact under
review — never the chat. Spawn it fresh each pass. Its whole personality is
"well, actually" — default to skeptical and try to be right about it.

**Pass I — attack the intent (pre-record).** Brief = the proposed intent phrasing +
the existing arrow.
- Refute the phrasing: name every ambiguity, contradiction, and unhandled edge case.
- Coherence: is this intent a **duplicate** of an already-recorded intent/spec? Does
  it **conflict** with a recorded decision? Cite the offending arrow location.
- Verdict: the sharpened phrasing + a dedup/conflict ruling.

**Pass II — refute the work (post-compile).** Brief = the recorded intent + the
compiler's diff / changed files.
- Try to prove the code does NOT faithfully + correctly realize the intent: bugs,
  untested paths, behavior beyond the intent (scope creep), drift from the spec, a
  green test that asserts the wrong thing.
- A **manufactured proxy seam** — a test that asserts a value the code controls
  rather than the user-visible surface — counts as "asserts the wrong thing"; flag
  it. A declared inspection-exit must name its weakness in the spec or it's drift.
- If the change took the **fast path**, audit the route against the spec envelope:
  does it truly break no existing spec (re-run the relevant tests **across segments**;
  treat an **absent, proxy-only, or deleted test as red**), sit behind an
  already-`[x]` test-covered spec (not first-realizing a `[ ]` gap), need no new spec,
  and touch no SAFE/invariant spec? And do the cumulative edits escape the envelope
  (salami-slicing)?
- When Pass II is **uncertain whether the code encodes an unstated invariant the EARS
  doesn't state** (a `B-ONLY-DRIFT`-shaped worry) on a **consequential** change,
  escalate that one EARS to a single blind **bidirectional-differential** round-trip
  rather than guessing — its B-direction reconstructs the EARS from blind code, and its
  blindness is the edge (it can't be fooled by the context that biases this pass).
  Opt-in and per-EARS, never the default; needs the arrow overlay + `@spec`.
- Default to "refuted" when uncertain; cite `file:line`.
- Verdict: confirmed / refuted-with-findings.

Skeptical by default; a pass is "no counterexample found *this pass*," not proof.
Use a perspective-diverse panel (correctness / spec-fidelity / scope) when the
change is consequential. The refiner resolves or surfaces every finding before the
human is asked to accept.

## Hard rules

- The **refiner writes no code on the full loop** — it refines intent and records
  it; the compiler implements. (On the fast path the refiner may type the
  objectively-trivial, arrow-recorded edit itself — the rule guards against
  race-to-code on substantive work, not a label edit or a deletion.)
- **Route before you refine** — by the spec envelope (breaks no existing spec, needs
  no new spec, touches no SAFE/invariant spec), never by felt risk; any uncertainty
  about *meaning* routes to the full loop (see *Routing the want*).
- The **gate is on the intent** (steps 2–3), confirmed *before* any compile. The
  demo gate (step 8) only checks fidelity.
- **One intent per compile.** Don't batch unrelated changes into one subagent.
- **Test-first, or declare the exit.** The behavior isn't trusted until a test
  asserts it; the only exception is a user-visible surface property with no
  deterministic assertion, which gets a snapshot or a weakness-disclosed
  inspection-exit recorded in the spec — never logic, never a SAFE/invariant spec,
  never a manufactured proxy seam. The router trusts these tests to decide whether a
  change breaks a spec, so a weak or proxy test mis-routes the change.
- **No code ahead of the arrow.** The LLD/EARS delta precedes the code, always —
  fast path included.
- **Pass II is never skipped; only Pass I is** (fast path only, with the skip
  disclosed). A zero-context haterbot hardens the intent before recording (and
  dedups/flags conflicts against the arrow) and refutes the compiled work before the
  demo; on the fast path Pass II also audits the route. Because the fast path has no
  other mandatory subagent, acceptance there is gated on a **recorded Pass II verdict
  artifact** — no artifact, no route (reverts to full loop). The refiner resolves or
  surfaces every finding before asking the human to accept. The haterbot reads the
  arrow, never the chat.

## Scope & trust boundary

This skill governs a **cooperating agent**. Like any prose, it *instructs*; it cannot
*enforce*. Three boundaries follow — stated so a reviewer doesn't mistake them for
unhandled holes:

- **Enforcement that a step actually fires is a harness concern, not prose.** "Pass II
  is never skipped" is a rule the refiner is trusted to honor; what *makes* it hold on
  the fast path is the external accept-gate — a Stop hook that blocks acceptance until a
  recorded Pass II verdict artifact exists. The skill specifies the artifact; the hook
  enforces it. A bad-faith agent can ignore any line here exactly as it can ignore any
  instruction — that is the harness's boundary to hold, not the document's.
- **Gate 2 ("needs no new spec") is an irreducible judgment.** By construction, brand-new
  behavior breaks no existing test, so no executable oracle can detect it. The skill does
  not pretend otherwise: it shrinks the discretion (the falsifiable disclosure naming the
  `[x]` spec ID) and backstops it three ways — Pass II's route-audit, the reconciliation
  sweep, and a bidirectional-differential audit over the arrow-maintenance overlay.
  Residual judgment remains, by nature.
- **The bar is good-faith guidance, not adversary-proofing.** Success = a good-faith
  agent is steered to the right path, the honest path is the cheapest, and the human has
  one artifact (the Pass II verdict) to check. "Could a determined bad actor still cheat?"
  is always *yes* for a document, and is out of scope here.

## Notes

- This skill formalizes the cycle: refine intent → record → compile via subagent →
  demo → gate → loop. It composes with `linked-intent-dev` (the cascade the
  compiler runs) and `update-lid` (project setup).
- Routing changes to the fast path (Pass I skipped-with-disclosure, Pass II + its
  route-audit retained; the refiner types a trivial value/string edit itself, while a
  large but envelope-clean change still delegates typing to the compiler) is governed by
  *Routing the want* — the intent gate and the arrow-first record are never skipped.
- **Reconciliation sweep.** Fast-path edits drift values out from under their specs
  silently over time. At segment close, batch-audit the `[x]` EARS touched since the
  last sweep with the **bidirectional-differential** audit — the concrete form of the
  gate-2 / silent-spec backstop: a `B-ONLY-DRIFT` verdict means a fast-path edit quietly
  changed behavior the spec doesn't state → surface it as a new want and cascade. A fast
  lane without this sweep rots the arrow. (Requires the `arrow-maintenance` overlay +
  `@spec` annotations; absent either, the sweep degrades to a manual spec re-read.)
- **bidirectional-differential is post-hoc, not a router input.** It greps `@spec`
  against landed code, so it can only audit a *result*, never inform the *route* (which
  precedes code). Gate 2 stays a judgment; bidiff is the instrument that catches a
  *wrong* gate-2 call and feeds the next cycle. The compiler's linked-intent-dev
  Phase-6 boundary already makes bidiff's ambient trigger eligible — the two touchpoints
  above are what this loop adds deliberately on top. Advisory throughout: a concentrator
  of human attention, not an oracle (it inherits the audit's naive-baseline and small-N
  limits).
