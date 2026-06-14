# ARCH-008 — Fix Price Extraction for Forwarded Invoice Emails

**Status:** draft
**Created:** 2026-06-14
**Traces:** REQ-008
**Verified by:** TEST-008

## Summary

Small, targeted fix to `backend/imap/parser.py`. `ReceiptParser._extract_prices`
currently finds price rows with `price_table.find_all("tr", recursive=False)`,
which assumes `<tr>` elements are direct children of the price `<table>`. Email
clients that re-render HTML on forward (e.g. Gmail) insert an implicit
`<tbody>` between `<table>` and `<tr>`, causing this lookup to return nothing
and every item to be priced at 0.

## Design

### Change: `_direct_rows` helper

Add a small static helper to `ReceiptParser` that returns a table's row
elements, looking through at most one level of `<tbody>`:

```python
@staticmethod
def _direct_rows(table: Tag) -> list[Tag]:
    """Return a table's <tr> children, looking through an optional <tbody>.

    Some email clients (e.g. Gmail, on forward) wrap a table's <tr> elements
    in an implicit <tbody> that Picnic's original HTML does not have.
    """
    rows = table.find_all("tr", recursive=False)
    if rows:
        return rows

    rows = []
    for tbody in table.find_all("tbody", recursive=False):
        rows.extend(tbody.find_all("tr", recursive=False))
    return rows
```

`_extract_prices` switches from
`price_table.find_all("tr", recursive=False)` to
`self._direct_rows(price_table)`. No other call sites are affected:

- `_parse_item_row`'s row/quantity-badge/name lookups use `select_one` /
  `get_text`, which are recursive and unaffected by `<tbody>`.
- `_extract_stated_total` calls `_extract_prices` and therefore benefits from
  the same fix automatically.

### Why not just use `recursive=True`?

Switching to `find_all("tr", recursive=True)` would also be unaffected by
`<tbody>`, but it would additionally match `<tr>` elements from the *nested*
cent-value table inside each price cell (`<table><tr><td>49</td></tr>...`).
Those rows happen to be filtered out today by the `len(cells) != 2` check, but
relying on that incidental filtering for correctness is fragile and makes the
"two cells = one price row" invariant harder to reason about. The `_direct_rows`
helper keeps the original "row is a direct child of this table (modulo one
`<tbody>`)" semantics, which is what the function actually depends on.

## Out of Scope

- Handling forwarding clients that introduce other structural changes beyond
  `<tbody>` wrapping — none observed so far; revisit if new failures appear.
- Backfilling/re-parsing already-imported zero-price receipts (manual DB step,
  see REQ-008 notes).
