# B10 Frozen Audit Prompts (instrument of record, frozen 2026-08-02 post-pilot)

All grid arms use these templates verbatim (per-unit fields in `{braces}`; `{FIXTURE}` is FIXTURE-DESCRIPTION.txt). Pilot ran a pre-freeze rubric; pilot audits are shakeout only and the 4 pilot specs re-run on these prompts inside the grid.

## A-direction (×3 per unit, fresh zero-context, arm model)

> {FIXTURE}
>
> You are given ONLY the EARS requirement below. Do not use any tools; do not open, search for, or read any files; respond directly from the requirement text alone. (Attempt {i} — independent.)
>
> EARS {specId}: "{specText}"
>
> Produce: a concise Rust implementation sketch (a function or small module) that implements exactly this requirement. Make reasonable assumptions; explicitly list EVERY assumption you had to invent (type shapes, edge cases around invalid/boundary input, defaults, fallback behavior). If the EARS is ambiguous, state which interpretation you chose and why. Keep it under 400 words. Your final message is consumed as raw data by a harness, not read by a human.

## B-direction (×3 per unit, fresh zero-context, arm model)

> {FIXTURE}
>
> (Attempt {i} — independent.) Read ONLY these files — do not open, search for, or read anything else:
> {sliceFiles}
>
> Among other concerns, these files implement: {topic}. Reconstruct the EARS-style requirement(s) (patterns: ubiquitous / event-driven / state-driven / unwanted-behavior) that this code ENFORCES for that specific concern, written the way a spec author would state them in a requirements doc. Include every behavior the code pins — including behavior pinned only by tests — that a requirements doc should state: exact constants, tie-break rules, normalization, error semantics, boundary handling. Do not speculate beyond what the code and tests show. Keep it under 400 words. Your final message is consumed as raw data by a harness, not read by a human.

## Classifier (×1 per unit, arm model, schema-forced)

> You are the classification step of a bidirectional differential audit (B9/B10 protocol). {FIXTURE}
>
> The REAL EARS requirement {specId}: "{specText}"
>
> The real implementing code and tests — read these files:
> {sliceFiles}
>
> Below are 3 independent A-direction outputs (implementation sketches written from the EARS text ALONE) and 3 independent B-direction outputs (EARS reconstructions written from the code ALONE).
>
> Direction semantics:
> - Direction A = SPEC-SIDE SURPLUS: the spec states or forces something the code does not honor — behavior the A-outputs implement because the spec text states it but the real code lacks it, or a sub-decision the spec leaves open, forcing the A-outputs to invent. IMPORTANT: distinguish spec-traced behavior from inventions — A-side behavior that traces to explicit spec text and is missing from the real code IS a finding; unanimous A-side behavior with NO basis in the spec text is an assumption artifact, NOT a finding.
> - Direction B = CODE-SIDE SURPLUS: the code+tests enforce behavior (constants, tie-breaks, normalization, error semantics, boundaries) that the spec text never states — visible by comparing the B-outputs against the REAL EARS text above.
> - BD = both directions surface the same or related gap.
>
> Classification is the RELATIONSHIP between the two signals, not either alone:
> - BD-COHERENT: neither direction surfaces anything material.
> - A-ONLY-DRIFT: A-side surplus only. / B-ONLY-DRIFT: B-side surplus only. / BD-DRIFT: both surface the same or related gap. / INCONSISTENT-BLIND: runs within a direction disagree too much to classify.
>
> [A1..A3, B1..B3 blocks]
>
> Classify, then list each concrete drift finding ORDERED STRONGEST-FIRST (direction + precise description: what the spec text says vs what the code+tests actually pin, naming exact constants/rules where relevant). Rate each direction's stability (agreement across its 3 runs).

Schema: classification ∈ {BD-COHERENT, A-ONLY-DRIFT, B-ONLY-DRIFT, BD-DRIFT, INCONSISTENT-BLIND}; findings[] {direction ∈ {A,B,BD}, description}; stability {aAgreement, bAgreement ∈ {low, medium, high}}; notes.

## Adjudication (measurement layer — Fable; Sol cross-check mirrors with embedded materials)

Realness (blind, per unit): verdict per finding ∈ {REAL, CROSSREF(sibling), FALSE-ALARM}, judged against the audit tree and the full requirements file; no knowledge of seeds or the key.
Key-match (seed units): detected iff some finding surfaces the seeded gap with correct direction and substance. Direction rule: key B matched by finding B or BD; key A by A or BD; key BD by BD, or by an A finding plus a B finding covering both sides.
