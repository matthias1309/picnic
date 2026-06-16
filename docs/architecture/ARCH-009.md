# ARCH-009 — Delete a Receipt

**Status:** approved
**Created:** 2026-06-15
**Traces:** REQ-009
**Verified by:** TEST-009

## Summary

ARCH-009 adds a single new endpoint, `DELETE /picnic/api/receipts/{receipt_id}`,
and a corresponding `delete_receipt` query function in
`backend/services/receipt_service.py`. On the frontend, `ReceiptDetail.tsx`
gains a "Delete receipt" button that confirms with the user, calls the new
endpoint, and navigates back to the receipt list on success.

---

## Design

### Component Overview

```
┌──────────────────────────────────────────────────────────────┐
│  frontend/src/components/Receipts/ReceiptDetail.tsx          │
│   "Delete receipt" button                                     │
│     → window.confirm(...)                                     │
│     → useDeleteReceipt().mutate(receiptId)                    │
│     → on success: invalidate ["receipts"], navigate("/receipts") │
└──────────────────────────────────────────────────────────────┘
                              ↓ calls
┌──────────────────────────────────────────────────────────────┐
│  frontend/src/hooks/useReceipts.ts                            │
│   useDeleteReceipt() -> useMutation(deleteJson(`/receipts/${id}`)) │
└──────────────────────────────────────────────────────────────┘
                              ↓ HTTP DELETE
┌──────────────────────────────────────────────────────────────┐
│  backend/api/routes.py                                        │
│   DELETE /receipts/{receipt_id}  (mounted under api_router,   │
│   already requires get_current_user — REQ-006)                │
└──────────────────────────────────────────────────────────────┘
                              ↓ calls
┌──────────────────────────────────────────────────────────────┐
│  backend/services/receipt_service.py                          │
│   delete_receipt(db, receipt_id) -> bool                       │
│     - deletes PriceHistory rows where receipt_id == id        │
│     - db.delete(receipt) -> cascades to ReceiptItem rows       │
│     - commit                                                    │
└──────────────────────────────────────────────────────────────┘
```

### Endpoint

| Method | Path | Maps to | Response |
|--------|------|---------|----------|
| DELETE | `/picnic/api/receipts/{receipt_id}` | AC-009-04, AC-009-05 | `204 No Content` / `404` |

### Data Flow — `DELETE /api/receipts/{id}`

```
DELETE /picnic/api/receipts/{receipt_id}
        ↓
routes.delete_receipt_endpoint(receipt_id, db)
        ↓
deleted = receipt_service.delete_receipt(db, receipt_id)
if not deleted: raise HTTPException(404, "Receipt not found")
        ↓
Response(status_code=204)
```

```
receipt_service.delete_receipt(db, receipt_id):
  receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
  if receipt is None:
      return False

  db.query(PriceHistory).filter(PriceHistory.receipt_id == receipt_id).delete()
  db.delete(receipt)   # cascade="all, delete-orphan" removes ReceiptItem rows
  db.commit()
  return True
```

### Frontend Flow — `ReceiptDetail`

```
"Delete receipt" button
  → onClick: if (!window.confirm("Delete this receipt?")) return
  → deleteReceipt.mutate(receiptId)
       mutationFn: () => deleteJson(`/receipts/${receiptId}`)
       onSuccess:
         - queryClient.invalidateQueries({ queryKey: ["receipts"] })
         - navigate("/receipts")
```

### Module Layout

```
backend/
  api/
    routes.py                 # extended: DELETE /receipts/{receipt_id}
  services/
    receipt_service.py        # extended: delete_receipt(db, receipt_id) -> bool

frontend/
  src/
    api/
      client.ts                # extended: deleteJson(path) -> Promise<void>
    hooks/
      useReceipts.ts            # extended: useDeleteReceipt()
    components/
      Receipts/
        ReceiptDetail.tsx        # extended: "Delete receipt" button + confirm
```

---

## Key Decisions

### 1. `DELETE` returns `204 No Content`

**Decision:** Successful deletion returns HTTP 204 with an empty body,
matching standard REST semantics for `DELETE`. Not-found returns `404` with
the existing `{"detail": "Receipt not found"}` shape used by
`GET /api/receipts/{id}` (ARCH-003), for consistency.

**Rationale:** No response body is needed by the frontend (it navigates away
on success); reusing the existing 404 shape keeps the error contract
consistent across the receipts endpoints.

### 2. `PriceHistory` rows are deleted explicitly by the service

**Decision:** `delete_receipt` issues a bulk `DELETE` on `price_history` rows
matching `receipt_id` before deleting the `Receipt` row.

**Rationale:** `PriceHistory` has a `receipt_id` foreign key (ARCH-002) but no
ORM relationship back to `Receipt` and no DB-level `ON DELETE CASCADE`.
Without this step, deleted receipts would leave orphaned price-history points
that still show up in `GET /api/products/{id}/price-history` and
`GET /api/stats/price-trend/{id}` (REQ-003, REQ-004), silently corrupting
price trends. `ReceiptItem` rows do not need special handling — the existing
`cascade="all, delete-orphan"` on `Receipt.items` (ARCH-002) handles them.

### 3. Confirmation via `window.confirm`

**Decision:** The frontend uses the browser's built-in `window.confirm()`
dialog rather than a custom modal component.

**Rationale:** KISS/YAGNI — this is a single, low-frequency, destructive
action in a single-user app. A custom modal component would duplicate
`window.confirm`'s behavior for no functional benefit. `window.confirm` is
straightforward to mock in Vitest tests (`vi.spyOn(window, "confirm")`).

### 4. No new Pydantic response schema

**Decision:** No new schema is added to `backend/schemas.py`; the endpoint
returns `Response(status_code=204)` with no body.

**Rationale:** A 204 response has no body by definition; introducing an empty
schema would add nothing.

---

## Out of Scope

- Bulk deletion endpoints (`DELETE /api/receipts?ids=...`) — YAGNI for MVP.
- Deleting/cleaning up `Product` rows left with zero `receipt_items` after a
  receipt is deleted (REQ-009 Notes).
- Soft-delete / undo — out of scope per REQ-009.
- Custom confirmation modal component — `window.confirm` per Key Decision 3.
</content>
