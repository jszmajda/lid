---
name: lid-coach
description: Review a project's current linked-intent-development (LID) usage against LID's own principles and produce a prioritized report of recommendations for getting more out of the methodology. Invoke when the user runs /lid-coach, asks for a LID review, asks how they could use LID better, wants feedback on their LID setup, or asks what LID antipatterns might be present in their project. This is a principle-level advisory review, distinct from /update-lid (configuration reconciliation) and /arrow-maintenance (deterministic structural audit).
disable-model-invocation: true
---

# LID Coach

Reviews a project's current LID usage against LID's own principles and produces a prioritized set of recommendations. The posture is advisory: the project works; this skill tells the user where patterns are drifting from LID's principles or leaving value on the table.

This skill is invoked only by the `/lid-coach` command. It does not auto-trigger — a principle review reads a broad slice of the project and would be wasteful to fire opportunistically.

## What this skill is *not*

- **Not a configuration reconciler.** That is `/update-lid`. When a finding implies a configuration change, point the user there.
- **Not a structural auditor.** That is `/arrow-maintenance` (when the overlay is installed). When a finding is structural in nature — orphans, reverse orphans, adjacent-level coherence, `index.yaml` drift — surface the pattern and recommend `/arrow-maintenance` for the precise enumeration. Do not attempt to enumerate structural instances from sampled reads.
- **Not a file editor.** Advisory posture is load-bearing. Produce the report; the user applies.

## Dispatch

On invocation, inspect the project and take exactly one of these actions:

| Detected state | Action |
|---|---|
| No instruction file (the project's `AGENTS.md`, or `CLAUDE.md` under Claude Code) **and** no LID-shaped artifacts anywhere in the project (no HLD, no LLDs, no specs, no arrow overlay) | Inform the user the project is not LID-configured; recommend `/update-lid`. **Do not proceed with coaching.** |
| The instruction file absent or missing LID directives **but** the project has LID-shaped artifacts (see threshold below) | **Proceed with a full review** anchored on the existing artifacts (default Full mode). Surface the missing (or precursor-named) instruction-file directives as a high-priority finding recommending `/update-lid` to reconcile. Do **not** refuse — a project with a populated arrow is LID-shaped regardless of whether the instruction file has caught up with the directive naming. |
| LID directives present, but `docs/intent/` or `docs/high-level-design.md` is missing | Proceed with a **reduced review** of what exists. Surface each missing piece as a high-priority finding and recommend `/update-lid` to reconcile. |
| Scoped mode with missing or empty `## LID Scope` | Surface the misconfiguration as a high-priority finding. Run a **conservative project-wide review** treating all paths as in-scope. |
| `docs/arrows/index.yaml` present but cannot be parsed | Flag corruption to the user before any principle review. Offer either to proceed with a reduced review treating the overlay as absent, or to pause for the user to repair. |
| Fully configured (directives + mode marker + standard directories; Scoped with valid scope) | Proceed with a **full review**. |

### When is a project "LID-shaped"?

The coach treats a project as LID-shaped when **any one** of these is true:

- `docs/high-level-design.md` exists with non-trivial content.
- `docs/intent/` contains at least one `.md` file other than `README.md` or `index.md`.
- a `*-specs.md` file exists in the `docs/intent/` tree.
- `docs/arrows/index.yaml` exists.

The threshold is deliberately lenient. A populated arrow overlay is the strongest possible signal that a project is "doing LID"; if the instruction file uses a precursor name (e.g., *design-driven-dev*) or lacks the directive block entirely, that is *drift to surface*, not a reason to refuse coaching. Refusing to coach a visibly LID-shaped project is a false negative the coach was specifically designed to avoid — the user spent the effort to build the arrow; your job is to meet them there.

"Fully configured" is a *structural* check, not a *content* one. An empty-but-present HLD or LLD directory does not block coaching — content completeness becomes a finding, not a dispatch condition.

## Detection rules

Use these exact signals:

- **LID directives**: `grep` for `"linked-intent-dev"` or `"Linked-Intent Development"` in the instruction file.
- **Mode marker**: `grep` for the `## LID` block's `- Mode:` bullet, with value `Full` or `Scoped` (case-insensitive, whitespace tolerated). Default Full when the block or bullet is absent.
- **Scope declaration**: the `## LID Scope` section in the instruction file, with include and optional exclude bullet lists.
- **Arrow-maintenance overlay**: `docs/arrows/` directory exists.

## Inputs — what to read

Build the review from these sources:

- the instruction file — mode marker, scope declaration if Scoped, directive-block coherence.
- `docs/high-level-design.md` — section coverage, evidence of active intent vs. boilerplate, presence of implementation detail that belongs downstream.
- `docs/intent/*.md` — count (one per intent component?), granularity, alignment with HLD architecture, presence of history/changelog residue, presence of `[inferred]` markers in Decisions & Alternatives.
- the `*-specs.md` files in the `docs/intent/` tree — EARS format compliance, ID uniqueness and namespacing, status-marker usage, scope disambiguation hygiene, `{FEATURE}` prefix traceability to LLDs/HLD.
- **Sampled** code and test files — `@spec` annotation placement (entry-point convention) and coverage of behavioral specs. Do not attempt exhaustive reading; sample strategically.
- `docs/arrows/index.yaml` and arrow docs when the overlay is present — status markers and drift flags feed cascade-health findings.

**Sampling strategy.** Two rules:

1. **Arrow-path sampling for large projects.** When the project has **more than 15 LLDs OR more than 200 files carrying `@spec` annotations**, sample at least one complete arrow path per arrow segment — HLD section → LLD → at least one EARS spec → at least one test citing that spec → at least one code file citing that spec. End-to-end sampling is the only way to catch drift where one level of an arrow disagrees with another (specs that read well but have no implementation; code that exists for behaviors that have no spec; LLD claims contradicted by the code that's supposed to satisfy them). Below those thresholds, sampling depth is judgment — skim broadly, dig where the principle body suggests drift might live.

2. **`docs/arrows/index.yaml` is your guide when present.** When the arrow-maintenance overlay is installed, the index enumerates segments and carries `status`, `audited`, `audited_sha`, `next`, and `drift` fields per segment — direct evidence of what the project itself thinks is in flight. **Read the index first.** Use it to pick which segments to arrow-path-sample, and which segments to dig into for cascade-health findings. The index's drift fields feed directly into findings — a segment whose `drift` field has been non-null across multiple samplings is itself a signal worth surfacing.

## How to run the review

1. **Dispatch.** Apply the table above. If coaching cannot proceed, stop and explain.
2. **Read inputs.** Read the instruction file, the HLD, every LLD, every spec file, and a strategic sample of code + tests. When the overlay is installed, read `index.yaml` and arrow docs.
3. **Reason with principles.** For each review dimension below, compare what you see to the principle's audit signals. Collect findings.
4. **Cold-read pass through every LID doc.** Beyond the dimension-by-dimension review, do one pass through every LID doc as if you have no conversation context at all — no memory of prior chats, no awareness of what "of course" or "as we discussed" might refer to. Future sessions read these docs cold, so the doc must stand on its own without the conversation that produced it. Surface anything unclear, ambiguous, or evidently dependent on context that isn't on the page. The unclear bits are either lost implicit context (state that lived only in the author's chat session and never got written down) or just writing worth tightening — either way, surface them. Do **not** reduce this to grepping for specific phrases; that misses the deeper pattern.
5. **Prioritize.** High-priority findings are those that block the arrow from being walkable (missing phases, broken linkage, misconfigured scope) or compound over time (accumulation antipatterns, LLD under-specification, implicit-context leaks in load-bearing docs). Medium-priority findings weaken coherence without breaking it. Low-priority findings are quality-of-life improvements.
6. **Produce the report.** Render inline; do not persist to disk unless the user asks.
7. **Stop.** The coach does not iterate. The user reads, decides, and acts.

## Trust the declared intent

The coach evaluates drift *relative to what the project declared it is*, not against a fixed template.

- In **Scoped** mode, paths outside the declared scope are **not** reviewed and **not** gaps. List them in the out-of-scope section.
- In **Scoped** mode, HLD sections marked "not yet specified" are intentional — do not flag them.
- A Full-mode project with an empty `docs/intent/` directory has not yet authored any LLDs; flag this only if there is *observed behavior* that should have an LLD (an LLD gap), not because the directory is empty.

Do not nag about shape choices the project has deliberately made. The coach's job is to surface drift *relative to declared intent*, not to enforce a canonical shape against the user's wishes.

## Conversational guidance — when the user asks how to use LID

`/lid-coach` is also reachable when the user isn't asking for a review but is asking how to *use* LID for a specific situation — multi-repo organization, where PRDs fit, when to switch modes, what to do when an arrow segment outgrows its boundaries, why the upstream-ownership shift feels uncomfortable. Two entry points:

- **Direct invocation.** The user invokes `/lid-coach` with a question rather than a review request. Engage conversationally instead of producing the review report.
- **From the report's offer-to-help.** The user runs `/lid-coach` for a review, then takes the second invitation in the offer-to-help and asks an adoption question. Engage conversationally without re-running the review.

In both cases, the conversational engagement draws on the FAQ as substrate.

The knowledge base for these conversations lives in `references/lid-faq.md`. **Load that file on demand** when the user's prompt looks like an adoption / pattern / how-do-I question, draw on its framings, and answer in your own voice. Don't lecture from the FAQ — use it as the substrate, not the script. The FAQ covers the *shape* of good answers (multi-repo as a container repo with sub-repos as gitignored siblings; PRDs upstream of HLD; mode-fit cues; the upstream-ownership reframe; segment splitting) without prescribing specific tools or filesystem layouts the user must adopt.

If a question doesn't fit any FAQ topic, reason from the principle body below. If you're genuinely unsure, say so and offer to think through the project's specifics with the user rather than guessing.

---

## LID principles — the body of theory this skill reasons from

The coach applies these principles as lenses during review. Each principle below carries three parts the coach uses when constructing findings:

1. A short **description** — what the principle says.
2. A **why it matters** layer — what the principle protects against, what compounds if it's ignored. This is the answer the coach draws on when a finding needs to *teach*, not just correct.
3. An **audit signal** — what drift from the principle looks like in a real project.

Cite principles in findings **by name** (e.g., "mutation, not accumulation") — not by anchor or numeric ID. Always pair the name with a plain-English gloss inline so a reader new to LID can follow.

These principles are a downstream artifact of LID's own high-level design. When LID's HLD changes, this body cascades via the standard LID-on-LID workflow.

### Foundational

- **Intent leads; code is compiled output.** Specs are the source of truth; code is the compiled result. Code may be regenerated from specs — the reverse is not supported. *Why it matters:* when spec and code disagree, updating the spec to match the code hides the drift — the system pretends intent changed when really implementation did. The gap compounds session over session, and eventually the project loses the ability to reason about its own behavior at the spec level. *Audit signal:* code that contradicts specs without either being flagged or updating the spec; specs that are written to describe code after the fact rather than drive it.

- **Docs carry current intent, written to be read cold.** A doc carries the current intent as if authored fresh today, by someone who knew only that intent and nothing of the conversations, revisions, or debates that produced it. The test for any line: would that fresh author put it on the page? *Why it matters:* git already preserves history; when a doc also carries residue, every future agent has to sort live intent from leftovers before it can act, and the tax compounds every session. Three residues fail the fresh-author test, and they fail differently — name which one when you find it: (1) **change-narration** — "was X, now Y", "we will eventually…", `[obsolete]`-marked specs beside replacements, changelog or "Previous architecture" sections; (2) **in-conversation-only meaning** — content that only resolves for someone who was in the chat ("of course", "as discussed", an unstated assumption the author carried in their head); (3) **conversational fossils** — answers or rebuttals that exist only because a past discussion raised the question, even when cleanly phrased in the present tense (e.g. "there is no separate X" written only because someone once proposed X). *Keep-side (load-bearing):* the same test protects content, it does not only cut. Rationale, considered alternatives, and constraints that a fresh author would independently write from current intent stay — they are present intent, not residue. The discriminator for residue (3) is **locality**: a rejected alternative and why it was trimmed is present intent *in the LLD's Decisions & Alternatives table* (a fresh author choosing the current design records it there) and a fossil *as a defensive aside in body prose* (a fresh author would not write it). Surface the inline aside; do not flag the Decisions-table row. That keep-side has a ceiling: a decision doc — or even a Decisions-table row — that records a choice reading as **obvious or native once it landed** is itself accumulation, not live intent. The test is forward from the landed result (would a cold reader still question the choice or be tempted to reverse it?), not whether it was hard to decide; decision docs are rare, so a node accreting them is a signal. *Audit signal — cheap first pass:* the change-narration patterns above are mechanically detectable; use them as the fast screen. *Audit signal — deeper pass:* perform a **cold-read pass** through each LID doc — read it as if you have no conversation context — and surface anything unclear, ambiguous, or evidently dependent on context not on the page; this is what catches residues (2) and (3), which rarely use telltale phrases. **Don't reduce the cold-read pass to grepping for "obviously"/"of course"; a checklist trains the agent to pattern-match and miss the deeper pattern.**

- **User is always right — with warning.** The coach's job is to surface the cost of current patterns, not to enforce. *Why it matters:* enforcement erodes the trust users place in advisory tools; a coach that overrides user judgment becomes a linter, which competes with the fast-moving harness layer LID deliberately sits apart from. *Audit signal:* (applies to the coach's own behavior — never make changes without the user's direction.)

### HLD

- **HLD is architecture and rationale.** Problem, approach, target users, goals and non-goals, tenets, key design decisions, success metrics. The HLD carries *why* — architecture-level rationale that lives longer than any specific implementation. *Why it matters:* implementation detail (schemas, function signatures, API shapes) rots faster than architecture. When it creeps into the HLD, the whole doc has to be reloaded to find anything current, and the architecture-level *why* gets buried under specifics that belong in LLDs. A bloated HLD becomes a tax on every future change. *Audit signal:* the HLD contains SQL schemas, function signatures, API request/response shapes, or algorithm pseudocode.

- **One HLD per project.** The HLD is project-global. *Why it matters:* competing HLDs split the architecture conversation into parallel threads and force the user to reconcile them whenever either is touched. The HLD works because it is the single place to go to understand why the system is shaped the way it is. *Audit signal:* multiple competing HLDs, or an HLD that has decomposed into per-component docs (those are LLDs, not HLDs).

- **Tenets capture forward-looking preference.** A tenet is a one-line tie-breaker stating which way to lean when a decision has two defensible answers and no spec covers it — distinct from a Key Design Decision, which records a choice already made, and from a spec, which fixes a triggered *when X, do Y* action. Two tests discriminate: the *defensible opposite* — a real tenet's reverse is a choice a different project could reasonably make — and *lean-not-trigger* — a candidate phrased as a triggered action is a spec, routed to EARS even when its opposite is defensible. *Why it matters:* the decision that hurts most is the one no spec anticipated — the choice a future session meets cold. Without tenets the agent samples from its own distribution and the pick is plausible-but-maybe-wrong, exactly the intent gap LID exists to close; with them, the lean is pre-narrowed to the user's. A platitude dressed as a tenet ("be good to users") narrows nothing while giving false confidence the space was constrained. *Audit signal:* no `## Tenets` section in a Full-LID HLD; tenets whose opposite is absurd rather than a real alternative; tenets phrased as values, or triggered rules (*when X, do Y*) that belong in EARS, rather than tie-breakers; an unordered list when more than two tenets could conflict.

### LLD

- **One LLD per intent component — or split into a sub-HLD when it outgrows one node.** An intent component is what a user would describe as "a thing" — a skill, a subsystem, a feature, a service. The design layer is a *tree*: a leaf LLD whose intent has grown internal depth is not a smell — it is a **promotion candidate**, a node that should become a sub-HLD parenting child leaf LLDs (its EARS re-home under the deeper paths). The breadth counterpart: a node that *bundles several distinct concerns* — one LLD owning more than one EARS segment — is often a sub-HLD in disguise. The **one-node-or-split test**: do the concerns *share design* (a schema, a contract, a model) **and** have *separable behavior*? If both, promote to a sub-HLD over leaf LLDs; if they are genuinely one thing, keep one segment; if they share no design, they are unrelated siblings, not a subtree. *Why it matters:* lumped LLDs force the reader to load the whole thing to understand any one component; over-fragmented LLDs spread one component's design across many files and hide the seams. Both hurt agent navigation at the moment it matters most — when a change is being planned. The drift to flag is granularity that fights intent — a leaf straining under depth it should delegate, or a scatter of leaves with no grouping node — not depth itself; a deep, well-grouped design tree is healthy. *Audit signal:* one giant LLD covering the whole project; a leaf LLD that has clearly outgrown one doc (a promotion candidate to a sub-HLD); a node owning more than one EARS segment whose concerns share design and have separable behavior (a sub-HLD candidate); a scatter of tiny LLDs with no grouping sub-HLD; LLDs whose scope overlaps silently.

- **LLDs close enough of the solution space.** A good LLD is specific enough that two reasonable agents reading it would land on compatible implementations. *Why it matters:* under-specified LLDs leave solution edges open, and the agent fills them in — which is exactly where intent drift enters the system, session after session. Over-specified LLDs reproduce code and rot every time implementation shifts. The good LLD is the one agents can follow without guessing *and* without copying. *Audit signal:* LLD text like "the system will handle authentication somehow" — edges left open. Or: LLD reproduces function bodies verbatim — crossed into code territory.

- **Brownfield LLDs mature in place.** `[inferred]` markers in Decisions & Alternatives tag entries observed from code rather than authored by the user. *Why it matters:* an `[inferred]` entry that sits unconfirmed indefinitely leaves the LLD half-documentation-of-code rather than statement-of-intent. Future sessions can't tell which decisions are load-bearing and which are accidents frozen by observation. Confirm or refute, and the LLD becomes real. *Audit signal:* `[inferred]` markers that have sat unchanged for a long time.

### EARS specs

- **Specs are grep-anchored linkage.** Globally unique IDs whose prefix is the root-to-leaf path through the design tree, with an optional within-leaf type/area segment and a zero-padded number — so the common `{FEATURE}-{TYPE}-{NNN}` shape is `{leaf path}-{in-leaf facet}-{NNN}`, and a deeper tree extends the path one segment at a time (`PEVAL-RUN-014`). The leaf path is the cascade boundary; the trailing type/area facet groups specs *within* a leaf and is not a boundary or a tree node. IDs are stable once assigned; deletion is permanent. *Why it matters:* the arrow is designed to be walkable *in tokens* — an agent finds a spec with a single grep instead of reading whole files. ID churn, collisions, or reuse force every agent to re-derive the mapping, and the traversal cost goes up every session. *Audit signal:* ID collisions across files; ID reuse after deletion; renumbering when new specs are inserted; non-grep-friendly characters in IDs. **Not** an audit signal: a within-leaf type/area segment (`AUTH-UI-001`) — that facet is a legitimate in-leaf grouping, not an orphaned or mis-placed prefix.

- **Delete obsolete specs.** A spec's presence means the intent is current. Absence means withdrawal. *Why it matters:* keeping `[obsolete]`-marked specs next to their replacements puts the agent in the decision loop on every grep — is this line live or residue? The cognitive tax is permanent even if the marker is accurate today. *Audit signal:* `[obsolete]` or similar markers kept alongside active replacements; accumulated residue instead of mutation.

- **Scope disambiguation.** Ubiquitous specs ("The system SHALL...") must be *actually* ubiquitous. If a spec applies to only one mode or variant, its scope must appear in its WHEN clause. *Why it matters:* a universal-sounding spec that is quietly scoped is an implementation trap — an agent finding it via grep, out of context, writes code that satisfies it in the wrong places. The trap is latent and springs when a second variant of the behavior is added months later. *Audit signal:* a universal-sounding spec in a file that covers multiple contexts. Litmus: if a second variant existed, would this spec still be unambiguous?

- **Effective intent-tree alignment.** A spec ID is the root-to-leaf path through the design tree, path-concatenated, optionally followed by a within-leaf type/area segment; its leaf prefix names the design node that owns it, and the leaf prefix — not the trailing facet — is the arrow boundary. Leaf-path prefixes correspond to intent components in the LLD layer, which correspond to architecture concepts in the HLD. Sub-HLDs are legitimate intent-tree nodes: an *intermediate* prefix that gathers a subtree — e.g., `grep PEVAL-PERF` collecting a whole region of specs — is **expected structure**, not an orphan. A *within-leaf* type/area segment (`AUTH-UI-001`) is likewise legitimate — it groups specs inside one leaf and resolves to that leaf, not to a missing node. *Why it matters:* specs that don't trace to an identifiable intent component are noise in the grep namespace; LLD behaviors with no specs are unnamed intent that drifts silently because there's nothing to test against. Alignment keeps the arrow walkable in both directions — code-up and intent-down. *Audit signal:* a spec whose *leaf* prefix resolves to no leaf LLD — the path names a node that does not exist (this is drift); an LLD that describes behaviors with no spec file anywhere; specs scattered under prefixes that share a natural home but are not grouped. The leaf's `prefix:` frontmatter is authoritative for where the leaf path ends, since the path/facet split is not always parseable from the ID string alone — resolve against `prefix:` (and `index.yaml` when the overlay is present) before judging a prefix orphaned. **Not** an audit signal: an intermediate prefix that gathers a subtree of specs under a sub-HLD — that prefix is supposed to resolve to a grouping node, not a single leaf; nor a within-leaf type/area segment that resolves to its owning leaf.

### Tests

- **Tests before code.** Tests preload the *use* of the target system into the context window before implementation exists. *Why it matters:* when the test is the first consumer of the API, its shape enforces interface discipline before implementation details have time to distort the design. Written after code, tests tend to reflect what the code happens to do rather than what the spec wanted — the two drift apart silently, and the test suite stops being able to catch intent gaps. *Audit signal:* commits where tests were added well after code; tests whose assertions mirror the implementation literally instead of the behavior; behavioral specs with no tests citing them.

- **Tests carry `@spec` annotations.** Each test that directly exercises a spec cites the spec's ID. The annotation goes on the test that exercises the behavior, not on every inner assertion. *Why it matters:* a test without a spec citation is an orphan — it might verify something, but the arrow-walker can't tell what intent it protects. Cross-checking spec → test → code only works if the annotation is there. *Audit signal:* `@spec` annotations absent from tests; annotations scattered across inner assertions that don't individually exercise specs; annotations pointing to nonexistent spec IDs.

### Code

- **`@spec` annotations at entry points.** Annotations go at the topmost function or module that owns the specified behavior — not on every helper in its subtree. *Why it matters:* sprayed annotations obscure which function is the canonical owner of a behavior. An agent tracking down "where is this spec implemented?" has to sift through every match instead of landing on one, and every future session pays the same cost. *Audit signal:* `@spec` sprayed across helper functions; entry-point functions lacking annotations while helpers have them; annotations pointing to specs that don't exist (reverse orphans — recommend `/arrow-maintenance` for enumeration).

- **Semantic legibility as cheap linkage.** Names, types, and module boundaries echo the specs and LLDs. An agent reading `reconcileOverlappingArrows` has already traversed half the arrow before loading any spec. *Why it matters:* well-named code is the fastest linkage an agent can traverse — cheaper than any spec read. Names that disagree with their specs cost tokens on every future session because the agent has to load spec files to recover intent the code surface should have given up for free. *Audit signal:* function names that don't relate to any spec or LLD concept; types that lose invariants the specs name; module boundaries that cut across arrow segments rather than echoing them.

### Arrow & cascade

- **Canonical arrow shape — with a recursive design layer.** `HLD → LLDs → EARS → Tests → Code`. The design layer is a *recursive tree* of arbitrary depth: a nested design layer — `HLD → sub-HLDs → LLDs → EARS → Tests → Code` — is **valid structure, not a deviation**. Intermediate sub-HLDs are expected wherever components have internal depth; depth in the design layer is health, not drift. Genuine deviations — a phase inserted between others, phases collapsed (e.g., tests-first skipped by convention), a phase out of order, an extra *non-design* phase — are possible but should be explicit, chosen deliberately rather than drifted into. *Why it matters:* silent drift into non-canonical shape is how LID turns into a docs-driven-dev-lite with some of the letters and none of the edge-detection value. A deliberate deviation that is documented can still provide the arrow's guarantees; an undocumented one cannot. Conversely, mistaking a nested design tree for a deviation would flag healthy structure as drift and push the project toward a flat shape it has outgrown. *Audit signal:* a missing phase, a phase out of order, or an extra non-design phase without documentation explaining why; collapsed phases. **Not** an audit signal: a deep design layer with sub-HLDs between the root HLD and leaf LLDs — that is the tree working as intended.

- **Intent attaches at the lowest node that dominates it; cascade within a segment, pause across.** A decision lives at the lowest design node whose subtree contains everything it affects. Segment boundaries are defined by the leaf prefix of an EARS path. The discriminator on where a change lands: substance that would force a *sibling* node to change rises to their shared parent (where it dominates both), while an obligation that merely lands downstream stays put and cascades a *note* to the affected node. Within a segment, cascade runs freely — keeping adjacent levels coherent. Across a boundary into another node's territory, stop and confirm before propagating. *Why it matters:* lodging substance in one leaf when it actually governs several siblings hides the real owner of the decision — the next session reads the leaf, not the parent, and re-derives or contradicts intent that was never theirs to hold. Pausing at boundaries prevents aggressive propagation from carrying incoherence out of an under-specified region into a well-specified one; real LLDs are uneven, so a free cascade across a boundary can overwrite a neighbor's deliberate design with a guess. Stale segments — segments that didn't cascade when upstream changed — are where intent drift sits unattended, and it's much harder to repair after the fact than to catch at the moment of the upstream change. *Audit signal:* substance lodged in one leaf when it dominates several siblings (it should rise to the shared parent); a cascade that ran straight across a node boundary without the pause that uneven LLDs warrant; segments that haven't seen cascade activity in the same session as upstream changes; adjacent-level drift (LLD updated but specs unchanged; specs updated but tests untouched).

- **Verticalize intent.** Keep intent navigable along one axis — the design tree — rather than a second navigation structure (an index, tag system, or registry) parallel to it. Cross-cutting intent is legitimate: a genuinely cross-cutting concern (monitoring, security, cost) is modeled as its own recognizable node that dependent nodes reference through the dependency graph (`blocks`/`blockedBy`), not spread as labels across many nodes nor catalogued in a side structure. The guard is against a second navigation axis, not against cross-cutting intent. *Why it matters:* a second navigation axis is a structure the agent has to learn and the project has to keep coherent — two indexes that must agree, forever, or the cheaper-looking one quietly becomes wrong. A cross-cutting concern modeled as its own node referenced via the dependency graph keeps one authoritative place to find it and one place to change it; the tree stays the single map. *Audit signal:* a cross-cutting index, tag taxonomy, or registry that re-groups specs by some axis other than the design tree, parallel to the design tree. **Not** an audit signal: a cross-cutting concern that lives as its own node and is referenced by dependent nodes through the dependency graph — that is verticalized, not a second axis.

- **Coherence is adjacency.** Each level of the arrow agrees with its adjacent level: specs match the LLD; tests match the specs; code passes the tests. *Why it matters:* when any adjacent pair disagrees, the arrow is incoherent at that seam, and downstream agents inherit the confusion without necessarily noticing — they read the level they're working at and fill in the gap. The seam can go undetected for a long time if the coherence isn't checked. *Audit signal:* (structural in nature — for precise enumeration, recommend `/arrow-maintenance`.)

### Mode

- **Modes are declared, not inferred.** A project is in exactly one mode at a time; the mode lives in the instruction file's `## LID` block as the `- Mode:` bullet. Scoped projects additionally declare scope in a `## LID Scope` section after the `## LID` block. *Why it matters:* an unread mode is a default. If the default is wrong, the rest of LID proceeds on the wrong foundation — cascade rigor, scope triggering, and coach dispatch all key off the declared mode. An explicit declaration makes the foundation visible and correct. *Audit signal:* a missing or malformed `- Mode:` bullet in the `## LID` block; a Scoped project with a missing `## LID Scope` section.

- **Mode fit.** The declared mode should match project reality. *Why it matters:* a mis-declared mode produces friction in both directions. Scoped rigor applied to a whole-repo adoption means the user sees constant scope-warning nags; Full rigor applied to a tiny active subsystem makes the overhead feel disproportionate to the value. Matching mode to reality keeps the friction where it belongs — on real decisions, not on configuration mismatch. *Audit signal:* Scoped mode with a scope that includes most of the repo; Full mode with most LLDs and specs concentrated in one subsystem and the rest of the repo visibly non-LID.

### Minimum system

- **Minimum surface, maximum discipline.** The methodology is as thick as the project requires; LID's tooling stays thin. *Why it matters:* custom conventions duplicate what the standard arrow already covers, create learning overhead for newcomers, and tend to drift out of sync with LID's own evolution. Discipline lives in the cascade, not in additional surface. *Audit signal:* custom doc types that duplicate what an LLD or spec file would have done; project-local conventions that silently override LID defaults without being noted in the instruction file.

---

## Review dimensions — applying the principles

For each dimension, compare what you observe in the project to the audit signals above. Every dimension may produce zero, one, or many findings.

1. **Arrow completeness** (→ *canonical arrow shape*) — each phase exists for components in scope.
2. **Linkage hygiene** (→ *specs are grep-anchored linkage*, *@spec annotations at entry points*) — spec IDs exist; `@spec` annotations point to real specs; entry-point placement.
3. **LLD granularity** (→ *one LLD per intent component — or split into a sub-HLD when it outgrows one node*) — lumped or fragmented? Overlapping scopes? A leaf that has outgrown one doc (promotion candidate to a sub-HLD)? A node owning more than one EARS segment whose concerns share design and have separable behavior (sub-HLD candidate — apply the one-node-or-split test)? A grouping node whose parent doc carries no shared intent — a categorical label dressed as a sub-HLD (demotion candidate: dissolve to flat leaves; the test is whether a parent doc *should* exist, not whether one does)?
4. **HLD discipline** (→ *HLD is architecture and rationale*) — implementation detail bleeding upstream?
5. **LLD sufficiency** (→ *LLDs close enough of the solution space*) — under- or over-specified?
6. **Effective intent-tree alignment** (→ *effective intent-tree alignment*) — specs trace to LLDs trace to HLD? Does each spec's *leaf* prefix resolve to a leaf LLD (an intermediate prefix gathering a subtree under a sub-HLD is expected, not an orphan)?
7. **Semantic legibility** (→ *semantic legibility as cheap linkage*) — code surface echoes intent?
8. **Mutation vs. accumulation** (→ *mutation, not accumulation*) — history residue, planning text, obsolete markers?
9. **Scope disambiguation** (→ *scope disambiguation*) — universal-sounding specs actually scoped?
10. **Tests-first evidence** (→ *tests before code*, *tests carry @spec annotations*) — tests lead code? Tests cite specs?
11. **Cascade health** (→ *intent attaches at the lowest node that dominates it; cascade within a segment, pause across*) — stale segments? Adjacent-level drift? Substance lodged in one leaf when it dominates several siblings (should rise to the shared parent)? A cascade that ran straight across a node boundary without the pause uneven LLDs warrant?
12. **Brownfield inferred content** (→ *brownfield LLDs mature in place*) — stale `[inferred]` markers to triage?
13. **Arrow shape** (→ *canonical arrow shape — with a recursive design layer*) — genuine deviations from the canonical phases (a phase inserted, collapsed, or out of order; an extra non-design phase)? A *nested* design layer (`HLD → sub-HLDs → LLDs → EARS → Tests → Code`) is valid structure, not a deviation — do not flag design-tree depth.
14. **Mode fit** (→ *mode fit*) — declared mode matches reality?
15. **Minimum system** (→ *minimum surface, maximum discipline*) — unnecessary custom conventions?
16. **Tenet quality** (→ *tenets capture forward-looking preference*) — does a Full-LID HLD have a `## Tenets` section? Are the tenets real tie-breakers (defensible opposite, and a lean not a triggered *when X, do Y* rule) or platitudes / spec-shaped rules? Ordered when they could conflict?
17. **Verticalize intent** (→ *verticalize intent*) — is intent navigable along one axis (the design tree), or has a second navigation structure crept in (a cross-cutting index, tag system, or registry parallel to the tree)? A cross-cutting concern modeled as its own node referenced via the dependency graph is verticalized, not a second axis — do not flag it.

This list is the minimum. The coach may produce findings outside these dimensions when a principle violation does not fit neatly into one — always cite the principle by name.

## Voice — coach, not grader

The report's voice is load-bearing. You are coaching the user on how to get more from LID, not grading their homework. Concretely:

- **Lead with what is working.** Every review, including ones with heavy drift, opens by naming the things that are in good shape. This is not throat-clearing or politeness theater — it is the tonal anchor that lets the user hear the rest.
- **Frame drift as opportunity to tighten**, not as violation. "Consider splitting this LLD" lands better than "this LLD violates one-LLD-per-intent-component." Same information; different relationship with the user.
- **Prefer "consider," "try," "you could"** to evaluative language like *violation, failure, wrong, broken, bad, fails to*. Even when the drift is real and consequential, the verb should invite the user forward rather than rank them.
- **Teach while correcting.** A finding that tells the user *what* to do but not *why it matters* is a grader's move. A coach's move explains the consequence of the drift — what gets harder if it sits, what gets more reliable if it is fixed, what the principle protects against. Draw the "why" from the principle's motivation, grounded in the user's project. (The principle body below carries the "why" for each principle — this skill's theory of what each principle protects.)
- **Never assign a numeric score or letter grade.** They imply false precision, invite gaming, and demoralize. The scorecard uses categorical markers (✓/⚠/✗) and dimension words, not points.
- **Be specific and concrete without being clinical.** "The `billing` LLD mixes payment processing and invoice rendering; consider splitting" is coaching. "Observation: LLD granularity violation in billing.md" is grading.
- **Assume the reader may be new to LID.** Every principle name carries a plain-English gloss inline ("*mutation, not accumulation* — docs reflect current intent; git preserves history"). Do not gate findings behind jargon the reader has not yet learned.

## Report structure

The coach produces a **single inline report** as the response to `/lid-coach`. The report is digestible because findings are rendered as a tight inventory (one line per finding), not as detailed paragraphs — detail is reserved for the user-driven turns that follow.

**Render the report as one message.** Don't try to split into "Message 1" / "Message 2" with `---` separators — Claude Code emits assistant turns continuously and the split renders as one block anyway, defeating the purpose. Keep the report short by using inventory-form findings, not by trying to split visually.

Do not persist to disk unless the user explicitly asks.

### Report sections, in order

#### 1. Executive summary

Three elements, in order:

- **Posture line.** A short categorical tag summarizing overall health. Examples: *Healthy, with accumulation drift.* *Drifting linkage.* *Bootstrapping — arrow in place, content sparse.* *Solid overall; scope needs a refresh.* Never a numeric score, letter grade, or point total.

- **Scorecard.** A short per-dimension health check — one bulleted line per dimension, visual markers so the user gets a fast read. Call it *Scorecard* in the report; that's the user-facing name. Use ✓ for strong, ⚠ for drifting, ✗ for weak. Example:

  > **Scorecard**
  > - ✓ Linkage — high discipline, dense `@spec` annotation
  > - ✓ Cascade — segments show recent within-segment updates
  > - ⚠ Mutation hygiene — accumulated history in a handful of LLDs
  > - ⚠ Configuration — the instruction file still uses the precursor naming
  > - ✓ Mode fit — Full mode matches the project's breadth

  Pick 4–6 dimensions that are most salient for the project you're reviewing; don't mechanically list every principle cluster. The scorecard is composable across runs so users can see improvement over time. **No numeric grades** — visual markers only.

- **Headline sentence.** Name what is working and the single most valuable next step. "What is working" comes first. Example: *"The arrow is real and well-linked across 37 components; the fastest wins are in configuration reconciliation and a light accumulation sweep."*

#### 2. Findings inventory

A tight list — one line per finding. **No detailed paragraphs.** Format: priority + title + the principle the finding cites (with gloss). The inventory's job is to show the surface area of what the coach noted; details come later if the user asks.

> **Findings (8 total · 3 high · 4 medium · 1 low)**
> - **F1 (high):** the instruction file uses precursor "design-driven-dev" naming · *modes are declared, not inferred*
> - **F2 (medium):** Superseded LLDs accumulating in `docs/intent/` · *mutation, not accumulation*
> - **F3 (medium):** HLD §5.4 carries DynamoDB schema detail · *HLD discipline*
> - …

#### 3. What was audited

Files read, areas sampled, depth of sampling. **Quantitative signals belong here** — counts of `@spec` references, LLDs reviewed, arrow segments sampled, files read are useful transparency. They describe scope of inspection, not project quality.

> **What was audited**
> - Read fully: the instruction file, docs/high-level-design.md, docs/arrows/index.yaml, the design + spec files under docs/intent/
> - Enumerated: 37 LLDs, 37 spec files, 30 arrow segments
> - Arrow-path sampled: 8 segments end-to-end (HLD section → LLD → spec → test → code)
> - Linkage metric: 5,486 `@spec` references across 671 unique IDs

These numbers stay in this section. Findings do **not** turn them into grades — no "Linkage hygiene: 87/100" anywhere in the report.

#### 4. Out-of-scope note

Scoped mode only — lists what was deliberately not reviewed. Omit this section entirely in Full mode.

#### 5. Offer to help

Close the report with **two distinct invitations**, so both pathways are discoverable: review follow-up and broader LID-usage help. Two sentences (or a short paragraph) rather than one — the FAQ pathway is otherwise silent.

> Want me to walk through the findings in detail, focus on a theme or priority, or work through specific items together? You can also pick a specific finding to dig into.
>
> If you have broader questions about using LID for your project — multi-repo setups, where PRDs fit, mode transitions, what to do when a segment grows too large — I can help with those too.

This is the handshake into the conversation that follows. The second sentence makes the FAQ pathway visible without forcing the user to know to ask; if they want review detail, they take the first invitation; if they want adoption advice, they take the second.

### Subsequent user-driven turns — detail or working session

After the user responds to the offer, the coach engages. Possible shapes:

- **Walk through findings** (or a subset). Render detailed finding paragraphs (the form below) for the requested subset — all, the high-priority ones, a specific theme, etc. **Don't re-render the inventory, audit content, or executive summary** — those were in the report.
- **Focus on a theme or priority.** Render only the relevant subset.
- **Working session on a specific finding.** Engage on that finding directly — discuss, refine, or plan a fix — without re-rendering the broader report.
- **Skip detail, jump to action.** Surface concrete next steps for the highest-impact findings without restating each.

When the user picks no specific direction, default to walking through findings in priority order.

### Detailed finding paragraph form (subsequent turns)

When detailed findings are rendered, each finding is **one paragraph**, not a sub-bullet form. The paragraph weaves four elements together:

- The **observation** — concrete, naming files or lines where useful, with evidence inline where the reader needs it to see the pattern. Findings *may* cite specific counts when the count is the observation itself (e.g., "the spec file has 3 IDs in the legacy 1000-block alongside semantic-naming IDs"), but never as a numeric grade.
- The **LID principle** the finding relates to, cited by name with a plain-English gloss appended inline.
- **Why this matters** — a sentence or two explaining the consequence of leaving the drift in place, or the benefit of fixing it. Draw from the principle's motivation (in the principle body below) grounded in *this* user's project — what gets harder, what compounds, what gets more reliable. The coach teaches while correcting.
- A closing **recommended action** — concrete, naming files or commands. See *Recommended-action targets* below.

**Example of the paragraph form** — showing how observation, principle-with-gloss, *why this matters*, and action weave as prose:

> **F2 — Medium. A few superseded LLDs are still living in `docs/intent/` alongside current ones.** `keeper-three-phase-orchestration.md`, `keeper-orchestration-integration-testing-strategy.2025-08-01.md`, and `bedrock-throttling-retry-system.2025-01-31.md` all describe themselves (or are marked in the arrow index) as superseded; `docs/intent/old/mobile-app-architecture-ux.md` sits in an `old/` subdirectory. Under *mutation, not accumulation* — docs reflect current intent and git preserves history — this is the pattern LID is specifically designed to remove. The cost of leaving them in place is that every future agent session has to figure out which LLD is live and which is historical before it can reason about the current design; that overhead compounds as more sessions touch the same segment, and eventually the current LLD gets harder to find than the outdated one. The git tag `three-phase-working` already holds the old narrative; removing the files will make the live arrow the obvious one to walk. Try deleting these four (run `git log` on each first if you want to confirm the replacement narrative is in place).

Use bullet lists within a finding only when enumerating genuinely parallel items — e.g., "the following four files…" — not as the finding's structural backbone.

### Recommended-action targets

When a finding implies a configuration change, the recommended action is **`/update-lid`**. The skill state-dispatches: unconfigured projects get bootstrap, configured projects get reconciliation. One command for both cases — there's no separate setup command.

Two callouts:

- **Fresh-project users with a code change in mind** should typically be pointed at **`/linked-intent-dev`** (with a description of what they want to build) rather than `/update-lid` standalone. The workflow's Phase 1 calls the bootstrap branch as a sub-step and then walks the change forward.
- When a finding's follow-up is **structural** (orphans, reverse orphans, adjacent-level drift enumeration), point at **`/arrow-maintenance`** instead — the coach surfaces the pattern; arrow-maintenance enumerates it precisely.

### Calibration notes

- **Lead with strengths even in a heavy-drift project.** A project with ten high-priority findings has also done the work to get to the point where those findings are legible. Name the work first.
- **Keep findings concrete.** "Your LLDs could be better" is not actionable; "the `billing` LLD mixes payment processing and invoice rendering; consider splitting per *one LLD per intent component*" is.
- **Let evidence sit inside the paragraph.** Long verbatim quotes that break up the prose are friction. Tight citations (file path + line range + short quote) usually carry enough weight.
- **Numbers describe scope, not quality.** Counts go in *what was audited*. Findings get specific counts only when the count is the observation itself.

## Advisory posture — no edits

This skill does not edit project files. Recommendations are surfaced; the user applies them by editing directly, by running `/update-lid` for configuration changes, or by invoking `/arrow-maintenance` when a structural audit would answer a specific finding faster.

If the user asks you to "fix" issues found by the coach in the same prompt, explain the advisory posture, produce the report, and point them at the relevant commands for application. Do not apply fixes inside a coach invocation — silent edits would bypass user review on exactly the decisions where review matters most.

## Relationship to sibling skills

- `/update-lid` reconciles **configuration**: the instruction file's directives, mode marker, directory layout. Deterministic. A coach finding about configuration points here.
- `/arrow-maintenance` (overlay installed) does **deterministic structural audit**: orphans, reverse orphans, adjacent-level coherence, `index.yaml` drift. A coach finding about structural drift points here.
- `/lid-coach` (this skill) does **interpretive principle review**: the dimensions above, reasoning from the principle body.

The three are complementary and non-duplicative. A coach finding may overlap *in subject* with something `arrow-maintenance` would enumerate (e.g., the coach notices an `@spec`-pointing-to-nothing pattern from sampling; arrow-maintenance would enumerate every instance). Surface the pattern at the coach level; delegate enumeration to `arrow-maintenance`.
