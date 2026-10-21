---
parent: high-level-design
prefix: LID
---

# Sub-HLD: linked-intent-dev Plugin

## Context and Design Philosophy

The `linked-intent-dev` plugin is the mandatory core of LID. It translates the methodology described in the High-Level Design (HLD) into three skills: a pure-prose workflow skill (`linked-intent-dev`) that shapes how the agent approaches code changes, a behavioral skill (`update-lid`) that bootstraps and maintains project state, and a behavioral skill (`lid-coach`) that reviews a project's LID usage against LID's principles and produces improvement recommendations.

This is the `LID` sub-HLD: it owns no EARS itself and parents three leaf LLDs, one per skill —

| Leaf | Segment | Skill |
|---|---|---|
| [`core/core-design.md`](core/core-design.md) | `LID-CORE` | the pure-prose workflow skill |
| [`update-lid/update-lid-design.md`](update-lid/update-lid-design.md) | `LID-UPDATE` | the behavioral bootstrap/maintenance skill |
| [`lid-coach/lid-coach-design.md`](lid-coach/lid-coach-design.md) | `LID-COACH` | the behavioral principle-review skill |

The three skills share a body of plugin-level design — mode detection, spec-ID format, the LID-on-LID linkage inversion, `index.yaml` update mechanics, the eval-metadata schema, and capability flags. Those concerns live in this sub-HLD and are referenced from the leaves rather than restated in each. Skill-specific design lives in the corresponding leaf.

**A note on actors.** Throughout this plugin's docs, "the skill" refers to the prose guidance contained in a `SKILL.md`. The skill does not act on its own — it is content the agent consults. When a doc says "the skill surfaces X" or "the skill warns," the mechanism is: the agent, after consulting the skill, performs the surfacing or warning in the assistant turn it produces. The skill is the instruction; the agent is the actor.

Two design constraints shape the plugin:

- **Minimum surface.** The plugin exposes one pure-prose skill (`linked-intent-dev`) and two behavioral skills (`update-lid`, `lid-coach`). Any capability that can live inside those three is absorbed into them rather than given its own entry point. Each skill's separation rationale is documented in its leaf LLD.
- **Describe, do not dictate.** The leaf LLDs describe the *behavior* each skill should produce. They do not prescribe the exact wording of skill prompts. The prompt is the implementation; its phrasing is free to change as long as the described behavior is preserved and the EARS specs pass.

This sub-HLD describes intent; the `SKILL.md` files and references under `plugins/linked-intent-dev/` are the compiled outcome. Terms like *arrow*, *segment*, *drift*, *coherence*, and *cascade* are defined in the HLD's Glossary section.

## Plugin Structure

The plugin lives at `plugins/linked-intent-dev/` with this shape:

- `.claude-plugin/plugin.json` — Claude Code plugin manifest (name, version, skills listing). Its `version` is the canonical LID conventions version (see the HLD's Versioning note).
- `skills/linked-intent-dev/` — the pure-prose workflow skill. Specified in `docs/intent/linked-intent-dev/core/core-design.md`.
  - `SKILL.md`
  - `references/` — supporting reference docs (EARS syntax, LLD template, HLD template, decision-doc template, capability flags).
  - `evals/` — the scenario evals for the moments with a checkable output.
- `skills/update-lid/` — the behavioral bootstrap/update skill. Specified in `docs/intent/linked-intent-dev/update-lid/update-lid-design.md`.
  - `SKILL.md`
  - `references/` — instruction-file template fragments keyed by mode.
- `skills/lid-coach/` — the behavioral principle-review skill. Specified in `docs/intent/linked-intent-dev/lid-coach/lid-coach-design.md`.
  - `SKILL.md`
  - `references/` — situational material: follow-up turns, conversational guidance, sampling, and the LID FAQ.

No `commands/` directory. Per Claude Code's skills model, an identically-named skill is already directly invokable as `/skill-name`, so a separate command stub would be redundant surface (and would be shadowed by the skill anyway). Users invoke `/linked-intent-dev`, `/update-lid`, and `/lid-coach` directly against their skills.

**Size and line limits.** Every `SKILL.md` body stays under 50 KB, and no line in a shipped skill or reference file runs past 2,000 characters. Some agent harnesses cap what one tool call returns: opencode, for one, cuts any tool output past 51,200 bytes (its skill loader included) and any line past 2,000 characters when reading a file, without the model seeing more than a short notice. A skill over those limits silently loses its tail, or the end of its longest paragraphs, on those harnesses. What every invocation needs stays in `SKILL.md`; material a skill needs only in some situations moves to `references/`, which harnesses page through like any file. Long paragraphs break across lines rather than running on one.

The plugin intentionally does not bundle scripts. Everything the skills do is expressed in prompts and references; there is no code layer between the skill and the agent's tool use.

## Mode Detection Mechanics

The project's mode and version live in its **agent-instructions file** — `AGENTS.md` (the canonical cross-tool convention; under Claude Code a `CLAUDE.md` symlink alias resolves to it) or `CLAUDE.md` where a project predates the convention. This plugin's skills read whichever file the project presents — `AGENTS.md` if present, otherwise `CLAUDE.md` — and never branch on which host they run under. Throughout this plugin's LLDs and skills, *the instruction file* names this file. (The bootstrap-writing rule — create `AGENTS.md` canonical plus a `CLAUDE.md` alias, no host detection — lives in the `update-lid` LLD, the skill that writes it.)

Mode is detected by a single parse of the instruction file. The skill reads the `## LID` block and takes the value of its `- Mode:` bullet, which is one of `Full` or `Scoped`. Matching is case-insensitive on the mode name; whitespace around the bullet is tolerated.

If the `## LID` block or its `- Mode:` bullet is missing, malformed, or names an unrecognized mode value, the skill defaults to Full LID and surfaces a one-line warning during the next `linked-intent-dev` consult asking the user to add a valid `- Mode:` bullet explicitly. Full and Scoped are close enough in behavior that defaulting to the more rigorous one carries negligible cost. The skill does not silently write a marker — doing so would let a misconfigured project drift for sessions before anyone notices.

**Multiple instruction files.** In monorepos or nested projects, the agent's harness typically resolves which instruction file is in scope. The skill trusts that resolution. Absent harness guidance, the skill uses the instruction file nearest to the files under review — walking up from the file's directory until one is found.

## Spec ID Format

An EARS spec ID is the path from the root of the design tree to the leaf segment that owns the spec, concatenated segment-by-segment and ending in a number. A flat project is `FEATURE-NNN` (e.g., `LID-UPDATE-003`). Each level of nesting prepends one more segment of the path: `PEVAL-RUN-014` is spec 14 of the `run` leaf under the `peval` root; `PEVAL-PERF-LOAD-003` adds another level for a `load` leaf under a `perf` sub-HLD. A leaf MAY append one within-leaf type/area facet before the number (`AUTH-UI-001`, `ENGINE-LEDGER-001`); the facet groups specs inside a leaf and is not a tree boundary. (`LID-CORE-001` is path-concatenation — the `core` leaf under the `LID` sub-HLD — not a facet.) The prefix *is* the spec's position in the tree, so `grep PEVAL-PERF` gathers that whole subtree by construction. Format rules:

- **Position-encoding prefix.** The ID's prefix is the root-to-leaf path; a prefix grep gathers every spec in the named subtree, and one `prefix:`/`index.yaml` lookup resolves an ID to its owning design doc.
- **Global uniqueness.** Two specs cannot share an ID anywhere in the project. Path-concatenation gives this for free — two leaves at different positions necessarily have different prefixes.
- **Grep-friendliness.** IDs use uppercase letters, digits, and hyphens only — no other characters — so `grep "PEVAL-RUN-014"` across the repo finds every annotation, test, and spec file that references it.
- **ID stability.** Once assigned, an ID does not move under ordinary growth — adding or refining specs within a segment never renames existing IDs. The prefix changes only under a deliberate, tooled re-parent or rename of a segment, which rewrites the affected IDs and their annotations together. Deletion is permanent; the number is not recycled into a future spec, because doing so would collide with git-history references to the old ID.
- **Disambiguation on conflict.** When the skill is about to draft a new spec whose natural path prefix already exists for an unrelated segment, it surfaces the collision and asks the user how to disambiguate the position rather than silently picking.

## Spec-File Header Format (LID-on-LID Linkage Inversion)

In LID-on-LID, EARS spec files carry the downstream artifact pointer, because `SKILL.md` bodies cannot host `@spec` annotations without bending runtime behavior. Spec file header format:

```markdown
# {Feature} Specs

**LLD**: docs/intent/{path-to-leaf}.md
**Implementing artifacts**:
- plugins/{plugin}/skills/{skill}/SKILL.md
- plugins/{plugin}/skills/{skill}/references/{file}.md

---

## {ROOT-TO-LEAF-PATH}-001

WHEN {condition} THEN the system SHALL {behavior}. [x]

...
```

The `LLD` line points upstream to the authoritative design doc. The `Implementing artifacts` list points downstream to the compiled prompt files. An agent walking from a SKILL.md file to its specs does so by consulting this list in the relevant spec file, not by reading the SKILL.md body.

This inversion applies **only** to LID-on-LID. Normal LID projects — where code is the artifact — follow the standard convention: `@spec` annotations live in code and tests, and spec files do not carry downstream artifact pointers.

## Eval Metadata Conventions

For behavioral skills, `evals/evals.json` and per-eval `eval_metadata.json` carry spec linkage at the assertion level. Schema extension beyond skill-creator's defaults:

```json
{
  "eval_id": 0,
  "eval_name": "bootstraps-fresh-project",
  "prompt": "Set up LID in this empty directory",
  "assertions": [
    {
      "text": "docs/intent/ directory exists",
      "spec_ids": ["LID-UPDATE-002"]
    },
    {
      "text": "the instruction file contains a '## LID' block with '- Mode: Full'",
      "spec_ids": ["LID-UPDATE-004", "LID-UPDATE-007"]
    }
  ]
}
```

An eval may add a scripted second turn as `"follow_up": {"prompt": "...", "assertions": [...]}`: the harness sends the follow-up prompt in the same session after the first response, and grades its assertions against the reply. It exists for behavior a skill reserves for later turns, such as the coach's remedies, which its first report does not give.

`spec_ids` is per-assertion, not per-eval — different assertions in one eval typically verify different specs. The grader produces `grading.json` with the standard `text`/`passed`/`evidence` fields; `spec_ids` travels with the assertion through grading so the benchmark viewer can display which specs an eval actually exercised.

Coverage audit: every behavioral EARS spec should appear in at least one assertion's `spec_ids` across the eval suite. The `arrow-maintenance` overlay runs this audit when present. The pure-prose `linked-intent-dev` workflow skill (`LID-CORE`) is verified mainly by dogfooding: its behaviors are guidance the agent consults across a whole change, not one checkable run. It carries a small suite of **scenario evals** for the moments that do produce a checkable output, such as whether a decision doc is offered or withheld when the user settles a choice. Those use the same schema, usually with a `follow_up` turn for the user's side of the exchange. The coverage audit applies to the behavioral leaves (`LID-UPDATE`, `LID-COACH`) and to the core specs a scenario eval exercises; the rest of `LID-CORE` stays outside it.

**Models tested.** Each `evals.json` carries a top-level `tested_with` list recording the runs its results rest on: the exact model ID, the run date, which evals ran, and the with-skill pass count — e.g. `{"model": "claude-sonnet-4-5", "date": "2026-09-25", "evals": "0-10", "passed": "48/51"}`. A run executed outside Claude Code also names its agent harness and version — e.g. `"harness": "opencode-ai@1.18.32"` for the alternate-model runner (`docs/intent/alt-model-evals/`); an entry without `harness` ran under Claude Code. Each entry names its reasoning effort — e.g. `"effort": "medium"` — because the same model at a different effort is a different configuration; LID's own runs pin `medium` (see *Capability Flags*). Evals name models, never relative tiers ("floor", "frontier", "strong"): which model counts as strong changes as models change, and an exact ID stays true. A suite's results are a claim about the models it names; every other model is unsampled (HLD tenet *Design for the pair, not the model*). An empty list means no run is on record.

## Capability Flags

LID's guidance runs on whatever model the user pairs it with. Most of it — phase discipline, restraint, the stops — holds on any model. Some judgment does not: eval evidence can show some model configurations reliably missing a kind of judgment that others catch, where rewording the skill does not close the gap. A **capability flag** records such a gap so that LID brings the user in on that judgment rather than letting the model proceed on it alone (HLD tenet *Design for the pair, not the model*).

**Where the list lives.** One file, `skills/linked-intent-dev/references/capability-flags.md`. Any LID skill whose work touches a flagged area reads it — the core workflow, `lid-coach`, and the `review-depth` experiment each specify how in their own LLDs.

**Entry shape.** Each flag names:

- **Area** — the kind of judgment the flag covers, by its name in the core LLD's list (see *What still reaches the human*), with a line describing it so a model can recognize it while working (e.g., *tenet or goal conflict: noticing that a design's mechanism works against one of the project's own tenets or goals*).
- **Configurations** — what the flag covers, each an exact model ID at a reasoning effort. Each row also records the harness the runs used, the model's release date, and its vendor size tier (small / mid / large; e.g., Haiku / Sonnet / Opus) as data, not as a key: across vendor lines neither predicts which models miss a judgment, though within one line newer and larger models have done no worse (see *Self-matching*), and recording them lets a pattern be found later if one exists.
- **Evidence** — fixtures, runs per model, and the date, with one row per configuration tested: the exact model ID, the harness, the reasoning effort, and the pass rate. Rows for configurations that passed are listed too, so a model can find itself whether or not it is flagged.

**Layout.** A model's question is what applies to it, so the file opens with a lookup: each tested model at its effort, with the flags and tendencies that apply, plus any untested model the maintainers know a tested one covers. What each flag and tendency means and what to do follow, and the evidence tables come last.

**Self-matching.** A model finds its row by the identity its context states: a line its harness adds naming the model it runs, as Claude Code and opencode do, or the user saying which model they run. A display name counts as well as an ID when it names exactly one model (`Claude Opus 5.5` is `claude-opus-5-5`). Text that is not about the running model, such as a file the agent read, states nothing, and neither does persona text that names only a vendor ("you are a Claude agent"); statements that disagree count as no statement. The model reads a stated ID and the list's IDs alike past route, vendor, and cloud-region prefixes, date stamps, provider revision tags, and dot-or-dash spelling, keeping every word that names the model, its size, or its variant: `openrouter/google/gemini-4-argon` is `gemini-4-argon`, `us.anthropic.claude-sonnet-4-5-20250929-v1:0` is `claude-sonnet-4-5`, and `z-ai/glm-5.3-flash` stays apart from `z-ai/glm-5.3`. The model's own belief about what it is never places it in a row that lifts a flag: models rarely know their exact version, guess an older sibling when they do guess, and open models often believe they are Claude or GPT. Belief may still add caution: a model that believes it is a model the list flags takes that row's flags.

When no row matches its ID, a model places itself by a tested relative. A *line* here is one vendor's model under one name across releases (Sonnet, GPT Sol, GLM Flash), and a *generation* is one release across its sizes (Claude 5.5's Haiku, Sonnet, and Opus). The lookup may list an untested model as covered by a tested one, which settles relations a model could not judge alone, and such a listing comes first. Otherwise a model that can tell from its ID that it is a later release in a tested model's line takes the row of the nearest such model; failing that, a model that can tell it is larger than a tested model of its own generation takes the row of the nearest such model. Either way it takes flags and tendencies alike. Within each vendor line tested, newer and larger models have done no worse on a flag than the ones before them, while smaller siblings have done worse, so inheritance runs only from older or smaller, and from the model's own line first: a smaller sibling can sit well below it. When the context states no identity, or nothing places it, it treats every flag the list defines as applying. Both errors cost the user: a flag raised needlessly wears on their patience with the tool, and a flag skipped where it was needed costs their project quality. Where the two trade off, the list errs toward the flag (HLD tenet *Lean toward the human's attention*). As a model is tested, it gains a row of its own, flagged or passing.

**What a flag does.** It changes who checks the judgment, not what the model does: the model still does its best work in the area, then names the area to the user once, plainly, and asks them to check that judgment themselves. It is a routing instruction, not a disclaimer — no apology, no hedging of the rest of the work.

**Tendencies.** Evidence can also show a configuration leaning the wrong way on a behavior that already reaches the user, such as offering a decision doc for a choice a row covers. The user already sees that behavior and decides it, so a flag would route nothing. The list records it as a **tendency** instead: a model whose configuration is listed tells the user once, when the behavior comes up, that models configured like it lean that way, so the user can weigh it. A tendency meets the same evidence bar as a flag and changes nothing about who decides.

**Evidence bar.** A flag enters the list only when all three hold:

1. At least 10 completed runs per model configuration on each fixture. A run its host cuts short, by a timeout or a harness error, is a transient failure, not a result: the list records what the model does, and the same model is served by other hosts. Such a run is rerun unless no outcome of the missing runs could change the result.
2. The pass-rate gap between the flagged configuration and configurations that pass exceeds the spread between repeated identical runs on one model, measured by a noise study on the same fixtures. Strong configurations score 9 or 10 of 10 across repeated batches, so a pass rate of 70% or lower on a fixture (7 of 10) counts as a miss: the line sits just below that spread rather than well beyond it, so a borderline gap is resolved toward the flag (HLD tenet *Lean toward the human's attention*).
3. The configuration misses on at least two fixtures.

LID's own evidence runs pin reasoning effort at `medium`, the most common default across current flagship models (Claude Code's default for the newest Claude models; OpenRouter's for current GPT and Gemini), so the table describes what a user on default settings most likely runs. Effort moves results as much as the model does, so a row names its effort, and the same model at a different effort is a different row. No harness tells the model its effort, so a model takes a row's effort as its own unless its context states a lower one: medium is the lowest effort commonly used for coding work, so a passing row at medium describes a user on default or higher settings. A model whose context states a lower effort is not covered by a passing row at medium and treats every flag as applying. Efforts rank none, minimal, low, medium, high, xhigh, max; a stated effort off that scale, such as a token budget, counts as unstated. Effort never decides whether a model is placed: the model is placed by its identity, a stated effort chooses among that model's rows when the list has several, and the comparison applies to whichever row places it, its own or a relative's.

**Evidence runs exclude the capability subsystem.** A run that produces evidence for the list measures the model's own judgment, so the skill text the run gives the model carries no trace of the list. The run's copy of the skills drops `references/capability-flags.md` and every passage that mentions the list or its flags, wherever the model could read it: the skills, their references, the vendored workflow doc, the plugin's changelog. Files the run never gives the model, such as eval definitions and earlier run output, stay as shipped like everything else: eval definitions hold the assertions the run is graded by, so editing them would change what is measured. The subsystem is a handful of passages, so they are removed from the copy by hand. Before any run starts, a case-insensitive search for `capability` over the parts of the copy the model is given finds only uses unrelated to the list, and a diff of the whole copy against the commit it came from shows nothing changed but those passages. The run's results are recorded against that commit.

A configuration leaves a flag when a rerun at that configuration no longer clears the bar.

## Decisions & Alternatives

These are the decisions shared across the plugin's three skills. Skill-specific decisions live in each leaf LLD's own Decisions & Alternatives section.

| Decision | Chosen | Alternatives Considered | Rationale |
|---|---|---|---|
| Skill size and line length | `SKILL.md` body under 50 KB; no line over 2,000 characters; situational material in `references/` | No limit (each harness's problem); a smaller hard budget; splitting skills into more skills | Measured: opencode's skill tool cut the last 6 KB of a 57 KB `lid-coach` body, and its file reader cut the end of a 3,136-character principle line, with no visible loss to the model. Limits matching the strictest harness observed keep every harness on the full skill. Splitting a skill adds surface (*Minimum surface*); references keep one skill while letting harnesses page. |
| Spec ID format | Path-concatenated prefix — the root-to-leaf path of the owning segment, one segment per tree level, with an optional within-leaf type facet | Fixed two-segment format (`FEATURE-TYPE-NNN`); loose namespaces decoupled from position; GUID; hierarchical numeric only | The prefix encodes position, so a single grep gathers a subtree and an agent can place any ID from the ID alone. Fixed segments cannot express depth. Position-decoupled prefixes need a second structure (frontmatter) to locate a spec. GUIDs break grep-friendliness. (See `docs/decisions/namespace-structure.md`.) |
| EARS spec linkage direction for LID-on-LID | Spec file header points to artifacts (inverted) | `@spec` annotations in SKILL.md body; frontmatter `specs:` field | Prompt bodies cannot host annotations without instruction contamination. Spec-as-authoritative-end is philosophically cleaner than either alternative. |
| Capability-flag keying | Exact configuration — model ID at a reasoning effort — with harness, release date, and size tier recorded as data, not keyed | Model class by size tier and release year; exact model IDs without effort; a single "Sonnet-level" capability floor; no flags, rewording the skill until the gap closes | Measured across 13 configurations, the misses followed neither size nor date: `claude-haiku-5-5` (small) passed every test project while `claude-sonnet-4-5` (mid) is flagged twice, and within one vendor line `claude-haiku-4-5` misses what `claude-haiku-5-5` catches. Reasoning effort moved one model as far as the model choice did (`claude-sonnet-4-5` on a tenet-conflict project: 7 of 10 with thinking, 0 of 10 without). A single floor goes stale and names no judgment. Rewording was tried against a detection gap: pass rates did not move, and wording aimed at one model regressed other behaviors. How a model with no exact row places itself is its own decision (next row). Harness is not a key: once one harness's file-reading truncation was fixed, the same model scored alike under Claude Code and opencode, and a model often cannot name its harness. Size and date are kept as data: across lines they predict nothing, and within a line the model's stated ID already places it among its relatives. |
| How a model places itself in the list | By the identity its harness or user states, as an ID or a display name naming one model, normalized past prefixes, date stamps, and revision tags; with no row, the row the lookup names as covering it, else the nearest tested earlier release in its own line, else the nearest tested smaller model of its generation; otherwise every flag applies. A row's effort is taken as the model's own unless its context states a lower one | The model's own belief about its identity; IDs only, not display names; exact matching only, with every untested configuration taking all flags; the union of both kinds of relative's flags; a maintained table of every model's relatives; the user declaring model and effort in the project's instruction file | A stated identity is the one reliable signal: in-context identity overrides a model's trained-in belief, while that belief rarely knows the model's version and, for open models, often names another vendor. DeepSeek behind a gateway answered "Claude Opus 4.8", a row with no flags, while the line its harness stated read `deepseek-v4-pro`. So belief may add a flag but never lift one. A display name places a model as surely as an ID when only one model carries it, and two of the harnesses checked state only a display name; a statement that is not about the running model, or two that disagree, place nothing. Of twelve harnesses checked, four state an exact ID, Claude Code and opencode among them, and none states effort (`docs/research/harness-model-identity.md`). Exact matching on model and effort would therefore leave every passing row unused and flag every model always, and a flag on every model teaches users to skip flags, spending the attention flags exist to direct. Within each vendor line tested, newer and larger models did no worse on any flag than earlier ones (Sonnet 4.5 → 4.6 → 5.5, Haiku 4.5 → 5.5, Opus 4.8 → 5.5, GPT-5.6 Sol → 6.1 Sol), while smaller siblings did worse (GLM 5.3 Flash beside GLM 5.3, GPT-5.6 Terra beside Sol), so inheritance runs only from older or smaller. The model's own line comes before its generation: an earlier release shares its name and lineage and the line pattern held in four lines, while a smaller sibling can sit far below it (GPT-5.6 Terra beside Sol). Taking the union of both relatives' flags would raise flags that both patterns say the model does not need. Inheritance carries tendencies too. In both tested lines where a model leaned toward offering decision docs, the newer or larger model did not (Opus 4.8 → 5.5, GLM 5.3 Flash → GLM 5.3), but two lines do not show that a lean always fades, so an untested model keeps its relative's tendencies until its own run shows otherwise. Nor does inheritance rule out a lean the relative lacked; only testing the model shows one. A table of every model's relatives cannot keep pace with releases, so the lookup records coverage where maintainers know it and the model judges the rest from its stated ID. Medium is the lowest effort commonly used for coding work, so assuming it errs toward the user's actual setup, and a stated effort that cannot be ranked is treated as unstated for the same reason; a declared effort goes stale as users change effort between sessions. |
| Where a miss starts | A pass rate of 70% or lower on a fixture (7 of 10), on at least two fixtures | 60% or lower (6 of 10); 80% or lower (8 of 10); requiring the two configurations' 95% intervals not to overlap | At 10 runs, a configuration that truly passes 9 runs in 10 scores 7 or lower on a fixture about 7% of the time, so it misses two of two fixtures by chance about 0.5% of the time and two of four about 3%. At 80% those chances rise to about 7% and 29%: where four fixtures stand behind a flag, one strong configuration in four would be flagged on luck. At 60% they fall to about 0.02% and 0.1%, but a configuration scoring 7 of 10 on two fixtures, outside every strong configuration's measured spread, would pass without a word. Non-overlapping intervals at 10 runs need a score of 4 or lower against a 10, so only gross gaps would flag. 70% resolves the borderline toward the flag (HLD tenet *Lean toward the human's attention*) while keeping chance flags rare. |
| Runs a host cuts short | A timeout or harness error is a transient failure: not graded, not recorded, and rerun unless no outcome of the missing runs could change the result | Count a timeout as a miss; report timeouts beside the pass rate; always rerun to 10 completed runs | The list records what a model does, and the same model is served by several hosts, so a host's slowness or a stalled stream says nothing the list should keep. A single timeout cannot tell a model that loops from a slow host, and a model that truly loops keeps timing out on reruns, which the rerun rule surfaces. Rerunning when no outcome could change the result buys no information. |
| A lean in a behavior the user already decides | Recorded as a tendency, mentioned to the user once when the behavior comes up | A flag; leaving it out of the list | A flag routes a judgment to the user, but here the user already makes the call, so a flag would change nothing. Leaving it out hides something the user can use: a model offering decision docs too readily nudges a user who tends to accept what is offered. |
| The capability subsystem during evidence runs | Removed from the run's copy of the skills by hand, then checked before any run by a search for the subsystem's terms over the text the model is given and a diff of the whole copy against the source commit; results recorded against that commit | Run the skills with an empty list, relying on their own rule to stay silent when nothing is listed; run them as shipped, list and all; mark each passage in the shipped skills so the runners can cut it; commit each stripped copy under a tag so its exact text can be checked out | An empty list is not silent in practice: in runs with nothing listed, models still applied the rule for configurations with no row and raised tenet checks, the very judgment being measured (17 of about 1,000 runs, most of them from two small models). Running as shipped is worse once rows exist, since every untested model is told all flags apply. Markers would put eval scaffolding into every shipped skill (*Minimum surface*) and would still need the search to confirm the cut; the subsystem is small enough that removing it by hand and checking with the search is reliable. The search catches a passage left in where the model could read it; the diff, over the whole copy, catches anything else the cut disturbed, eval definitions included. A tag per stripped copy would add a ref to the repository every evidence round only to guard against a cut those two checks already cover. |
| What a capability flag does | Brings the user in on the flagged judgment | Skip the area on flagged configurations; a general "results may vary" disclaimer | When judgment depends on the model, bring in the user: the pair is what executes LID, and the user supplies what the model misses. Skipping drops the check entirely; a disclaimer moves no work and wears on the pair's working relationship. |
| Recording eval models | `tested_with` with exact model IDs, date, evals run, pass count | Tier labels ("floor", "frontier") | A tier is relative to the models of its day and silently goes stale; an exact ID stays true. |

## Open Questions & Future Decisions

Skill-specific open questions live in each leaf LLD. Plugin-wide:

1. ✅ One plugin, three skills (one prose + two behavioral); commands are entry points to the behavioral skills, the workflow skill is invoked directly.
2. ✅ Deleted spec IDs are not reused; git history preserves the old ID's meaning.
3. ✅ Spec IDs are path-concatenated — the root-to-leaf path of the owning segment; the skill asks how to disambiguate when two segments would collide on a path prefix.
4. Self-matching has no eval yet. Open: scenario evals checking that a model given only its context's stated ID finds the right row, inherits from an older or smaller tested model, does not lift a flag on self-belief alone (a cross-vendor impostor), and treats every flag as applying when no ID is stated.

## References

- `docs/high-level-design.md` — the HLD this sub-HLD traces from.
- `docs/intent/linked-intent-dev/core/core-design.md` — leaf LLD for the `linked-intent-dev` workflow skill (`LID-CORE`).
- `docs/intent/linked-intent-dev/update-lid/update-lid-design.md` — leaf LLD for the `update-lid` skill (`LID-UPDATE`).
- `docs/intent/linked-intent-dev/lid-coach/lid-coach-design.md` — leaf LLD for the `lid-coach` skill (`LID-COACH`).
- `docs/intent/arrow-maintenance/arrow-maintenance-design.md` — sibling plugin sub-HLD; the coherence-audit behavior lives there.
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/ears-syntax.md` — EARS syntax reference.
- `plugins/linked-intent-dev/skills/linked-intent-dev/references/lld-templates.md` — LLD structure template.
- `skill-creator` plugin — eval harness used for behavioral-skill evals.
- `docs/research/harness-model-identity.md` — what coding harnesses tell the model about its identity and effort, and how reliably models identify themselves; the evidence behind *Self-matching*.
