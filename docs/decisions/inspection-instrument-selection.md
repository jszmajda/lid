---
node: high-level-design
---

# Decision: Instrument selection is conversational, not configured

## Context

The HLD's narrowing approach names two kinds of intent work — specifying and inspecting the cascade — each admitting plural instruments: drafting-then-review or elicitation for specification; personal review, zero-context readers, delegated inspectors, or out-of-band review for inspection. Something must determine which instrument a session uses. The obvious mechanism is configuration — a bullet in the instruction file's `## LID` block beside `- Mode:`, declaring the project's posture. The stake: a mechanism too rigid freezes a property that varies moment to moment; one too weak makes the instruments undiscoverable and re-negotiated every session.

## Decision Elements

*Background invariant (constrains every option, decides none): whatever selects the instrument leaves inspection on by default — a mechanism that could silently reach "nothing inspects" would fail the* Every phase is inspected *tenet and is outside the option space.*
- **Fit to the property's variance (major).** Instrument choice varies per session, per artifact, and per moment: the same user elicits one concept, reviews the next document whole, delegates inspection of a mechanical change and reads a risky one line-by-line. A storage mechanism should match the variance of the property it stores (*minimum surface, maximum discipline*).
- **Surface cost (moderate).** Every configuration key is surface: users must learn it, `/update-lid` must reconcile it, docs must define it (*minimum surface, maximum discipline*).
- **Discoverability (moderate).** Users should learn the instruments exist without reading the whole methodology.

## Options in the Domain

### A `## LID` block bullet

A declared per-project posture (for example `- Inspection: delegated`), read the way `- Mode:` is read, defaulting to personal review when the bullet is absent.

- Variance fit: **weak** — a per-project key stores a per-moment property; in practice it is either ignored or pressures sessions toward a posture that does not fit the work at hand.
- Surface cost: **weak** — a new key, a reconcile rule, migration surface.
- Discoverability: **strong** — the key is visible in every instruction file.

### Conversational selection with a stated default

The skill states the default (the human inspects each phase's output at its stop) and offers alternatives at natural moments — an instrument shift when the user's interaction grain changes, delegation when the user asks for it. The choice lives in the session; nothing persists.

- Variance fit: **strong** — the choice is made exactly where it varies.
- Surface cost: **strong** — no key, nothing to reconcile.
- Discoverability: **partial** — carried by the skill's offer language rather than a visible artifact.

### Hybrid: project default plus session override

A `## LID` bullet sets the default posture; sessions override it conversationally.

- Variance fit: **partial** — the override rescues per-moment cases, but the stored default still misdescribes many of them.
- Surface cost: **weak** — the key *and* an override protocol; the most surface of the three options.
- Discoverability: **strong**.

## Selection

Conversational selection with a stated default. It is the only option strong on the major criterion — the choice is made at the moment the property varies — and it costs no surface. The discoverability gap is closed by the skill's own offer language, which names each alternative at the moment it is useful.

Implications: there is nothing persistent for `/update-lid` to reconcile. A user with a standing preference records it as prose in their own instruction file, which the agent reads like any other project guidance. The `lid-experimental` plugin may trial a *declared posture* for review-cadence experiments — a deliberate exception confined to experimental surface; promoting such an experiment into core reopens this decision with evidence in hand.

Turns on *minimum surface, maximum discipline*; the background invariant it preserves is *Every phase is inspected*.
