# LLD: lid-experimental Plugin

**Created**: 2026-04-23
**Status**: Skeleton — no experiments yet

## Context and Design Philosophy

The `lid-experimental` plugin is the opt-in, third plugin in the LID distribution. It houses novel capabilities under evaluation for promotion into core: new intent-coherence mechanisms today, other experimental behaviors over time. It is the sanctioned escape valve for LID's minimum-system discipline — the place where new surface is allowed to exist *because* it carries a known retirement path.

The plugin exists to resolve a specific tension. Goal 2 of the HLD ("Stay a minimum system") aggressively resists new commands and skills; the *Minimum-system discipline — the why* design decision explains why. But real progress in a methodology like LID requires somewhere to try ideas under realistic conditions, not just in design discussion. The experimental plugin is that place: novel surface lands here first, must earn community adoption, and is either promoted into a core plugin or removed.

Three properties make the separation load-bearing:

1. **Opt-in installation** — users who want LID's minimum surface ignore the plugin and pay no runtime cost. Users curious about a candidate capability install it deliberately.
2. **Same arrow obligation as core** — experiments are not exempt from coherence. Each experiment walks HLD → LLD → EARS → tests/evals → code, anchored in this LLD. Experimental status is a marker on the surface, not a relaxation of design rigor.
3. **Explicit lifecycle** — every experiment has two known exits (promotion, retirement). Indefinitely-experimental status is a smell.

Terms like *arrow*, *segment*, *cascade*, *coherence*, and *intent component* are defined in the HLD's Glossary.

## HLD Trace

This LLD traces upstream to:

- **Architecture § Plugins** — names `lid-experimental` as the third plugin alongside `linked-intent-dev` and `arrow-maintenance`, opt-in, with each experiment rooted in this LLD.
- **Key Design Decisions § Experimental features as a separate plugin** — the canonical statement of the separation rationale, arrow obligation, promotion-or-retirement lifecycle, and the aspirational community-feedback commitment.
- **Key Design Decisions § Minimum-system discipline — the why** — names the experimental plugin as the destination for surface that survives the "can existing surface absorb this?" test. This LLD is how that placement is realized.
- **Goal 2 — "Stay a minimum system."** — experiments are how LID grows without breaking this goal. Promotion into core only after community adoption and value stories.
- **Goal 4 — "Dogfood itself — falsifiably."** — experiments installed in this repository participate in the dogfooding signals (process and coherence) along with core plugins.

## Component Variant

The plugin itself is structural — it is a container for experiments rather than a single skill. Each *experiment* inside the plugin chooses its own variant from the three defined in HLD § The arrow for LID itself:

- **Pure-prose experiment** — guides agent behavior without a definite procedure. Arrow: `HLD → this LLD → experiment subsection / sub-LLD → SKILL.md + references/`. Verification by dogfooding.
- **Behavioral experiment** — produces verifiable project-state changes when invoked. Arrow: `HLD → this LLD → experiment subsection / sub-LLD → EARS → evals + SKILL.md + references/`.
- **Dual-mode experiment** — ambient + command. Same arrow as behavioral for command-mode assertions; ambient mode verified by dogfooding.

The variant is declared per experiment, not per plugin. Most early experiments are expected to be behavioral or dual-mode (intent-coherence mechanisms typically produce auditable state changes), but the plugin does not constrain this.

**Where experiments are documented.** Two acceptable layouts, chosen per experiment:

- **Inline** — small experiments with a tight scope are documented as a section within this LLD, with their own EARS file under `docs/specs/lid-experimental-{experiment-name}-specs.md`.
- **Sub-LLD** — experiments substantial enough to warrant their own design doc get `docs/llds/lid-experimental/{experiment-name}.md` and a corresponding spec file. This LLD then carries only a one-paragraph entry pointing to the sub-LLD.

The choice is a judgement call at the time the experiment is added; the default is inline until the experiment outgrows it.

## Plugin Structure

The plugin lives at `plugins/lid-experimental/`:

- `.claude-plugin/plugin.json` — manifest. Description must communicate the opt-in, evaluation-focused nature ("Opt-in plugin for novel LID capabilities under evaluation. Install only if you want to try experiments and provide feedback.").
- `skills/{experiment-name}/` — one directory per experiment, each a self-contained skill.
  - `SKILL.md` — the experiment's prose. Header includes an `Experimental:` block stating: candidate-for (which core plugin would receive it on promotion), open-questions, and a feedback-link placeholder.
  - `references/` — per-experiment reference material.
- `commands/` — command stubs only when the experiment exposes a slash command.
- `evals/` — per-experiment eval suites for behavioral experiments.

**No shared code or shared state across experiments.** Each experiment is independent so that promotion or retirement is a self-contained operation: removing an experiment removes only its own subdirectory and spec file, with no cross-experiment cleanup.

## Lifecycle

### Adding an experiment

When a candidate capability has survived the "can existing surface absorb this?" test and is ready to be tried:

1. Choose the documentation layout (inline vs. sub-LLD) and add the experiment's design.
2. Write the EARS spec file (behavioral and dual-mode experiments) with the standard `{FEATURE}-{TYPE}-{NNN}` ID pattern; the `{FEATURE}` segment must be the experiment's name to keep its specs separable for promotion or retirement.
3. Write the skill prompt, references, and (for behavioral / dual-mode) the eval suite.
4. Update the experiment's `Experimental:` SKILL.md header with the candidate-for plugin and open questions.
5. Announce the experiment with a brief published note inviting community adoption and feedback. Channel TBD — see *Community feedback* below.

The standard arrow cascade applies — new experiments enter through HLD → this LLD (or a sub-LLD) → EARS → tests/evals → code, in that order, with the same stop-and-iterate gating as core work.

### Promotion

An experiment is a candidate for promotion when:

- It has accumulated **community adoption** — concrete users who have installed the experimental plugin and used the experiment in their own projects.
- Those users have produced **real-world value stories** — accounts of how the experiment changed their LID practice for the better, specific enough to recognize in another project.
- Its design has stabilized enough that further iteration is expected to be incremental, not structural.

Promotion is a structural change to the receiving core plugin (`linked-intent-dev` or `arrow-maintenance`) and follows the standard LID workflow:

1. Update the receiving plugin's LLD to absorb the experiment.
2. Move EARS specs from the experiment's spec file into the receiving plugin's spec file. Spec IDs typically renumber to fit the receiving plugin's namespace; arrows in code that referenced the old IDs are updated in the same change.
3. Move the skill (or fold its behavior into an existing skill — minimum-system applies even on promotion).
4. Remove the experiment from `plugins/lid-experimental/` and from this LLD entirely. No deprecation marker, no migration path: mutation, not accumulation.

The change is one merge, not a phased rollout. Users on the prior version of `lid-experimental` who do not update simply continue to have the experimental version; users who update receive the promoted version in core and may uninstall `lid-experimental` if it carries no remaining experiments they care about.

### Retirement

An experiment is retired when:

- It has not accumulated adoption after a reasonable trial (informal, judgement-based — no formal time bound), **or**
- The fast-moving tooling layer (agent harness, IDE, model capability) has absorbed the capability the experiment was probing, making LID's version redundant per minimum-system reasoning, **or**
- Iteration has revealed a structural problem with the approach that cannot be repaired within experimental scope.

Retirement removes the experiment's directory, EARS spec file, and entry in this LLD in a single change. No deprecation, no historical preservation in the docs tree — the commit history is the only record. This matches HLD's *what is currently here is the truth* tenet.

### Long-running experiments

An experiment that is neither promoted nor retired after a long period is itself a signal that something is wrong — the design hypothesis it embodies is not being validated *or* falsified. The expected response is to articulate why the experiment is in this state and either fix the hypothesis (re-frame the experiment with clearer success criteria), or retire it. Indefinite experimental status without a working hypothesis violates the spirit of the lifecycle.

## Community Feedback

The HLD commits the project to publishing each experiment and actively seeking community feedback. The mechanism is **aspirational at this stage** and will be filled in here as the first experiments land. Open questions:

- **Channel.** GitHub Issues / Discussions on this repo? A dedicated label? An external survey? A periodic call-for-feedback note in releases?
- **Cadence.** Push (publish-and-wait) vs. pull (active outreach to known LID users)?
- **Aggregation.** How feedback is collected, summarized, and surfaced when promotion-or-retirement is being evaluated.

These questions are deliberately left open in the skeleton so the first experiment can shape the answers in light of what kind of feedback it actually needs. The placeholder commitment in the meantime: every experiment that lands in this plugin is announced in some publicly-visible way, and the project is reachable for response.

## Active Experiments

### bidirectional-differential

Audits EARS↔code coherence by running two fresh `claude -p` sessions in parallel — one reconstructs code from the EARS (A-direction), the other reconstructs the EARS from stripped code (B-direction) — then classifies drift from the relationship between A's diff and B's diff. Surfaces operational-halo drift, decomposition gaps, missing sub-decisions, and unstated invariants that formal/structural engines (type systems, CodeQL, test-witness, LemmaScript) cannot see. Hard dependency on `arrow-maintenance`: audit records live in a reserved sibling subtree at `docs/arrows/experiments/bidirectional-differential/` so retirement is `rm -rf` and promotion is a single move.

- **Sub-LLD**: `docs/llds/lid-experimental/bidirectional-differential.md`
- **EARS**: `docs/specs/lid-experimental-bidirectional-differential-specs.md` (prefix `BIDIFF`)
- **Skill**: `plugins/lid-experimental/skills/bidirectional-differential/`
- **Candidate promotion target**: `linked-intent-dev` (primary — the audit's natural home is Phase 6 integration) or `arrow-maintenance` (secondary — if audit-record-maintenance dominates implementation).

## Spec Coverage

This LLD is structural and currently has no behavioral surface of its own — the plugin is a container, and EARS coverage attaches to individual experiments rather than the container. Once experiments are added, spec files are per-experiment (`docs/specs/lid-experimental-{experiment-name}-specs.md`) and tracked from the experiments' design sections.

If, over time, the container itself acquires behavioral surface (for example, an experiment-listing command, or shared eval scaffolding), an EARS file `docs/specs/lid-experimental-specs.md` is created at that point.

## Open Questions

- **Plugin manifest description.** The opt-in nature must be unambiguous in the marketplace listing. Final wording deferred to first experiment so the description can give a concrete example of what "experimental capabilities" actually means.
- **Eval scaffolding.** Whether `lid-experimental` provides any shared eval helpers (e.g., baseline-vs-experimental run pairs) or each experiment owns its evals end-to-end. Default for now: each experiment owns its evals; revisit if duplication becomes painful.
- **Marketing-site treatment.** Whether the experimental plugin gets its own page, a section on an existing page, or no surface (deliberately undermarketed, found through the install flow only). Cascades from this LLD to `marketing-site.md` once decided.
