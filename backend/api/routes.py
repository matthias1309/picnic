"""
Read-only REST API routes for receipts and products.

Traces: ARCH-003
Implements: REQ-003 (AC-003-01 .. AC-003-06)
"""

from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from backend.api.dependencies import get_db
from backend.schemas import (
    BudgetSettingOut,
    BudgetSettingUpdate,
    BudgetStatus,
    CategoryOut,
    CategorySpending,
    PaginatedReceipts,
    PriceHistoryPoint,
    PriceTrend,
    PriceTrendPoint,
    ProductCategoryUpdate,
    ProductOut,
    ProductPriceHistory,
    ReceiptDetail,
    ReceiptItemOut,
    ReceiptSummary,
    SpendingBucket,
    SpendingOverTime,
    SummaryStats,
    TopItem,
)
from backend.services import (
    budget_service,
    category_service,
    receipt_service,
    stats_service,
)
from backend.services.category_service import CategoryKey

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
DEFAULT_TOP_ITEMS_LIMIT = 10
MONTH_PATTERN = r"^\d{4}-\d{2}$"

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
            effective_date=receipt.effective_date,
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
            order_number=item.order_number,
        )
        for item in receipt.items
    ]
    return ReceiptDetail(
        id=receipt.id,
        received_date=receipt.received_date,
        effective_date=receipt.effective_date,
        from_address=receipt.from_address,
        items=items,
        total_cents=sum(item.line_total_cents for item in receipt.items),
    )


@api_router.delete("/receipts/{receipt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(receipt_id: int, db: Session = Depends(get_db)) -> Response:
    """Delete a receipt, its items, and its price history (AC-009-04, AC-009-05)."""
    deleted = receipt_service.delete_receipt(db, receipt_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Receipt not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@api_router.get("/products", response_model=list[ProductOut])
def list_products(db: Session = Depends(get_db)) -> list[ProductOut]:
    """List all products with how many times each was purchased."""
    return [
        ProductOut(
            id=product.id,
            name=product.name,
            purchase_count=purchase_count,
            category_key=product.category_key,
        )
        for product, purchase_count in receipt_service.list_products(db)
    ]


@api_router.get("/categories", response_model=list[CategoryOut])
def list_categories() -> list[CategoryOut]:
    """List the fixed set of product categories (AC-024-06)."""
    return [
        CategoryOut(key=key, label=label) for key, label in category_service.CATEGORY_LABELS.items()
    ]


@api_router.put("/products/{product_id}/category", response_model=ProductOut)
def update_product_category(
    product_id: int,
    payload: ProductCategoryUpdate,
    db: Session = Depends(get_db),
) -> ProductOut:
    """Assign a product's category by hand (AC-024-03, AC-024-10)."""
    product = category_service.set_product_category(db, product_id, payload.category_key)
    if product is None:
        raise HTTPException(status_code=404, detail="Product not found")

    return ProductOut(
        id=product.id,
        name=product.name,
        purchase_count=len(product.receipt_items),
        category_key=product.category_key,
    )


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


@api_router.get("/stats/spending", response_model=SpendingOverTime)
def get_spending(
    granularity: Literal["week", "month"] = "month",
    from_date: date | None = None,
    to_date: date | None = None,
    category: CategoryKey | None = None,
    db: Session = Depends(get_db),
) -> SpendingOverTime:
    """Get total spending grouped by week or month (AC-004-01, AC-024-09)."""
    buckets = stats_service.get_spending_over_time(db, granularity, from_date, to_date, category)
    return SpendingOverTime(
        granularity=granularity,
        buckets=[SpendingBucket(period=period, total_cents=total) for period, total in buckets],
    )


@api_router.get("/stats/top-items", response_model=list[TopItem])
def get_top_items(
    limit: int = Query(DEFAULT_TOP_ITEMS_LIMIT, ge=1, le=MAX_PAGE_SIZE),
    category: CategoryKey | None = None,
    db: Session = Depends(get_db),
) -> list[TopItem]:
    """Get the most frequently purchased products (AC-004-02, AC-024-09)."""
    return [
        TopItem(
            product_id=product.id,
            product_name=product.name,
            total_quantity=total_quantity,
            total_spend_cents=total_spend_cents,
        )
        for product, total_quantity, total_spend_cents in stats_service.get_top_items(
            db, limit, category
        )
    ]


@api_router.get("/stats/price-trend/{product_id}", response_model=PriceTrend)
def get_price_trend(
    product_id: int,
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
) -> PriceTrend:
    """Get a product's price trend with min/max/avg unit price (AC-004-03)."""
    result = stats_service.get_price_trend(db, product_id, from_date, to_date)
    if result is None:
        raise HTTPException(status_code=404, detail="Product not found")

    product, points, min_price_cents, max_price_cents, avg_price_cents = result
    return PriceTrend(
        product_id=product.id,
        product_name=product.name,
        points=[
            PriceTrendPoint(
                date=point.recorded_date,
                unit_price_cents=point.unit_price_cents,
                quantity=point.quantity,
            )
            for point in points
        ],
        min_price_cents=min_price_cents,
        max_price_cents=max_price_cents,
        avg_price_cents=avg_price_cents,
    )


@api_router.put("/settings/budget", response_model=BudgetSettingOut)
def update_budget(
    payload: BudgetSettingUpdate,
    db: Session = Depends(get_db),
) -> BudgetSettingOut:
    """Update the configured monthly budget (AC-011-03, AC-011-05, AC-011-06)."""
    monthly_budget_cents = budget_service.set_monthly_budget_cents(db, payload.monthly_budget_cents)
    return BudgetSettingOut(monthly_budget_cents=monthly_budget_cents)


@api_router.get("/stats/budget", response_model=BudgetStatus)
def get_budget(
    month: str = Query(..., pattern=MONTH_PATTERN),
    db: Session = Depends(get_db),
) -> BudgetStatus:
    """Get configured budget vs. actual spend for a month (AC-004-04, AC-011-06)."""
    spent_cents = stats_service.get_spent_for_month(db, month)
    budget_cents = budget_service.get_monthly_budget_cents(db)
    return BudgetStatus(
        month=month,
        budget_cents=budget_cents,
        spent_cents=spent_cents,
        remaining_cents=budget_cents - spent_cents,
    )


@api_router.get("/stats/by-category", response_model=list[CategorySpending])
def get_spending_by_category(
    from_date: date | None = None,
    to_date: date | None = None,
    db: Session = Depends(get_db),
) -> list[CategorySpending]:
    """Get total spend per category, highest first (AC-024-07, AC-024-08)."""
    return [
        CategorySpending(category_key=category_key, total_cents=total_cents)
        for category_key, total_cents in stats_service.get_spending_by_category(
            db, from_date, to_date
        )
    ]


@api_router.get("/stats/summary", response_model=SummaryStats)
def get_summary(db: Session = Depends(get_db)) -> SummaryStats:
    """Get headline spending figures (AC-004-05)."""
    summary = stats_service.get_summary(db)
    return SummaryStats(
        total_spend_cents=summary.total_spend_cents,
        receipt_count=summary.receipt_count,
        distinct_product_count=summary.distinct_product_count,
        average_basket_cents=summary.average_basket_cents,
        current_month_spend_cents=summary.current_month_spend_cents,
    )
