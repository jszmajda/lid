# Audit of formal-verification-exploration.md

Audit performed cold — only this file was read. Items are organized by category A–G with line numbers (from the v3 draft) and the gap a fresh reader would hit.

## Category A — Undefined terms / acronyms

| # | Term | First used | Problem |
|---|---|---|---|
| A1 | **LID** | Title, l.1 | Never expanded. Reader guesses "Linked-Intent Development" only because the surrounding project tells them; the doc itself never spells it out. |
| A2 | **EARS** | l.10 | Appears as if known. Never expanded ("Easy Approach to Requirements Syntax") or explained as a requirements-authoring convention. Patterns (Ubiquitous / Event-driven / State-driven / Unwanted) listed at l.30–35 as if canonical. |
| A3 | **HLD / LLD** | l.8, l.13 | Never expanded. Reader has to guess "High-Level Design" / "Low-Level Design" and that they live in `docs/`. |
| A4 | **arrow / arrow overlay** | l.55, l.170 | Undefined. "per-arrow" appears without saying what an arrow is (a traced dependency from HLD through code, per project convention). `docs/arrows/` introduced at l.170 as if self-explanatory. |
| A5 | **@spec annotation** | l.98 | Introduced as "`@spec {ID}` annotations pointing code → EARS" but the convention is LID-specific and should be stated once: a code comment linking a file region to one or more EARS IDs. |
| A6 | **cascade discipline** | l.135, l.228 | "Existing cascade rule" / "existing cascade discipline" treated as known. Never defined (it's LID's rule that touching one node forces propagation through linked nodes). |
| A7 | **MC/DC** | l.216, l.288, l.301, l.452 | Aviation-software term (Modified Condition/Decision Coverage). Reader without DO-178C background will not know it. Doc mentions it five times. |
| A8 | **VC (verification condition)** | l.143, l.278 | "753 VCs", "241 VCs" without defining VC. Standard in formal methods but worth a one-time inline gloss. |
| A9 | **`//@` annotation** | l.285, l.525, l.547 | LemmaScript-specific syntax. Not introduced — reader seeing `//@ ensures` has to infer. |
| A10 | **`[V] / [Vp] / [Vx] / [Vn]`** | l.149, l.219–224 | Status markers are defined at l.219 but used earlier at l.149, l.161. Forward reference is workable but a first-time reader will stumble. |
| A11 | **`[x]`** | l.226 | Used in "compose with EARS markers" without saying `[x]` is the existing EARS "implemented" marker. |
| A12 | **trajectory-in-output** | l.285, l.301, l.326 | Introduced mid-flow as if familiar. Fully defined only in Appendix G. Forward reference without anchor. |
| A13 | **shard / coherence shard** | §5.5, l.134 | Basilisk term (group of variables updated atomically), adapted to EARS. Fine once Basilisk is introduced, but the section header uses it before it's defined. |
| A14 | **test-witness** | l.46, l.160 | A coined/bespoke engine name. Never defined — is it a product? a pattern? (It appears to be a pattern: a test file + a contract YAML asserting the test's semantic correspondence to an EARS.) |
| A15 | **differential re-interpretation / round-trip** | l.52, l.76 | Used heavily. Defined inline at l.76 ("A/B round-trip") but the A-direction / B-direction terminology at l.297 and Appendix E assumes the reader has anchored it. |
| A16 | **DDB** | l.276 | DynamoDB, presumably. Never expanded. |
| A17 | **Kahn's (topological sort)** | l.144 | "Kahn's topological sort" — fine for CS readers, but terse. |
| A18 | **Dafny, Why3, TLA+, Alloy, Lean, Coq, F\***, **Liquid Haskell** | l.47–50 | Named in a table with no one-line gloss. Experienced FM readers will know them; the doc promises to be legible to senior engineers and some will not. |
| A19 | **SMT-backed prover** | l.139 | Fine for FM readers; worth a gloss that the prover uses an SMT solver (Z3) as its decision procedure. |
| A20 | **`_status.yaml`** | l.178, l.230, l.335 | First used before defined. Schema appears in Appendix F. |
| A21 | **`[Vn]` qualitative / LLM-shaped** | l.149, l.161 | "LLM-shaped EARS" is a doc-specific category for requirements describing LLM behavior. Never introduced. |

## Category B — Undefined project references

| # | Reference | First used | Problem |
|---|---|---|---|
| B1 | **the case-study codebase** | l.156, l.272 | Introduced as if known — the case-study project the experiments run against. No one-liner about what it is. |
| B2 | **FEAT-DET-018, FEAT-DET-014, FEAT-DET-021, FEAT-LIFE-001..003, FEAT-DATA-001, FEAT-NAR-003** | l.102, l.156–161 | EARS IDs with no legend — prefix meanings (DET = classification, LIFE = lifecycle, DATA = data, NAR = narrative?) are guessable but undocumented. |
| B3 | **`docs/llds/FEAT.md`, `docs/specs/FEAT.md`, `docs/arrows/FEAT.md`** | l.102, l.168–170 | File paths into the case-study repo, not this one. Reader will look in this repo and not find them. |
| B4 | **`runner.ts`, `runner.test.ts` (generic placeholders)** | l.198, l.200 | Same issue — case-study paths shown without saying "these paths live in the case-study repo." |
| B5 | **`node_modules/lemmascript/tools/dist/dafny-emit.js:337`** | l.331 | File path into the case-study's `node_modules`; not reproducible from this repo. |
| B6 | **the existing cascade rule** | l.228 | Assumes the reader knows LID already has one. |
| B7 | **arrow overlay (plugin)** | l.241 | Presumed-known plugin / tooling. |

## Category C — Session / history references

| # | Reference | First used | Problem |
|---|---|---|---|
| C1 | **"the earlier framing"** | l.10 | Whose earlier framing? Prior draft? Prior turn of a conversation? Unclear. |
| C2 | **"we've been exploring"** | l.24 | "We" is undefined in a research doc — presumably the author + an agent across a multi-turn session. |
| C3 | **"our first experiment"** | l.163 | Which one? Explained later in §11, but the forward reference isn't signposted. |
| C4 | **Wave 1 / Wave 2** | l.285, l.291, l.307 | "Refined in Wave 2" before Wave 2 is introduced. §11.1 headers use "First wave" / "Second wave" which helps, but cross-referencing by "Wave 2 / B5" (l.285) requires the reader to flip forward. |
| C5 | **"Turn 5 pivot"** | l.315 | Opaque. Which turn? Pivot from what to what? This is conversation metadata leaking into the doc. |
| C6 | **"this session"** | l.315, l.329 | Unlabeled — the reader has no timestamp/anchor for the session. |
| C7 | **"the promotion question resolves"** | l.337 | Promotion to what? From research to adopted? Reader has no prior context for "promotion." |
| C8 | **"both this document admits …"** / **"two prior claims in this document were wrong"** | l.311 | Which claims were wrong is narrated, but the artifact of the prior-and-now-softened claim isn't obvious to a first-time reader — they're reading the softened version. |
| C9 | **v0.1 / v0.2 / v0.3 schema versions** | l.181, l.212, l.321, l.354 | The v0.1 schema is never shown (v0.2 is "post-experiment"). A reader who wants to see the baseline has nothing. |
| C10 | **"Ran 2026-04-22 in parallel"** | l.293 | "In parallel" with what? Prior or concurrent session work? |

## Category D — External citations / claims-without-warrant

| # | Reference | First used | Problem |
|---|---|---|---|
| D1 | **Basilisk (OSDI 2025)** | l.88, l.90 | Cited but no authors/URL in-body. Reader who hasn't read the paper cannot evaluate claims like "Basilisk augments hosts with an append-only log" (l.130). A one-line "what it is, what it showed" is missing. |
| D2 | **LemmaScript** | l.47, l.137 | URL given at l.139, good. But the case-study claims ("hono CVE-2026-39409", "charmchat Kahn's", "equality-game 753 VCs") have no URL/reference. Reader cannot verify. |
| D3 | **hono CVEs (CVE-2026-39409, CVE-2026-39410)** | l.141 | Presented as fact. Future-dated from a 2026-04-22 perspective, plausible — but no link. |
| D4 | **node-casbin**, **equality-game**, **charmchat** | l.142–144 | Project names with no context. `charmchat` in particular is unlikely to be recognized. |
| D5 | **Liquid Haskell, refinement-TS, `@lemmafit/contracts`, io-ts, zod** | l.50–51 | Listed without sources. |
| D6 | **Dafny 4.11 + Z3** | l.278 | Versions asserted; fine. |
| D7 | **"LemmaScript emitter produces Dafny `method` (not pure `function`)"** | l.570 | Technical claim without source. Anyone trying to reproduce would need the emitter source. |

## Category E — Cross-references (§N) pointing at thinly-contextualized content

| # | Reference | From | To | Problem |
|---|---|---|---|---|
| E1 | "(see §5.4)" | l.121 | §5.4 | §5.4 is about git as history-preservation — self-contained enough. OK. |
| E2 | "Narrowed the §10 claim" | l.301 | §10 | §10 is a skeptical-case list; the specific claim narrowed isn't pinpointed until Wave 2 findings §11.3. |
| E3 | "§7 / §10 implicitly treated CodeQL as limited…" | l.313 | §7, §10 | Reader has to scan both sections to find the offending implicit treatment. No line-level anchor. |
| E4 | "See Appendix G" | l.312, l.326, l.573 | App. G | Appendix G is self-contained. OK. |
| E5 | "See Appendix F" | l.321 | App. F | Appendix F is the v0.3 schema; self-contained. OK. |
| E6 | "See §11.3" (implicit in "Wave 2 cross-cutting findings") | l.285 | §11.3 | Wave 2 is fine once §11.2 is read. Lightly coupled. |
| E7 | "See `docs/research/experiments/…`" | l.280, l.305 | external | Reader who doesn't know experiments live in this repo may miss it. |
| E8 | "The earlier framing" | l.10 | No § | There is no prior section — this is session-history, not a real cross-reference (dup of C1). |

## Category F — Assumed code / infrastructure knowledge

| # | Item | First used | Problem |
|---|---|---|---|
| F1 | **CodeQL** | l.45 | Standard engineer knowledge probably, but a one-line gloss wouldn't hurt — a GitHub tool for querying code as a database of facts. |
| F2 | **Semgrep Pro** | l.45 | Same. |
| F3 | **DynamoDB / `list_append`** | l.276 | Engine-specific DynamoDB update expression. A reader not familiar with DDB will miss why `list_append`-only is a meaningful structural property. |
| F4 | **`@spec` annotation syntax** (`// @spec AUTH-UI-001, AUTH-UI-002`) | nowhere in this doc | The doc assumes readers know the syntax and placement. A one-line example would help. |
| F5 | **`frontmatter`** in markdown EARS files | l.98–106 | A YAML block at the head of a markdown file carrying per-spec metadata. Fine for most, but the "per-EARS or per-section" placement is under-specified. |
| F6 | **`git log -S`, `git grep -l`, `git log --follow`** | l.600–603 | Technical git invocations, fine for senior engineers but some will blink at `-S` (pickaxe). |
| F7 | **Claude Code plugin** | l.349 | Referred to as if known tooling. |
| F8 | **Dafny `method` vs. `function`** | l.570 | Fine for Dafny users; opaque to others. |
| F9 | **`@lemmafit/contracts`** | l.51 | An npm package, probably — no URL or note. |
| F10 | **`TaintTracking::Global`** | l.313 | CodeQL-specific API. |

## Category G — Missing-motivation claims

| # | Claim | Line | What's missing |
|---|---|---|---|
| G1 | "Per-arrow, per-layer engine profile. Not universal. Not one prover." | l.55 | Why not one prover? Obvious counter ("wouldn't a single formal backend be simpler?") isn't engaged. |
| G2 | "Formal verification scales down the stack; differential re-interpretation scales up." | l.68 | Asserted; the prior table supports it, but a one-sentence "because prose gets narrative-heavy upstream, LLM reading dominates; because code gets formal, engines dominate" seals it. |
| G3 | "Differential produces review comments (probabilistic). They occupy different stages of the loop." | l.86 | Why can't differential be a gate too? Because non-determinism (noted much later at l.261); connect earlier. |
| G4 | "Source stays untouched." | l.146 | Why overlay, not inline? Reader may ask: wouldn't inlining be tighter? Justification (decoupling language-native toolchain, minimizing LID footprint) is implied but not stated here. |
| G5 | "Git-provenance engines MUST NOT block CI." | l.628 | Why MUST NOT? B7 found raw-drift noise. A one-liner next to the MUST NOT would help. Already partially covered at l.319 but not near the MUST NOT. |
| G6 | "Not a new plugin. Additive:" | l.234 | Why not a new plugin? Presumably to avoid surface-area growth; stated as minimum-system discipline — but that discipline isn't referenced. |
| G7 | "LLD ↔ HLD differential (gate 2) — high noise ratio until gate 3 proves out" | l.345 | Why high noise? Not argued. |
| G8 | "Intent ↔ HLD (gate 1) — user-in-loop by necessity" | l.346 | Why "by necessity"? Briefly: because the ground truth lives in the human's head. |
| G9 | "Basilisk-style inductive-invariant synthesis — different problem shape" | l.348 | Different how? LID isn't a distributed protocol, noted at l.90, but linking the two would help. |
| G10 | "Claude Code plugin packaging — architecture not yet stable" | l.349 | Fine, but "Claude Code plugin" appears once as deferred work without prior grounding. |
| G11 | "TLA+ experiment — no protocol-shaped EARS in the case-study" | l.350 | Defensible but dangles — a reader who doesn't know the case-study's scope can't evaluate. |

## Totals

- Category A (undefined terms): 21 items
- Category B (undefined project references): 7 items
- Category C (session/history references): 10 items
- Category D (external citations): 7 items
- Category E (cross-references): 8 items (3 genuinely problematic)
- Category F (assumed infra knowledge): 10 items
- Category G (missing motivations): 11 items

**Total: ~74 items**, with heavy overlap in A/B and C/E. The highest-leverage fixes are:

1. Add a §0 background/prerequisites section introducing LID, HLD, LLD, EARS, arrow, @spec, cascade, the case-study codebase, Basilisk, LemmaScript, and differential re-interpretation.
2. Add a §0.1 provenance paragraph explaining that this doc grew from an exploratory session, "Wave 1 / Wave 2" map to specific dated experiment sets under `docs/research/experiments/`, and "Turn 5 pivot" is session metadata that should be reframed.
3. Inline-expand acronyms at first use (EARS, HLD, LLD, MC/DC, VC, @spec, SMT, DDB).
4. Add a one-line gloss for each external tool/paper (Basilisk, LemmaScript case studies, CodeQL/Semgrep, Dafny/TLA+/Alloy).
5. Reframe Turn 5 / "the earlier framing" / "our first experiment" / "this session" language.
6. Leave v0.1 → v0.2 schema evolution as-is but note the v0.1 baseline was never formalized (historical).
