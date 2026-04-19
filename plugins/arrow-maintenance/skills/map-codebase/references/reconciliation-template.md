# Reconciliation Presentation Template

Format for presenting candidate clusterings to the user in Phase 2 (lens selection) and Phase 3 (slicing granularity). The goal is to make the choice a *decision among alternatives* rather than a reaction to a single proposed answer.

## Phase 2 — Lens selection (3–5 clusterings)

Present each candidate as a section. Keep each under ~200 words so the user can compare side-by-side.

```markdown
## Clustering A: {lens name}

**Lens**: {one-sentence description of the angle}

**Clusters it produces** ({N} clusters):
1. **{cluster-name-1}** — {one-line description}, covering {file count} files including {3–5 key files}.
2. **{cluster-name-2}** — ...
(etc.)

**Pros**: {what this lens supports well}
**Cons**: {what this lens makes harder}
**Best for**: {what kind of reasoning this lens best supports — e.g., "understanding data dependencies", "tracking user-visible capability changes"}

---

## Clustering B: {different lens name}
(same structure)

---
```

End the presentation with:

> Pick a lens (A, B, C...) before we move to slicing granularity. If none fits, say so — I'll propose different lenses.

**Anti-pattern lenses to exclude** (do not propose): frontend/backend split, files-that-deploy-together, team ownership, generic "utils."

## Phase 3 — Slicing granularity (2–3 variations within the chosen lens)

```markdown
## Slicing: Coarse (3–4 segments)

- **{segment-1}** — covers {code areas}
- **{segment-2}** — covers {code areas}
- **{segment-3}** — covers {code areas}

Each segment carries broad scope. Fewer LLDs, less precise tracking.

---

## Slicing: Medium (6–8 segments)

(each segment finer; list them)

Balanced.

---

## Slicing: Fine (10+ segments)

(each segment narrow; list them)

More LLDs, more precise spec tracking. Higher maintenance cost.
```

End with:

> Pick a granularity. Coarse makes fewer LLDs easier to keep updated; fine makes segment-scoped change tracking more precise.

## Phase 4 — Final clustering reconciliation

Present the final segmentation (chosen lens + chosen granularity) as a table, one row per segment:

```markdown
| Segment | Description | File/path evidence | Notes |
|---|---|---|---|
| {name} | {one-line purpose} | {N} files including {key paths} | {conflicts flagged from parallel subagents, if any; component-quality concerns} |
```

Ask the user to approve, modify boundaries, reject, or split/combine specific segments. Call out any anti-pattern-shaped segments for explicit review (segments that look like team boundaries, deployment units, or generic utilities). Proceed to artifact generation only after explicit approval.
