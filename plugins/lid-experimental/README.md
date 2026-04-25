# lid-experimental

Opt-in plugin for **experimental LID skills** — techniques that have earned their place but aren't yet promoted into the core LID workflow. This plugin is separate from `linked-intent-dev` and `arrow-maintenance` on purpose: it lets you try new skills with eyes open about their cost, lifecycle, and immaturity, without those skills lurking inside your default install.

If you're new to LID, start with the [main README](../../README.md) and the core plugins. Come back here once the basics are familiar and you're curious what else is possible.

---

## Install

```
/plugin install lid-experimental@jszmajda-lid
```

That's it. The plugin's skills become available in Claude Code immediately. No `lid-setup`-style bootstrapping is required at the plugin level — each experimental skill declares its own preconditions (and aborts cleanly if they aren't met).

---

## Why "experimental" is a separate plugin

LID's core (`linked-intent-dev` + `arrow-maintenance`) is the part of the methodology we believe in enough to recommend by default. Experimental skills are different:

- **Higher maintenance ceiling.** Experimental skills often layer on top of the core plugins and ask more from you — heavier docs discipline, real Anthropic API spend on subprocesses, more interpretive judgment. The `bidirectional-differential` skill below, for example, requires `arrow-maintenance` to be set up first and costs real money per audit.
- **Faster iteration.** Behaviors, defaults, even the skill names can change between releases. We try to keep changes coherent, but the core's stability guarantees don't apply here.
- **Explicit lifecycle.** Every experimental skill has one of two futures: **promotion** into core (its design and code move into `linked-intent-dev` or `arrow-maintenance`) or **retirement** (it's deleted from the repo, and you uninstall the plugin). The plugin exists so neither outcome surprises you.

In short: install this plugin if you want to try the new stuff and you accept that "the new stuff" is where things change first.

---

## What's in here

### `bidirectional-differential`

Audits **EARS↔code coherence** by running two parallel fresh Claude sessions on a single EARS+code pair. One session sees only the EARS and writes naive code from it (the *A-direction*). The other sees only the production code with leaky identifiers stripped out and reconstructs what the EARS must have said (the *B-direction*). The skill compares both reconstructions against ground truth and classifies the result.

Five outcome codes plus one signpost:

| Code | What it means |
|---|---|
| `BD-COHERENT` | Both reconstructions match the originals. Intent and code agree. |
| `A-ONLY-DRIFT` | The code makes an arbitrary implementation choice the EARS doesn't pin down. Usually fine. |
| `B-ONLY-DRIFT` | The code encodes intent (an invariant, a contract, an edge-case handling) the EARS doesn't state. Reconcile by updating the EARS. |
| `BIDIRECTIONAL-DRIFT` | Both reconstructions disagree with ground truth in correlated ways. A real drift signal — a missing sub-decision, an operational halo, or a decomposition gap. |
| `INCONSISTENT-BLIND` | The audit can't classify cleanly because the EARS itself is too ambiguous. Tighten the EARS first. |
| `UNANNOTATABLE` | The EARS is a negative requirement ("shall NOT X") with no production-code sink. Out of scope for this technique; the skill suggests an alternative. |

When drift is found, the skill's recommendation walks the LID arrow in order — validate the discovered intent with you, check LLD coherence, update the EARS, update tests, then adjust code only if needed. The skill never recommends a code change without first ensuring tests will assert the intended behavior.

#### What audits typically surface

In an early sample of six EARS specs from a real codebase, **five surfaced drift worth investigating; one was genuinely coherent**. Findings clustered into a handful of recurring shapes — single-claim specs missing a sub-decision, operational behavior that the code implements but the spec doesn't mention, sibling specs that don't cross-reference each other, and unstated invariants in the code. See [Appendix A](#appendix-a-what-a-real-audit-found) for concrete worked examples.

#### When to use it

- You want a deeper coherence check than `arrow-maintenance` provides on a specific feature or segment.
- You've finished a Phase 6 implementation in `linked-intent-dev` and want a second opinion on whether the EARS and the code agree about meaning.
- You're investigating a hunch — *"I think this spec doesn't actually say what we built"* — and want a structured way to confirm or refute it.

#### When not to use it

- You haven't run `arrow-maintenance` yet. The skill aborts with a hard error in that case — overlay-based audit machinery is its foundation, not optional.
- You're looking at a small, throwaway change. The audit costs real subprocess spawns; not every change is worth the spend.
- The EARS in question is intentionally vague (e.g., quality-of-result EARS that depend on LLM judgment). The skill will likely return `INCONSISTENT-BLIND` and tell you to refine the EARS first.

#### How to invoke

```
/lid-experimental:differential-audit
```

With no arguments, the skill opens a scoping conversation:
1. It asks what you want audited in plain language ("the login flow", "the scoring rules").
2. It maps your description to one or more arrows in your overlay and confirms the alignment.
3. It shows you the EARS inventory for each chosen arrow and asks which to audit.
4. It captures the runs-per-direction (default 3) and shows a cost estimate.
5. After your explicit confirmation, it spawns the blind sessions in parallel and writes per-EARS audit records under `docs/arrows/experiments/bidirectional-differential/`.

You can also pass EARS IDs directly to skip the conversation:

```
/lid-experimental:differential-audit AUTH-UI-001 AUTH-UI-002
```

#### Configuring it per project

Add a section to your project's `CLAUDE.md` to override the skill's defaults:

```
## LID Experimental
bidirectional-differential:
  ambient: false           # disable the Phase-6 ambient hook
  default-runs: 5          # override N=3 if you want more confidence per audit
```

#### Where audit records land

```
docs/arrows/experiments/bidirectional-differential/{segment-name}/{EARS-ID}.md
```

Each record is a per-EARS markdown file with the classification, the per-direction summaries, the drift findings, and a cascade-shaped recommendation list (validate → LLD → EARS → tests → code). New audits replace the file in place — `git diff` is how you compare two audits across time.

The reserved subtree under `docs/arrows/experiments/` keeps `arrow-maintenance` from touching these records during its own audits. If this experiment is ever retired, deleting the subtree is the cleanup; if it's promoted, the records and protocol move into core in one mechanical step.

#### Design rationale

For the design decisions behind this skill — why the audit is bidirectional rather than one-shot, why the user picks scope explicitly rather than the skill recommending it, why the repair path walks the full LID arrow rather than just editing the layer the audit found drift on — see the LLD: [`docs/llds/lid-experimental/bidirectional-differential.md`](../../docs/llds/lid-experimental/bidirectional-differential.md).

---

## Lifecycle and stability

Experimental skills follow the LID-experimental framework documented in [`docs/llds/lid-experimental.md`](../../docs/llds/lid-experimental.md). The short version:

- **A skill earns promotion** when adoption signals say "this should be core" — users report real wins, the design has stabilized, the implementation isn't churning. On promotion, the skill moves into `linked-intent-dev` or `arrow-maintenance` and the experimental version is deleted from this plugin.
- **A skill is retired** when it stops earning its keep — chronically low signal, the underlying tooling absorbs what it does, or the design fails to converge. Retirement is `rm -rf`; you uninstall the plugin (or just the skill, once the plugin supports skill-level granularity) and move on.
- **The plugin itself** stays at version 0.x while at least one skill is experimental. It graduates only if and when the framework has earned a 1.0 — different question from any individual skill's lifecycle.

If you adopt an experimental skill, expect to track changes more actively than you would for the core plugins. The repo's commit log on `plugins/lid-experimental/` is where that activity lives.

---

## Reporting issues, asking questions

GitHub Issues on the [LID repo](https://github.com/jszmajda/lid) with the `lid-experimental` label. Real-world feedback is what tells us whether a skill should be promoted or retired — that's the loop we're trying to close.

---

## Appendix A: What a real audit found

In an early sample of six EARS specs from a real codebase — ranging from short single-claim rules to multi-line behavioral specs — five surfaced drift worth investigating; one was genuinely coherent. Concretely, in plain language:

- **A "cap at 20" rule that didn't say which 20.** The code kept the twenty oldest items by creation timestamp. The spec didn't pin that down. Three independent agents writing code from the spec alone produced three different answers (input order, newest-first, oldest-first). The audit surfaced the choice as worth a product conversation.

- **A "prefer field A over field B" rule that didn't address empty values.** Code used JavaScript's `||` (treats empty string as missing) and silently dropped items where both fields were absent. The spec said neither. Three independent reconstructions of the spec from the code reliably split the rule into two specs — one for the preference, one for the unwanted "drop on empty" behavior.

- **A filter rule whose central condition was perfectly coherent — but that surrounded itself with unstated operational behavior.** Error handling, pagination, partial-failure recovery, and unconfigured-source fallback were all in the code, none in the spec. Reconstructions from the code uniformly surfaced all four as missing requirements.

- **A cluster of sibling specs** that together described one feature, with no spec cross-referencing the others. A blind reader of any one spec under-implemented; a blind reader of the code reconstructed the whole cluster. The fix is cross-references between siblings, not within-spec rewording.

- **A genuinely coherent case** — a four-branch scoring matrix over a bounded output domain. Both directions matched. No edits recommended. Bounded exhaustive enumeration is a coherence-friendly spec shape.

### Direction asymmetry

Across the sample, the **code-to-spec** direction was the more reliable drift detector — low variance across runs, consistent findings. The **spec-to-code** direction disambiguated whether a finding was a real ambiguity (different agents picked different answers) or just an arbitrary implementation choice that didn't need spec coverage. Both directions together carry more signal than either alone — that's the "bidirectional" bit.

### Side benefit

In the same sample, five of the six EARS were still marked as gaps (`[ ]`) in their spec file even though the code had already implemented them — and most of those implementations also lacked `@spec` annotations linking back to the spec. The audit incidentally surfaces stale status markers and missing annotations along the way — small wins for `arrow-maintenance` coherence even when the spec-and-code drift itself turns out negligible.

### A note on sample size

This is one early dataset on one codebase. The shapes of drift listed above are robust across other smaller samples we've run, but the **5-of-6** rate isn't a guarantee — different codebases will hit different mixes. Treat it as a sense of what the audit can catch when it's working, not a promise of what it will catch every time.
