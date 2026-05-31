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
  presents the demo. **Writes no code.**
- **Compiler** (a subagent, spawned per accepted intent) — cascades the recorded
  intent through the LID arrow: LLD → EARS → **tests-first** → code → build →
  launch the demo. Reports back. Implements *exactly* the intent — no more.
- **Haterbot** (a **zero-context** subagent) — gets **no conversation history**;
  it reads the *arrow*, never the chat. Runs twice per cycle: once to attack the
  proposed intent (pre-record), once to refute the compiled work (post-compile).
  Skeptical by default; a pass means "no counterexample found this pass," not proof.

## The loop

Repeat until the user exits:

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
   sharpens accordingly. (For trivial tweaks this pass may be skipped — see Notes.)
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
- Default to "refuted" when uncertain; cite `file:line`.
- Verdict: confirmed / refuted-with-findings.

Skeptical by default; a pass is "no counterexample found *this pass*," not proof.
Use a perspective-diverse panel (correctness / spec-fidelity / scope) when the
change is consequential. The refiner resolves or surfaces every finding before the
human is asked to accept.

## Hard rules

- The **refiner writes no code** — it refines intent and records it; the compiler
  implements.
- The **gate is on the intent** (steps 2–3), confirmed *before* any compile. The
  demo gate (step 8) only checks fidelity.
- **One intent per compile.** Don't batch unrelated changes into one subagent.
- **Test-first inside the compile.** The behavior isn't trusted until a test
  asserts it.
- **No code ahead of the arrow.** The LLD/EARS delta precedes the code, always.
- **Two haterbot passes per cycle** — a zero-context haterbot hardens the intent
  before recording (and dedups/flags conflicts against the arrow) and refutes the
  compiled work before the demo. The refiner resolves or surfaces every finding
  before asking the human to accept. The haterbot reads the arrow, never the chat.

## Notes

- This skill formalizes the cycle: refine intent → record → compile via subagent →
  demo → gate → loop. It composes with `linked-intent-dev` (the cascade the
  compiler runs) and `update-lid` (project setup).
- For trivial, unambiguous tweaks (a keybind, a duration) the refiner may still
  state the one-line intent and record it before dispatching — the gate can be a
  single confirmation rather than a multi-round menu, but it is never skipped.
