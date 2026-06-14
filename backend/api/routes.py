"""
Read-only REST API routes for receipts and products.

Traces: ARCH-003
Implements: REQ-003 (AC-003-01 .. AC-003-06)
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.schemas import (
    PaginatedReceipts,
    PriceHistoryPoint,
    ProductOut,
    ProductPriceHistory,
    ReceiptDetail,
    ReceiptItemOut,
    ReceiptSummary,
)
from backend.services import receipt_service

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100

api_router = APIRouter(prefix="/api")


@api_router.get("/receipts", response_model=PaginatedReceipts)
def list_receipts(
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    offset: int = Query(0, ge=0),
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
) -> PaginatedReceipts:
    """List receipts, newest first, with pagination and date-range filtering."""
    receipts, total = receipt_service.list_receipts(db, limit, offset, from_date, to_date)
    items = [
        ReceiptSummary(
            id=receipt.id,
            received_date=receipt.received_date,
            from_address=receipt.from_address,
            item_count=len(receipt.items),
            total_cents=sum(item.line_total_cents for item in receipt.items),
        )
        for receipt in receipts
    ]
    return PaginatedReceipts(items=items, total=total, limit=limit, offset=offset)


@api_router.get("/receipts/{receipt_id}", response_model=ReceiptDetail)
def get_receipt(receipt_id: int, db: Session = Depends(get_db)) -> ReceiptDetail:
    """Get a single receipt with its line items."""
    receipt = receipt_service.get_receipt_with_items(db, receipt_id)
    if receipt is None:
        raise HTTPException(status_code=404, detail="Receipt not found")

    items = [
        ReceiptItemOut(
            product_name=item.product.name,
            quantity=item.quantity,
            unit_price_cents=item.unit_price_cents,
            line_total_cents=item.line_total_cents,
        )
        for item in receipt.items
    ]
    return ReceiptDetail(
        id=receipt.id,
        received_date=receipt.received_date,
        from_address=receipt.from_address,
        items=items,
        total_cents=sum(item.line_total_cents for item in receipt.items),
    )


@api_router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)) -> list[ProductOut]:
    """List all products with how many times each was purchased."""
    return [
        ProductOut(id=product.id, name=product.name, purchase_count=purchase_count)
        for product, purchase_count in receipt_service.list_products(db)
    ]


@api_router.get("/products/{product_id}/price-history", response_model=ProductPriceHistory)
def get_product_price_history(
    product_id: int, db: Session = Depends(get_db)
) -> ProductPriceHistory:
    """Get a product's price history, ordered oldest to newest."""
    result = receipt_service.get_product_with_price_history(db, product_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product, history = result
    points = [
        PriceHistoryPoint(
            date=entry.recorded_date,
            unit_price_cents=entry.unit_price_cents,
            quantity=entry.quantity,
        )
        for entry in history
    ]
    return ProductPriceHistory(product_id=product.id, product_name=product.name, points=points)
