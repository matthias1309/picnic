# ARCH-012 — Robust Item-Row Detection for the Current Picnic Invoice Format

**Status:** approved
**Created:** 2026-06-16
**Traces:** REQ-012
**Verified by:** TEST-012

## Summary

Targeted change to `backend/imap/parser.py`. The item-row lookup is changed from
an exact, case-sensitive CSS substring selector to a whitespace- and
case-insensitive comparison, and an item row is additionally required to contain
a product image. No other parsing logic changes.

## Design

### Change 1: tolerant row matching

`ReceiptParser.parse` currently does:

```python
rows = soup.select(f'td[style*="{_ITEM_ROW_STYLE}"]')
```

with `_ITEM_ROW_STYLE = "border-bottom:1px solid #ebebeb"`.

This is replaced by a comparison against a normalized form of each `<td>`'s
`style` attribute, where normalization lowercases the value and removes spaces:

```python
def _normalize_style(style: str | None) -> str:
    return (style or "").replace(" ", "").lower()
```

`_ITEM_ROW_STYLE` keeps its human-readable value; it is normalized once with the
same helper so the constant and the candidate styles are compared on equal
footing. This absorbs both observed variations — `border-bottom: 1px` (extra
space) and `#EBEBEB` (uppercase) — without hard-coding either spelling.

### Change 2: an item row must have a product image

Candidate rows are filtered to those containing an `img[alt]`:

```python
rows = [
    cell
    for cell in soup.find_all("td")
    if _ITEM_ROW_STYLE_NORMALIZED in _normalize_style(cell.get("style"))
    and cell.select_one("img[alt]") is not None
]
```

Picnic's summary blocks (`Pfand`, `Eingereichtes Pfand`, `Lieferadresse`) carry
the same `border-bottom` style but have no product image, so this filter
excludes them. Item rows always contain the product image — that image's `alt`
is already how `_parse_item_row` derives the product name — so requiring it adds
no risk of dropping real items.

`_parse_item_row` keeps its existing `img[alt]` guard as a defensive check; with
the new filter it should never trigger, but removing it would weaken the
function's preconditions for no benefit.

### Why not a case-insensitive CSS selector?

CSS attribute selectors support an `i` flag (`[style*="..." i]`) for
case-insensitive matching, which would fix the `#EBEBEB` case but **not** the
`border-bottom: 1px` extra space — the substring still would not match. A
normalized comparison handles both in one place and is easy to reason about.

## Out of Scope

- Order-number extraction (ARCH-013).
- Structural changes from forwarding clients beyond styling (covered by
  ARCH-008's `<tbody>` handling).
- Re-parsing already-imported receipts (manual DB step).
