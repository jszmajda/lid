# HLD: Billing System

## Problem

Customers need to be billed monthly.

## Database Schema

```sql
CREATE TABLE invoices (
  id UUID PRIMARY KEY,
  customer_id UUID NOT NULL REFERENCES customers(id),
  amount_cents BIGINT NOT NULL,
  currency CHAR(3) NOT NULL,
  issued_at TIMESTAMPTZ NOT NULL,
  paid_at TIMESTAMPTZ
);

CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoices_unpaid ON invoices(customer_id) WHERE paid_at IS NULL;
```

## API Endpoints

- `POST /api/invoices` — create an invoice. Body: `{customer_id, amount_cents, currency}`. Returns 201 with invoice body.
- `GET /api/invoices/:id` — fetch by id. Returns 200 with invoice body, 404 if not found.
- `POST /api/invoices/:id/pay` — mark as paid. Body: `{paid_at}`. Returns 200.

## Functions

```typescript
export async function createInvoice(customerId: string, amountCents: number, currency: string): Promise<Invoice> {
  const id = uuid();
  const issuedAt = new Date();
  await db.insert('invoices', { id, customer_id: customerId, amount_cents: amountCents, currency, issued_at: issuedAt });
  return { id, customerId, amountCents, currency, issuedAt };
}
```
