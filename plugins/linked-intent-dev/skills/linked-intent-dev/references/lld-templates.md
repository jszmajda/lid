# LLD Templates Reference

Low-Level Designs (LLDs) document component-specific technical decisions before implementation. LLDs are **pure design documents** — they describe *how* things work, the constraints, trade-offs, and decisions. They do not track implementation status.

Implementation status is tracked in:
- **Spec files** (`docs/specs/`) via `[x]`/`[ ]`/`[D]` markers on EARS specs
- **Planning docs** (`docs/planning/`) via checkboxes for multi-session progress
- **Arrow docs** (`docs/arrows/`) via coverage tables (if using arrow-maintenance skill)

## File Location

Create LLDs in `/docs/llds/` with descriptive names:
- `user-authentication-flow.md`
- `payment-processing-pipeline.md`
- `offline-sync-strategy.md`

## Standard Structure

```markdown
# [Component Name]

**Created**: YYYY-MM-DD
**Status**: Design Phase | Implementation | Complete
**Supersedes**: (if replacing an older doc)

## Context and Design Philosophy

Why this component exists and guiding principles.

## [Major Section 1]

Technical details...

## [Major Section 2]

Technical details...

## Decisions & Alternatives

For each significant design choice, record what was chosen, what was considered, and why. This section preserves context for future sessions — if requirements change, the team can revisit a specific decision rather than re-exploring the entire design space.

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
