# ARCH-014 — Parse the Delivery Date from the Invoice HTML

**Status:** draft
**Created:** 2026-06-16
**Traces:** REQ-014
**Verified by:** TEST-014

## Summary

The receipt date today comes only from the email `Date` header
(`Receipt.received_date`). This change extracts the delivery date stated in the
invoice body ("… Lieferung von Montag 15 Juni 2026") in the parser and makes it
the canonical date a receipt is filed under. A nullable `Receipt.delivery_date`
column is added; `received_date` is kept as email metadata. A single
`effective_date` accessor coalesces the two so all date-based logic (price
history, stats, filters) uses the delivery date when present and falls back to
the email date otherwise (DRY).

## Design

### Parser (`backend/imap/parser.py`)

- `ParsedReceipt` gains `delivery_date: date | None = None`.
- German month names are mapped once at module level:

  ```python
  _GERMAN_MONTHS = {
      "januar": 1, "februar": 2, "märz": 3, "april": 4, "mai": 5, "juni": 6,
      "juli": 7, "august": 8, "september": 9, "oktober": 10, "november": 11,
      "dezember": 12,
  }
  ```

- The delivery sentence is matched tolerantly. The weekday only anchors the
  match and is discarded; an optional period after the day is allowed:

  ```python
  _DELIVERY_DATE_RE = re.compile(
      r"Lieferung von\s+\w+\s+(\d{1,2})\.?\s+([A-Za-zÄÖÜäöüß]+)\s+(\d{4})",
      re.IGNORECASE,
  )
  ```

- `_extract_delivery_date(soup)` searches the normalized body text, looks the
  month name up case-insensitively, and returns a `date` or `None`. An unknown
  month name or an out-of-range day/month returns `None` (never raises), so a
  wording change degrades to the email-date fallback rather than failing the
  whole parse (mirrors the `stated_total` best-effort approach, AC-014-03).
- `parse()` populates `delivery_date` on the returned `ParsedReceipt`.

### Model (`backend/models.py`)

`Receipt` gains:

```python
delivery_date = Column(Date, nullable=True)
```

and a hybrid accessor so the same coalesce works in Python and in SQL:

```python
@hybrid_property
def effective_date(self):
    return self.delivery_date or self.received_date

@effective_date.expression
def effective_date(cls):
    return func.coalesce(cls.delivery_date, cls.received_date)
```

Nullable so existing rows and older invoice formats stay valid. **Schema
change** — per CLAUDE.md the production SQLite DB is migrated by a human; for the
MVP the column is created via `Base.metadata.create_all` on a fresh DB, and
`ALTER TABLE receipts ADD COLUMN delivery_date DATE` is the documented manual
step for existing databases.

### Service (`backend/services/receipt_service.py`)

- `parse_pending_receipts` copies `parsed_receipt.delivery_date` onto
  `receipt.delivery_date` before storing (it stays `None` when not parsed).
- `_store_parsed_receipt` records `PriceHistory.recorded_date =
  receipt.effective_date`, so price points carry the delivery date when known.
- `list_receipts` filters and orders by `Receipt.effective_date` instead of
  `received_date`.

### Statistics (`backend/services/stats_service.py`)

The week/month period expressions and the month/date filters switch from
`Receipt.received_date` to `Receipt.effective_date`:

```python
WEEK_PERIOD_EXPR = func.date(Receipt.effective_date, "weekday 0", "-6 days")
MONTH_PERIOD_EXPR = func.strftime("%Y-%m", Receipt.effective_date)
```

`get_spent_for_month` and the `from_date`/`to_date` filters use
`func.date(Receipt.effective_date)` / `func.strftime("%Y-%m",
Receipt.effective_date)`. A re-delivered May invoice therefore counts in May
(AC-014-06).

## Out of Scope

- Re-dating already-imported receipts (manual re-parse, as REQ-008/012/013).
- Time-of-day precision (date granularity is enough for trends).
- Robust dedup of forwarded emails with a rewritten Message-ID.
- Locales/wordings other than German "Lieferung von …".
