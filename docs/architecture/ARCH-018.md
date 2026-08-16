# ARCH-018 — Receipt List and Detail Show the Effective (Delivery) Date

**Status:** approved
**Created:** 2026-08-16
**Traces:** REQ-018
**Verified by:** TEST-018

## Summary

Additive change across schema, API, and frontend. `Receipt.effective_date`
(`backend/models.py`) already computes `coalesce(delivery_date,
received_date)` and already drives sort order in
`receipt_service.list_receipts`. It is now also exposed on the two response
schemas that describe a receipt, and the two frontend components that render
a receipt's date switch from `received_date` to the new `effective_date`
field. `received_date` stays on both schemas — it's still true, just not the
right field for "what date is this receipt", and removing it isn't needed for
REQ-018.

## Design

### Backend: expose `effective_date` on the two receipt schemas

`backend/schemas.py` — add one field to each:

```python
class ReceiptSummary(BaseModel):
    """A single entry in the receipt list (AC-003-01, AC-018-01)."""

    id: int
    received_date: datetime
    effective_date: datetime
    from_address: str
    item_count: int
    total_cents: int


class ReceiptDetail(BaseModel):
    """Full receipt with its line items (AC-003-02, AC-018-02)."""

    id: int
    received_date: datetime
    effective_date: datetime
    from_address: str
    items: list[ReceiptItemOut]
    total_cents: int
```

`backend/api/routes.py` — pass the already-existing hybrid property through
at both call sites:

```python
ReceiptSummary(
    id=receipt.id,
    received_date=receipt.received_date,
    effective_date=receipt.effective_date,
    from_address=receipt.from_address,
    item_count=len(receipt.items),
    total_cents=sum(item.line_total_cents for item in receipt.items),
)
```

```python
ReceiptDetail(
    id=receipt.id,
    received_date=receipt.received_date,
    effective_date=receipt.effective_date,
    from_address=receipt.from_address,
    items=items,
    total_cents=sum(item.line_total_cents for item in receipt.items),
)
```

No schema/migration change: `effective_date` is derived at read time from
existing columns (`Receipt.effective_date` is a Python/SQL hybrid property,
not a stored column), exactly like it already is for sorting.

### Frontend: render `effective_date` instead of `received_date`

`frontend/src/types/index.ts` — add the field to both interfaces:

```typescript
export interface ReceiptSummary {
  id: number;
  received_date: string;
  effective_date: string;
  from_address: string;
  item_count: number;
  total_cents: number;
}

export interface ReceiptDetail {
  id: number;
  received_date: string;
  effective_date: string;
  from_address: string;
  items: ReceiptItemOut[];
  total_cents: number;
}
```

`frontend/src/components/Receipts/ReceiptList.tsx` (line 40) — swap the field
read by the existing date cell, no structural change:

```tsx
<span>{new Date(receipt.effective_date).toLocaleDateString("de-DE")}</span>
```

`frontend/src/components/Receipts/ReceiptDetail.tsx` (line 67) — same swap in
the heading:

```tsx
Receipt from {new Date(data.effective_date).toLocaleDateString("de-DE")}
```

### Why not fix this by rewriting `received_date`

Rewriting `received_date` for the affected production rows was considered and
rejected: `received_date` is supposed to mean "when the email arrived in the
mailbox", and for these rows it genuinely does — 2026-06-16/17 is when they
were (re-)polled and (re-)parsed after the Gunicorn-restart incident. That's
true, useful data (e.g. for debugging future reprocessing runs) and
overwriting it would destroy it to paper over a display bug. `delivery_date` /
`effective_date` is the field that already means "the date this receipt is
filed under" — REQ-018 is about showing the field that has always had the
right answer.

### Why not remove `received_date` from the schemas

`received_date` is not read by any frontend code outside the two spots this
change already updates, so keeping it is not risk — but nothing in REQ-018
requires removing it either, and doing so would be an unrelated
schema-narrowing change riding along on a display bug fix (YAGNI).

## Out of Scope

- Any change to how `delivery_date` is parsed or how `received_date` is
  populated at ingest time.
- Backfilling/correcting historical `received_date` values.
- The 0€ "Gratis" price points (confirmed correct, see REQ-018 Context).
