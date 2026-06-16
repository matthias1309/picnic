# ARCH-013 — Group Receipt Line Items by Picnic Order Number

**Status:** draft
**Created:** 2026-06-16
**Traces:** REQ-013
**Verified by:** TEST-013

## Summary

End-to-end change adding an order number to each line item: parser → ORM model →
service → API schema → frontend. The order number is stored as a plain nullable
string on `receipt_items`; no new table is introduced (KISS, YAGNI for the MVP).

## Design

### Parser (`backend/imap/parser.py`)

- `ParsedItem` gains `order_number: str | None`.
- A module-level regex captures the order number from the section header text:

  ```python
  _ORDER_NUMBER_RE = re.compile(r"Bestellnr\s+(\d{3}-\d{3}-\d{4})")
  ```

- For each item row, the order number is the **nearest preceding** match in
  document order:

  ```python
  def _extract_order_number(self, row: Tag) -> str | None:
      for text in row.find_all_previous(string=_ORDER_NUMBER_RE):
          match = _ORDER_NUMBER_RE.search(text)
          if match:
              return match.group(1)
      return None
  ```

  `find_all_previous` walks earlier nodes closest-first, so the first hit is the
  header the item belongs to. Items before any header return `None`
  (AC-013-02). The cost is bounded by the email size and runs once per item row.

### Model (`backend/models.py`)

`ReceiptItem` gains:

```python
order_number = Column(String(32), nullable=True, index=True)
```

Nullable so existing rows and emails without order numbers stay valid. **Schema
change** — per CLAUDE.md the production SQLite DB is migrated by a human; for the
MVP the column is created via `Base.metadata.create_all` on a fresh DB and a
one-line `ALTER TABLE receipt_items ADD COLUMN order_number VARCHAR(32)` is the
documented manual step for existing databases.

### Service (`backend/services/receipt_service.py`)

`_store_parsed_receipt` passes `order_number=item.order_number` when building
each `ReceiptItem`. `PriceHistory` is unchanged — price trends are per product,
independent of which order a purchase came from.

### API (`backend/schemas.py`, `backend/api/routes.py`)

- `ReceiptItemOut` gains `order_number: str | None = None`.
- The receipt-detail mapping includes `order_number=item.order_number`.

### Frontend (`frontend/src/types`, `ReceiptDetail.tsx`)

- The receipt-item type gains `order_number: string | null`.
- `ReceiptDetail` groups items by `order_number` (preserving first-seen order)
  and renders one section per order with the `Bestellnr` as a heading. A receipt
  with a single distinct value (or all `null`) renders as a single group, so the
  common case looks unchanged apart from an optional heading.

## Out of Scope

- An `orders` table, order-level totals, or per-order statistics (Phase 2+).
- Backfilling order numbers onto already-parsed receipts (manual re-parse).
