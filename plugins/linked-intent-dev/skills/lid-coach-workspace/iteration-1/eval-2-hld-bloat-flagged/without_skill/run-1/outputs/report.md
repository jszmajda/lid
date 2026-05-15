# LID Coach Review

I reviewed this project against LID principles. There is **one significant finding: the HLD has abstraction-level bloat**, plus a structural gap that follows from it.

## Finding 1 (Primary): HLD contains LLD- and EARS-level detail

`docs/high-level-design.md` is titled "HLD: Billing System" but most of its content does not belong at the high-level-design layer.

**The HLD should answer "why" and "what shape" — the problem, the architectural decomposition, and the boundaries between components. It should not contain:**

| Section in the HLD | Where it actually belongs | Why |
|---|---|---|
| `## Database Schema` (full `CREATE TABLE` + indexes) | An LLD (`docs/llds/`) | Concrete table layout, column types, and index strategy are low-level design decisions. They change for reasons (performance tuning, new columns) that should not force an HLD edit. |
| `## API Endpoints` (verbs, paths, request/response bodies, status codes) | EARS specs (`docs/specs/`) + an LLD | "Returns 201 with invoice body, 404 if not found" is testable behavior — that is exactly what EARS requirements capture. The contract belongs in specs, the routing/handler design in an LLD. |
| `## Functions` (the full `createInvoice` TypeScript body) | Code (with a `@spec` annotation) | An implementation body in the HLD is the strongest bloat signal. The HLD froze a specific implementation (`uuid()`, `new Date()`, a direct `db.insert`) into the top-of-arrow intent doc. This inverts LID: code should trace *up* to intent, not be *pasted into* it. |

**Why this matters under LID.** The arrow of intent runs HLD → LLD → EARS → Tests → Code. Each layer is more concrete than the one above it. When implementation detail lives in the HLD:

- **Cascades misfire.** Tuning an index or renaming a column is a code/LLD change, but here it would dirty the HLD — the document that's supposed to be the most stable. Every team member rereads the "architecture" doc for a migration-level tweak.
- **Mutation gets noisy.** LID is mutation-not-accumulation. If the HLD holds the literal function body, the body and the real code drift the moment anyone edits the code, and the HLD silently becomes a lie.
- **The "why" is buried.** The only genuine HLD-level content here is `## Problem` ("Customers need to be billed monthly") — and even that is thin. The actual architectural intent (what components exist, what they own, what the invoicing lifecycle is) is absent, crowded out by schema and code.

## Finding 2 (Structural, follows from #1): empty LLD and spec layers

`docs/llds/` and `docs/specs/` contain only `.gitkeep`. The detail that *should* populate them currently lives in the HLD. This isn't a separate problem so much as the other half of Finding 1: the content exists, it's just at the wrong layer. Splitting the HLD fixes both at once.

## Recommended remediation (do not apply without your go-ahead)

This is a coaching review — flagging, not fixing. When you're ready, the LID-correct restructure is:

1. **Slim the HLD** down to: the problem/why, the billing domain model at a conceptual level (Invoice lifecycle: created → issued → paid), the component decomposition (e.g. invoice service, persistence, payment API surface), and the key boundaries/decisions. No SQL, no endpoint tables, no function bodies.
2. **Create `docs/llds/billing.md`** holding the schema (table + index rationale) and the API/handler design.
3. **Create EARS specs in `docs/specs/`** for the observable behaviors, e.g.:
   - `BILL-API-001` — When a client POSTs to `/api/invoices` with a valid body, the system shall create an invoice and return 201 with the invoice body.
   - `BILL-API-002` — When a client GETs `/api/invoices/:id` for a non-existent id, the system shall return 404.
   - `BILL-API-003` — When a client POSTs to `/api/invoices/:id/pay`, the system shall mark the invoice paid and return 200.
4. **Move the `createInvoice` body to code** with a `// @spec BILL-API-001` annotation, deleting it from the HLD.

This re-establishes a clean arrow: HLD intent → LLD design → EARS behavior → annotated code.

## Verdict

**HLD bloat: flagged.** The high-level-design document is operating two layers below its station — it carries database DDL, API contracts, and an implementation body that belong in LLDs, EARS specs, and code respectively. The LLD and spec directories are correspondingly empty. The fix is a downward redistribution of detail along the arrow, summarized above. No files were changed in this review.
