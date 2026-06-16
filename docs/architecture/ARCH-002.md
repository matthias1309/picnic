# ARCH-002 — HTML Email Parsing and Structured Receipt Storage

**Status:** approved  
**Created:** 2026-06-13  
**Traces:** REQ-002  
**Verified by:** TEST-002

## Summary

ARCH-002 defines the backend architecture for turning the raw Picnic invoice
emails (stored by REQ-001 in `receipts.raw_email_text`, `processed = False`) into
normalized, queryable data. A dedicated scheduled task picks up unprocessed
receipts, extracts the HTML invoice table with BeautifulSoup, and persists line
items, a product catalog, and a denormalized price-history table. The design
emphasizes resilience (one bad email never blocks the rest), idempotency
(receipts are parsed exactly once), and monetary correctness (integer cents).

---

## Design

### Component Overview

```
┌──────────────────────────────────────────────────────────────┐
│  FastAPI Lifespan (backend/main.py)                          │
│   APScheduler jobs:                                           │
│    - poll_emails_task()    (REQ-001, every POLLING_INTERVAL) │
│    - parse_receipts_task() (REQ-002, every PARSE_INTERVAL)   │  ← new
└──────────────────────────────────────────────────────────────┘
                              ↓ calls
┌──────────────────────────────────────────────────────────────┐
│  backend/services/receipt_service.py                         │
│   parse_pending_receipts(db) -> ParseSummary                 │
│    1. query receipts WHERE processed = False                 │
│    2. for each receipt: parse + persist in its own txn       │
│    3. set processed = True on success; log+continue on error │
└──────────────────────────────────────────────────────────────┘
                              ↓ uses
┌──────────────────────────────────────────────────────────────┐
│  backend/imap/parser.py — ReceiptParser                      │
│   - extract_html(raw_email_text) -> str                      │
│   - parse(html, received_date) -> ParsedReceipt              │
│       ParsedReceipt = { items: [ParsedItem], stated_total }  │
│       ParsedItem    = { name, quantity, unit_price_cents,    │
│                         line_total_cents }                   │
└──────────────────────────────────────────────────────────────┘
                              ↓ persists
┌──────────────────────────────────────────────────────────────┐
│  backend/models.py                                           │
│   Receipt (REQ-001) ──1:N──> ReceiptItem ──N:1──> Product   │
│                              ReceiptItem ──1:1──> PriceHistory│
└──────────────────────────────────────────────────────────────┘
```

### Data Flow

```
parse_receipts_task (APScheduler, every PARSE_INTERVAL)
        ↓
parse_pending_receipts(db)
        ↓
  receipts = db.query(Receipt).filter(Receipt.processed == False).all()
        ↓ for each receipt
  ┌─────────────────────────────────────────────┐
  │ try:                                         │
  │   html  = parser.extract_html(raw)           │
  │   parsed = parser.parse(html, recv_date)     │
  │   for item in parsed.items:                   │
  │     product = get_or_create_product(name)     │
  │     add ReceiptItem(receipt, product, ...)    │
  │     add PriceHistory(product, price, date)    │
  │   reconcile(parsed)        # AC-002-06 warn   │
  │   receipt.processed = True                     │
  │   db.commit()              # per-receipt txn   │
  │ except ParseError as e:                        │
  │   db.rollback()                                │
  │   log.error(receipt.id, reason)                │
  │   continue   # processed stays False           │
  └─────────────────────────────────────────────┘
        ↓
  return ParseSummary(parsed=N, failed=M, items=K)
```

### Database Schema (new tables)

All monetary values are stored as **integer cents** (e.g. €3.49 → `349`) to avoid
floating-point rounding errors when summing. Formatting to currency strings is a
presentation concern handled in REQ-003/REQ-005.

**Table: `products`**

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | Integer | PK, autoincrement | Unique product ID |
| `name` | String(512) | UNIQUE, NOT NULL, indexed | Exact product name (dedup key) |
| `created_at` | DateTime | NOT NULL, default now | First seen |

**Table: `receipt_items`**

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | Integer | PK, autoincrement | Unique item ID |
| `receipt_id` | Integer | FK→receipts.id, NOT NULL, indexed | Owning receipt |
| `product_id` | Integer | FK→products.id, NOT NULL, indexed | Referenced product |
| `quantity` | Integer | NOT NULL | Units purchased (see decision 4) |
| `unit_price_cents` | Integer | NOT NULL | Price per unit, in cents |
| `line_total_cents` | Integer | NOT NULL | quantity × unit price, in cents |

**Table: `price_history`**

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | Integer | PK, autoincrement | Unique point ID |
| `product_id` | Integer | FK→products.id, NOT NULL, indexed | Product |
| `receipt_id` | Integer | FK→receipts.id, NOT NULL | Source receipt |
| `unit_price_cents` | Integer | NOT NULL | Price per unit at that date |
| `quantity` | Integer | NOT NULL | Quantity on that receipt |
| `recorded_date` | DateTime | NOT NULL, indexed | Receipt received_date (for trends) |

**Indexes:**
- `idx_product_name`: `products(name)` — get-or-create lookup
- `idx_receipt_items_receipt`: `receipt_items(receipt_id)` — list a receipt's items
- `idx_receipt_items_product`: `receipt_items(product_id)` — top-items stats
- `idx_price_history_product_date`: `price_history(product_id, recorded_date)` — trend queries

**Relationships:**
- `Receipt 1—N ReceiptItem` (`cascade="all, delete-orphan"`)
- `Product 1—N ReceiptItem`
- `Product 1—N PriceHistory`
- `Receipt 1—N PriceHistory`

> **Note:** `price_history` is intentionally denormalized (it duplicates
> quantity/price from `receipt_items`) per CLAUDE.md, to keep trend/chart queries
> simple and fast without joining through `receipt_items`.

### Parser (`backend/imap/parser.py`)

```python
# Pseudo-code; concrete cases defined in TEST-002

class ParseError(Exception):
    """Raised when an email does not match the expected invoice structure."""


@dataclass(frozen=True)
class ParsedItem:
    name: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int


@dataclass(frozen=True)
class ParsedReceipt:
    items: list[ParsedItem]
    stated_total_cents: int | None  # order total from email, if present


class ReceiptParser:
    def extract_html(self, raw_email_text: str) -> str:
        """Return the text/html MIME part of the raw email, or raise ParseError."""

    def parse(self, html: str, received_date: datetime) -> ParsedReceipt:
        """Parse the invoice table into structured items. Raise ParseError if the
        expected table/columns are absent."""

    @staticmethod
    def _to_cents(price_text: str) -> int:
        """Convert '3,49 €' / '€3.49' to integer cents. Raise ParseError on junk."""
```

### Service (`backend/services/receipt_service.py`)

```python
@dataclass
class ParseSummary:
    parsed: int
    failed: int
    items: int


def parse_pending_receipts(db: Session) -> ParseSummary:
    """Parse all receipts with processed == False. One transaction per receipt so
    a single failure never rolls back successful ones (AC-002-05)."""


def _get_or_create_product(db: Session, name: str) -> Product:
    """Exact-name lookup; create if absent (AC-002-02). No fuzzy matching (MVP)."""
```

### Configuration (additions to `.env`)

```bash
PARSE_INTERVAL=1800   # Seconds between parse runs (default 30 min, matches polling)
```

### Error Handling & Resilience

| Scenario | Behaviour |
|----------|-----------|
| HTML part missing / unparsable structure | `ParseError`; log `receipt.id` + reason; `processed` stays False; continue (AC-002-05) |
| Price cell cannot be converted to cents | `ParseError` for that receipt; rolled back; continue |
| Computed line-total sum ≠ stated total | Log a **warning**, still commit (AC-002-06) — totals are a sanity check, not a hard failure |
| DB write fails mid-receipt | Per-receipt `db.rollback()`; that receipt remains unprocessed; next run retries |
| No pending receipts | Return `ParseSummary(0, 0, 0)`; no-op |

---

## Key Decisions

### 1. Separate parse task vs. inline in polling

**Decision:** A dedicated `parse_receipts_task()` scheduled independently, picking
up `processed == False` receipts.

**Rationale:** Single Responsibility — polling and parsing fail independently and
can be retried/tuned separately. A parser bug never blocks ingestion, and emails
already in the DB (including pre-existing ones) get parsed regardless of polling.
Slightly more orchestration than inlining, accepted for the decoupling.

### 2. Integer cents for money

**Decision:** Store all amounts as integer cents.

**Rationale:** Exact integer arithmetic for sums and budgets; no float rounding
drift. Conversion happens once at parse time (`_to_cents`); presentation
formatting is a frontend concern. Alternative `Numeric(10,2)` is also exact but
adds Decimal handling throughout for no MVP benefit.

### 3. Per-receipt transaction (idempotency + isolation)

**Decision:** Commit after each receipt, setting `processed = True` in the same
transaction as its items.

**Rationale:** Guarantees AC-002-04 (parse exactly once) and AC-002-05 (one bad
email does not discard good ones). Re-runs are safe: processed receipts are
filtered out up front.

### 4. Exact product matching; integer quantity (MVP)

**Decision:** `_get_or_create_product` matches on exact name (per CLAUDE.md
"no fuzzy matching"). `quantity` is an integer for MVP.

**Rationale:** Matches MVP scope. Fractional/weight-based quantities (e.g. 0.5 kg)
are an open question (see below); if confirmed needed, `quantity` becomes a
`quantity_milli` integer or a separate unit field — deferred to keep MVP simple.

### 5. Denormalized `price_history`

**Decision:** Keep `price_history` as a standalone table duplicating price/qty.

**Rationale:** Per CLAUDE.md, enables efficient charting (REQ-004) without joining
through `receipt_items`. Write cost is trivial (one extra row per item).

---

## Out of Scope

- **Fuzzy product matching / renamed-product merging** → exact name only (Phase 2+).
- **Parser versioning / re-parse of already-processed receipts** → Phase 2+.
- **Deposit (Pfand) / discount modelling** → see open questions; MVP treats them as
  ordinary line items unless TEST-002 fixtures dictate otherwise.
- **Multi-language / alternative invoice layouts** → current Picnic.de format only.
- **REST exposure of parsed data** → REQ-003.
- **Statistics/aggregation** → REQ-004.

---

## Open Questions

1. **Deposits (Pfand) and discounts** — separate `ReceiptItem` kind, or signed
   `line_total_cents` (negative for discounts)? Resolve with real fixtures in
   TEST-002. Current lean: keep them as ordinary items with their natural sign.
2. **Fractional quantities** — does Picnic ever bill by weight (0.5 kg)? If yes,
   revisit `quantity` type (see decision 4) before implementation.
3. **Unit vs. line price source** — does the invoice state unit price, line total,
   or both? Parser must derive the missing one; confirm against fixtures.
4. **Stated total location** — exact HTML element/label for the order total used in
   AC-002-06 reconciliation; confirm against fixtures.
5. **Parser failure visibility** — is `processed = False` enough, or do we add a
   `parse_error` column / `parse_attempts` counter to avoid retrying a permanently
   broken email forever? MVP: leave False; reconsider if it causes log noise.
