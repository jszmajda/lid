# Audit protocol

Full six-step protocol for a single EARS audit. The SKILL.md body has a summary; this file has the depth.

## Inputs

- `EARS_ID` — the spec ID to audit (e.g., `KWP-UE-004`, `BIDIFF-007`).
- `N` — runs per direction. Default 3. Configurable via `--runs=N` or `bidirectional-differential.default-runs` in `CLAUDE.md`.
- `arrow_overlay_root` — `docs/arrows/` (verified present before this protocol runs).

## Step 1 — Resolve inputs

1. Find `EARS_ID` in `docs/specs/`. Each spec file is markdown; EARS appear as bullets in this format:
   ```
   - [{marker}] **{EARS_ID}**: {EARS text spanning to end of line}
   ```
   where `{marker}` is `x`, ` ` (space), or `D`. A regex like `^- \[[xD ]\] \*\*{EARS_ID}\*\*:` finds the bullet; the EARS text runs from the first character after the colon-space to end of line. Read the verbatim text.
2. Record the EARS's current status marker (`[x]` / `[ ]` / `[D]`).
3. Determine the segment the EARS belongs to from the arrow overlay — specifically, which segment in `docs/arrows/index.yaml` owns the spec file the EARS lives in. Don't try to derive segment names from the EARS ID's prefix shape; ID structure is project-flexible (LID supports `{FEATURE}-{TYPE}-{NNN}` and longer namespaced forms), so trust the arrow overlay's mapping rather than parsing the ID.
4. Find all `@spec {EARS_ID}` annotations in the codebase (`git grep -l "@spec.*{EARS_ID}"`). Collect each annotated region (the function, class, component, or block the annotation sits above).
5. Optionally collect co-located test regions that carry `@spec {EARS_ID}` — these provide extra context for the A-direction but are treated as separate input.

**If no `@spec` annotation is found** → emit a coverage-gap entry for this EARS in the final summary and skip the remaining steps. Do not spawn blind sessions.

**If the EARS is a negative requirement ("shall NOT X")** with no production sink to annotate → emit `UNANNOTATABLE` and skip. See the §Unwanted section of SKILL.md for the signpost recommendation.

### Codebase description for the blind sessions

Both A- and B-direction prompts include a one-line codebase description so the fresh sessions have minimal orientation. **Source it from `docs/high-level-design.md`** — the HLD's first descriptive paragraph (typically the project summary) usually compresses cleanly to one sentence. If the HLD is missing or too abstract to compress, ask the user during scoping for a one-line description and reuse it across the run.

## Step 2 — Strip leaky identifiers from the code

The B-direction session receives code only. It must not be able to reconstruct the EARS by reading vocabulary back out of identifiers, comments, or filenames.

### Stripping rule categories

1. **Annotations and ID mentions**. Remove `@spec` annotations and any textual occurrence of the EARS ID (including in commit-reference comments, JSDoc tags, log strings).
2. **Vocabulary-echoing identifiers**. Rename variables, functions, methods, and fields whose name restates the EARS. Example: an EARS saying "cap unincorporated entries at N" paired with code using `unincorporatedEntriesCap` → rename to `maxItems` or another semantics-preserving, spec-neutral name. Preserve behavior; remove surface hints.
3. **Comments paraphrasing the EARS**. Strip or genericize. Comments explaining *implementation choices* stay (they're design content the B-direction legitimately gets); comments restating *requirement intent* go.
4. **Test files in the B-direction input — exclude by default.** Tests articulate intent directly through `describe`/`it`/`test` strings — including them in the B-direction's input is effectively handing it the EARS, which collapses the audit to a tautology. The default behavior is to **omit test files entirely** from the B-direction's stripped-code input. Include test files only when the user explicitly opts in (e.g., when the production-code region is tiny and tests carry behavioral details that would otherwise be lost). When tests *are* included, genericize strings that echo EARS phrasing.
5. **File and directory names**. Flag but leave alone unless they textually embed the EARS ID. Renaming paths changes surrounding context (imports, module resolution) and risks breaking the semantic content the B-direction is supposed to read.

### Apply in a working copy

Do not modify the real code. Write the stripped version to a scratch file or pass it through stdin to the `claude -p` subprocess. The A-direction does not need stripping (it starts from the EARS, not the code).

### Stripping-failure spot-check

After the B-direction session returns, check whether its reconstructed EARS has **greater than approximately 70% word overlap** with the real EARS text. If it does:

- Flag the result as a *suspected stripping-rule failure* in the audit record.
- Do not silently emit `BD-COHERENT` — a B-direction that matches the real EARS word-for-word is most likely evidence of leaked vocabulary, not evidence of coherence.
- Surface the spot-check in the user summary for manual verification.

Overlap calculation: tokenize both strings (lowercase, whitespace + punctuation split, stopword removal), count intersection over union.

## Step 3 — Spawn N A-direction sessions

For each of N (default 3), invoke in parallel:

```bash
claude -p --output-format json "$A_PROMPT" < /dev/null &
```

where `$A_PROMPT` is:

```
Project context (one line): {codebase description from Step 1's HLD-derived line}

Task: Produce a minimal, naive implementation of the following EARS requirement.
Write idiomatic {language} code that satisfies the requirement. Do not add
features the EARS does not require. If a decision point is unstated, pick the
simplest default that satisfies the requirement as written.

EARS ({EARS_ID}): {verbatim EARS text}

Output only the code.
```

Collect each session's JSON output; extract the assistant message body as the A-direction candidate code.

## Step 4 — Spawn N B-direction sessions

Concurrent with A-direction. For each of N:

```bash
claude -p --output-format json "$B_PROMPT" < /dev/null &
```

where `$B_PROMPT` is:

```
Project context (one line): {codebase description from Step 1's HLD-derived line}

Task: The following code implements a requirement in a larger system. Reconstruct
the single EARS (Easy Approach to Requirements Syntax) requirement this code was
most likely written to satisfy. Use one of these EARS patterns:

- "The system shall {action}."
- "When {event}, the system shall {action}."
- "While {state}, the system shall {action}."
- "Where {feature enabled}, the system shall {action}."
- "If {condition}, then the system shall {action}."

Keep it to one sentence. State any invariants or edge cases the code enforces
that a naive implementer might miss.

Code:
{stripped code}

Output only the reconstructed EARS.
```

Collect each session's output as the B-direction candidate EARS.

## Step 5 — Compare and classify

Two analyses, in order. Comparison throughout this step is **by behavioral semantics, not text or AST shape**: ask "does this code do the same thing on the same inputs?" and "does this reconstructed EARS describe the same behavior under the same conditions?" — not "are the bytes the same?" Two implementations that look syntactically different but compute the same function on the same domain are equivalent for the audit's purpose. The judgment is the LLM's; the anchor is semantic equivalence.

### Within-direction variance

For A-direction:
- Compare each A-run's candidate code against the real code on behavioral grounds.
- Do the N A-runs produce **behaviorally similar candidates against the real code**, or do they diverge from each other?
- If they diverge significantly from each other (different approaches, different data structures, wildly different control flow that yields different behavior), A-runs have high variance.

For B-direction:
- Compare each B-run's reconstructed EARS against the others.
- Do the N B-runs elevate the *same* invariants / cluster *the same* sub-decisions, or do they point in different directions?
- If they diverge significantly from each other, B-runs have high variance.

**If within-direction runs split 2-vs-1 at N=3 on the classification-relevant dimension**, re-run the affected direction at N=5 and classify on the majority. If the 5-run outcome still splits or the split shape changes between runs, classify `INCONSISTENT-BLIND`.

### Between-direction alignment

Convergent A-runs + Convergent B-runs + A matches real code + B matches real EARS → `BD-COHERENT`.

Convergent A-runs + Convergent B-runs + A matches real code + B elevates unstated invariants → `B-ONLY-DRIFT`.

Divergent A-runs (all valid) + Convergent B-runs + B matches real EARS → `A-ONLY-DRIFT`.

Divergent A-runs + Divergent B-runs + correlated drift (A-runs miss what B-runs elevate) → `BIDIRECTIONAL-DRIFT`.

High within-direction variance, no clean alignment → `INCONSISTENT-BLIND`.

See `classification-codes.md` for decision rules with worked examples.

## Step 6 — Write the audit record

Output path:

```
docs/arrows/experiments/bidirectional-differential/{segment-name}/{EARS_ID}.md
```

Use the template in `audit-report-template.md`. Include:

- ISO timestamp of the run.
- Git SHA at audit time (`git rev-parse HEAD`).
- N (runs per direction), actual runs used (in case of re-run).
- Classification code and default Action per the Classification → Action mapping in `classification-codes.md`.
- Verbatim EARS text.
- Code-location anchors (file:line for each `@spec`-annotated region).
- A-direction summary (convergent produced code; divergent choices; sub-decisions invented).
- B-direction summary (reconstructed EARS; elevated sub-decisions; cluster-splits if applicable).
- Drift findings tagged with severity: `possible-bug`, `latent-refactor-hazard`, or `pure-documentation`.
- Recommended reconciliations.

**Mutation not accumulation.** A new audit for the same EARS replaces the file. Commit the prior audit before re-running if before/after comparison matters; use `git diff` across the two commits to compare.

## After all EARS in scope are audited

Produce the user summary:

- Per-arrow classification counts (e.g., `KWP-UE: 2 BD-COHERENT, 1 BIDIRECTIONAL-DRIFT, 1 B-ONLY-DRIFT`).
- Top-priority drift findings across the audited scope (rank by severity: possible-bug > latent-refactor-hazard > pure-documentation).
- Coverage gaps (EARS with no `@spec` annotation) and `UNANNOTATABLE` signposts.
- Recommended reconciliations grouped by Action: `reconcile-code` first, then `reconcile-EARS`, then `advisory`, then `acknowledged-coherent`.

For every non-`BD-COHERENT` finding, the recommendation begins with validating the discovered intent with the user and cascading through the arrow (HLD → LLD → EARS → Tests → Code). The Action names the starting layer; the cascade walks all downstream layers in order. See SKILL.md §"Repair path — cascade through the arrow".

## Failure modes to watch for

- **Leaked vocabulary** surviving stripping → caught by the > ~70% overlap spot-check.
- **Subprocess hang** (rare) → a session that doesn't return is treated as absent; if fewer than 2 sessions return per direction, classify `INCONSISTENT-BLIND` with a timeout note.
- **Model-version drift** between runs → all N A-direction and N B-direction sessions should use the same model; record which model in the audit record if it was explicit.
- **Large code regions** (thousands of lines) → the B-direction prompt may hit context limits. Segment the code along `@spec`-boundary lines and audit each segment as a sub-EARS.
