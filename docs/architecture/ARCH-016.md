# ARCH-016 — Idempotent Receipt Parsing Under Concurrent Workers

**Status:** approved
**Created:** 2026-07-10
**Traces:** REQ-016
**Verified by:** TEST-016

## Summary

Targeted change to `backend/services/receipt_service.py`. `parse_pending_receipts`
currently reads the list of pending receipts and then unconditionally stores
items for each one. It is changed to atomically *claim* each receipt
(`processed: False -> True`) immediately before parsing it, so a second caller
racing on the same still-pending receipt observes it as already claimed and
skips it instead of storing a second copy of its items. No schema change, no
new dependency, and no change to `ReceiptParser` or `_store_parsed_receipt`.

## Design

### The race being closed

```
Worker A scheduler tick               Worker B scheduler tick
------------------------              ------------------------
SELECT ... WHERE processed=0          SELECT ... WHERE processed=0
  -> receipt 22 (processed=False)       -> receipt 22 (processed=False)
parse HTML -> 17 items                 parse HTML -> 17 items
INSERT 17 receipt_items                INSERT 17 receipt_items
UPDATE processed=True; COMMIT          UPDATE processed=True; COMMIT
```

Both workers observe `processed == False` before either has written anything,
so both proceed to store. This is the exact sequence that produced 34
`receipt_items` for receipt 22 in production.

### Change: claim-before-parse

A new helper performs the claim as a single atomic statement:

```python
def _claim_receipt_for_processing(db: Session, receipt_id: int) -> bool:
    """Atomically flip one receipt from pending to claimed.

    Returns False if the receipt was no longer processed == False by the time
    this statement ran (i.e. another session already claimed it), so the
    caller must not store items for it.
    """
    result = db.execute(
        update(Receipt)
        .where(Receipt.id == receipt_id, Receipt.processed.is_(False))
        .values(processed=True)
    )
    db.commit()
    return result.rowcount == 1
```

`parse_pending_receipts` is restructured to claim before parsing:

```python
def parse_pending_receipts(db: Session, parser: ReceiptParser | None = None) -> ParseSummary:
    parser = parser or ReceiptParser()
    pending_ids = [
        receipt_id
        for (receipt_id,) in db.query(Receipt.id).filter(Receipt.processed.is_(False)).all()
    ]

    parsed_count = failed_count = item_count = 0

    for receipt_id in pending_ids:
        if not _claim_receipt_for_processing(db, receipt_id):
            continue  # another session already claimed this receipt

        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()

        try:
            html = parser.extract_html(receipt.raw_email_text)
            parsed_receipt = parser.parse(html)
        except ParseError as error:
            logger.error(f"Failed to parse receipt {receipt.id}: {error}")
            receipt.processed = False  # release the claim for a later retry
            db.commit()
            failed_count += 1
            continue

        receipt.delivery_date = parsed_receipt.delivery_date
        _store_parsed_receipt(db, receipt, parsed_receipt)
        _reconcile_total(receipt, parsed_receipt)
        db.commit()

        parsed_count += 1
        item_count += len(parsed_receipt.items)

    logger.info(
        f"Parsing complete: {parsed_count} parsed, {failed_count} failed, {item_count} items stored"
    )
    return ParseSummary(parsed=parsed_count, failed=failed_count, items=item_count)
```

Why this is safe under SQLite: a single `UPDATE ... WHERE ...` is one
statement, and SQLite only allows one writer transaction to commit at a time
(the file lock serializes writers). If two sessions issue the same claim
`UPDATE` concurrently, one blocks until the other commits, then re-evaluates
its `WHERE processed = 0` clause against the now-updated row and affects zero
rows. `rowcount` is therefore a correct, race-free signal of "did I win the
claim," independent of how many processes are issuing it.

The explicit `receipt.processed = True` at the end of the success path is
removed — the claim already set it, and there's nothing left to flip.

### Failure path keeps the receipt retryable

Claiming happens before we know whether the email is even parseable. If
`ReceiptParser.parse()` raises `ParseError`, the claim is released
(`processed = False`) so the existing "malformed receipts are retried on a
later pass" behavior (TC-002-09) is unchanged. This is a deliberate difference
from a naive claim-then-never-release design — without the release, a receipt
that fails to parse once would never be retried again.

### Why not a database-level uniqueness constraint

A `UNIQUE(receipt_id, product_id, order_number)` constraint on `receipt_items`
was considered as a defense-in-depth safety net. It was rejected: receipts 13,
16, and 26 were cross-checked against their raw source emails during the
investigation and confirmed to legitimately contain the same product twice as
separate line items (bought twice in one order). A hard uniqueness constraint
would reject that real data. The atomic claim is a complete fix on its own —
it stops both writers from ever attempting to store the same receipt, so
there is nothing left for a row-level constraint to catch.

### Why not single-instance the scheduler instead

Making only one of the two Gunicorn workers run the `BackgroundScheduler`
(e.g. via a file lock acquired in `lifespan()`) was also considered. It was
rejected as the primary fix because it only protects against *this specific*
topology (N Gunicorn workers on one host) and does nothing for the other
observed trigger — a manual maintenance script calling
`parse_pending_receipts()` directly over SSH while the live scheduler is also
ticking. The atomic claim protects both cases with one change, in one place,
and makes the fix independent of future deployment changes (more workers,
multiple hosts, ad-hoc scripts).

## Out of Scope

- Leader election / single-scheduler topology (see above).
- Schema migration — no column or table changes.
- Re-verifying receipts 13/16/26 beyond the raw-email cross-check already done
  during the investigation.
