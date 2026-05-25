# LLD Templates Reference

Low-Level Designs (LLDs) document component-specific technical decisions. LLDs are **pure design documents** — they describe *how* things work, the constraints, trade-offs, and decisions. They do not track implementation status.

An LLD is a **leaf of the design tree**: it owns its segment's EARS specs and sits under an HLD (the root) or a sub-HLD. "LLD" is a role by position, not a fixed type — the template below is a **starting point**, not a rigid shape. A node carries the sections it needs; flat depth-2 (one HLD over a flat set of LLDs) is the default. When a leaf LLD outgrows itself — its intent differentiating into sub-parts that each warrant their own design — it **promotes into a sub-HLD** with child LLDs beneath it (see the HLD template reference); the promoted node sheds its EARS to those children, since only leaves own specs.

**Frontmatter.** Every LLD carries two pointers: `parent:` names the node above it (the root HLD at depth-2, or a sub-HLD when nested), so the tree is walkable upward; `prefix:` carries the EARS namespace the leaf owns — its full root-to-leaf path — so a reader knows its spec namespace (`AUTH-*`, or `EXP-BIDIFF-*` when nested) without grepping. The directory and file names are human-readable and need not equal this prefix (`arrow-maintenance/maintenance.md` may own prefix `SCALE-MAINT`); `prefix:` is the authoritative bridge from the human name to the namespace, and it marks where the leaf path ends — a spec ID may append an optional within-leaf type/area segment and a number after the leaf prefix (`AUTH-UI-001`). A pure-prose leaf that owns no EARS omits `prefix:`. (Grouping sub-HLDs also carry `prefix:` — the namespace they root — per the HLD template reference.)

```markdown
---
parent: high-level-design
prefix: AUTH
---
```

Implementation status is tracked in:
- **Spec files** (`{node}-specs.md`, beside each design doc under `docs/intent/`) via `[x]`/`[ ]`/`[D]` markers on EARS specs
- **Arrow docs** (`docs/arrows/`) via coverage tables (if using arrow-maintenance plugin)

## Greenfield vs. Brownfield

The template below is used for both greenfield LLDs (authored before implementation) and brownfield LLDs (reverse-engineered from existing code). There is no separate brownfield template. What varies is the *content's starting state*:

- **Brownfield Decisions & Alternatives** rows carry `[inferred]` in the Rationale column when the decision was observed in code rather than authored by the user. As the user confirms or refutes the inference in subsequent sessions, the `[inferred]` marker is removed and the rationale is written out.
- **Brownfield Open Questions & Future Decisions** holds observed-but-unexplained behaviors and technical debt discovered during reconnaissance. These migrate into Decisions, into specs, or into a planned remediation as the user engages with the code.
- **Brownfield Major sections** may describe current state alongside intended behavior when the two differ — flag divergence explicitly rather than pretending the code matches intent.

As a brownfield LLD matures through normal LID cascades, inferred content becomes authored content. No migration or "graduation" step is needed — the LLD evolves in place.

## File Location

Every node is a **directory** under `/docs/intent/`, named for the node. A leaf LLD `foo` is `docs/intent/foo/foo-design.md`, with its EARS beside it as `foo-specs.md` and a `decisions/` dir if it has decision docs. At the default depth-2, each LLD is one such folder directly under `docs/intent/`:
- `docs/intent/user-authentication-flow/user-authentication-flow-design.md` (+ `user-authentication-flow-specs.md`)
- `docs/intent/payment-processing-pipeline/payment-processing-pipeline-design.md`
- `docs/intent/offline-sync-strategy/offline-sync-strategy-design.md`

**The directory layout mirrors the design tree's structure (node-as-folder).** A sub-HLD `foo` is the directory `docs/intent/…/foo/` holding `foo-design.md` plus a child directory per child — e.g. the `arrow-maintenance` sub-HLD is `docs/intent/arrow-maintenance/arrow-maintenance-design.md` with child directories `maintenance/` (holding `maintenance-design.md` + `maintenance-specs.md`) and `map-codebase/`. A leaf and a sub-HLD have the same shape, distinguished only by whether the folder holds a `-specs.md` (leaf) or child directories (sub-HLD). When a leaf promotes into a sub-HLD, its `-specs.md` goes away — the EARS move down into the new leaf children — and child directories appear beside its `-design.md`. Directory and file names are human-readable and need not equal the EARS prefix; each node's `prefix:` frontmatter carries it (see the EARS syntax reference). Decision docs follow `references/decision-doc-template.md`.

## Standard Structure

```markdown
# [Component Name]

## Context and Design Philosophy

Why this component exists and guiding principles.

## [Major Section 1]

Technical details...

## [Major Section 2]

Technical details...

## Decisions & Alternatives

For each significant design choice, record what was chosen, what was considered, and why. This section preserves context for future sessions — if requirements change, the team can revisit a specific decision rather than re-exploring the entire design space.

This table is the sanctioned home for rejected alternatives and why they were trimmed. A "we considered X and rejected it because Y" note belongs here, where a fresh author choosing the current design would independently record it. The same note as a defensive aside in body prose ("there is no separate X…") is residue under *docs carry current intent* — the rationale is legitimate; only its placement makes it keep-worthy here and a fossil elsewhere.

| Decision | Chosen | Alternatives Considered | Rationale |
|----------|--------|------------------------|-----------|
| (decision point) | (selected approach) | (brief list) | (why this direction) |

## Open Questions & Future Decisions

### Resolved
1. ✅ Decision made with rationale

### Deferred
1. Decision to make during implementation

## References

- Related docs, external resources
```

## When to Use Narrative vs Structured Format

### Use Narrative Format For:

**Complex constraint interactions** - When multiple requirements interact:

```markdown
## Offline Buffering Strategy

The offline buffer must balance three competing constraints: reliable
persistence across app crashes, efficient upload resumption, and minimal
battery impact during background sync. IndexedDB provides the persistence
foundation, storing metadata including uploadId and progress markers. When
network drops mid-upload, the multipart session preserves server-side state
while the client maintains enough context to resume without re-uploading
completed parts. The 5MB part size represents a deliberate trade-off between
retry cost (smaller parts mean less re-upload on failure) and request overhead
(larger parts mean fewer HTTP round-trips).
```

**Multi-service orchestration** - When showing flow between components:

```markdown
## Processing Pipeline

Order processing flows through three phases, each with distinct error handling
requirements. Phase 1 (validation) tolerates retry since it's idempotent - the
same input always produces the same result. Phase 2 (payment) requires careful
state tracking because payment gateway calls are expensive and partially-
completed transactions should be preserved. Phase 3 (fulfillment) uses database
transactions to ensure atomic updates across Orders, Inventory, and Shipping.
```

### Use Structured Format For:

**API contracts and interfaces**:

```markdown
## API Endpoints

| Endpoint              | Method | Request          | Response        |
| --------------------- | ------ | ---------------- | --------------- |
| `/orders`             | POST   | OrderCreateReq   | OrderConfirm    |
| `/orders/{id}`        | GET    | -                | Order           |
| `/orders/{id}/status` | GET    | -                | OrderStatus     |
```

**Configuration and thresholds**:

```markdown
## Rate Limiting Thresholds

**Per-user limits**:
- Standard tier: 100 requests/minute
- Premium tier: 1000 requests/minute
- Enterprise tier: Custom

**Global limits**:
- Burst: 10,000 requests/second
- Sustained: 5,000 requests/second
```

**State enumerations**:

```markdown
## Order States

- `pending` - Created, awaiting payment
- `paid` - Payment confirmed
- `processing` - Being prepared
- `shipped` - In transit
- `delivered` - Complete
- `cancelled` - Order cancelled
```

## Visual Diagrams

Include ASCII diagrams for UI layouts:

```markdown
## Visual Hierarchy

┌─────────────────────────────────────┐
│ My Orders                     [⚙]   │ ← Top nav
├─────────────────────────────────────┤
│ Active│History│ Returns             │ ← Tab bar
│ ██████│       │                     │
├─────────────────────────────────────┤
│ Order #12345              In Transit│ ← Order card
│ ┌─────────────────────────────────┐ │
│ │ 2 items · $47.99                │ │
│ │ Arrives: Jan 22                 │ │
│ └─────────────────────────────────┘ │
│              [Track Order]          │ ← CTA button
└─────────────────────────────────────┘
```

## Design Decision Documentation

Capture the "why" alongside the "what":

```markdown
## Decision: Payment Provider

**Chosen**: Stripe

**Rationale**: Stripe provides comprehensive fraud detection, handles
PCI compliance, and offers a well-documented API. The 2.9% + $0.30 fee
is competitive and predictable. Their webhook system enables reliable
async processing.

**Alternatives considered**:
- PayPal: Higher fees for our volume, more complex integration
- Square: Better for in-person, weaker for online-only
- Adyen: Enterprise pricing not cost-effective at our scale
```

## Section Depth Guidelines

- Keep sections focused on single concerns
- Use H2 for major sections, H3 for subsections
- If a section exceeds ~100 lines, consider splitting
- Link to separate reference docs for detailed specs
