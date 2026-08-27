"""
Aggregation logic for spending statistics and price trends.

Traces: ARCH-004
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import func
from sqlalchemy.orm import Session

from backend.models import PriceHistory, Product, Receipt, ReceiptItem
from backend.services.category_service import CategoryKey

WEEK_PERIOD_EXPR = func.date(Receipt.effective_date, "weekday 0", "-6 days")
MONTH_PERIOD_EXPR = func.strftime("%Y-%m", Receipt.effective_date)


@dataclass
class Summary:
    """Headline spending figures (AC-004-05)."""

    total_spend_cents: int
    receipt_count: int
    distinct_product_count: int
    average_basket_cents: int
    current_month_spend_cents: int


def get_spending_over_time(
    db: Session,
    granularity: str,
    from_date: date | None = None,
    to_date: date | None = None,
    category: CategoryKey | None = None,
) -> list[tuple[str, int]]:
    """Return total spend per period, ordered ascending (AC-004-01, AC-004-06, AC-024-09)."""
    period_expr = WEEK_PERIOD_EXPR if granularity == "week" else MONTH_PERIOD_EXPR

    query = db.query(period_expr.label("period"), func.sum(ReceiptItem.line_total_cents)).join(
        ReceiptItem, ReceiptItem.receipt_id == Receipt.id
    )
    if from_date is not None:
        query = query.filter(func.date(Receipt.effective_date) >= from_date)
    if to_date is not None:
        query = query.filter(func.date(Receipt.effective_date) <= to_date)
    if category is not None:
        query = query.join(Product, ReceiptItem.product_id == Product.id).filter(
            Product.category_key == category
        )

    return query.group_by("period").order_by("period").all()


def get_top_items(
    db: Session, limit: int, category: CategoryKey | None = None
) -> list[tuple[Product, int, int]]:
    """Return the most frequently purchased products, ranked by quantity (AC-004-02,
    AC-024-09)."""
    total_quantity = func.sum(ReceiptItem.quantity)
    total_spend_cents = func.sum(ReceiptItem.line_total_cents)

    query = db.query(Product, total_quantity, total_spend_cents).join(
        ReceiptItem, ReceiptItem.product_id == Product.id
    )
    if category is not None:
        query = query.filter(Product.category_key == category)

    return (
        query.group_by(Product.id)
        .order_by(total_quantity.desc(), total_spend_cents.desc())
        .limit(limit)
        .all()
    )


def get_spending_by_category(
    db: Session,
    from_date: date | None = None,
    to_date: date | None = None,
) -> list[tuple[str | None, int]]:
    """Return total spend per category, highest first (AC-024-07, AC-024-08).

    Products without a category are grouped into their own bucket, keyed None.
    Every receipt item belongs to exactly one product, so the buckets sum to
    the same total as `get_spending_over_time` over the same range.
    """
    total = func.sum(ReceiptItem.line_total_cents)

    query = (
        db.query(Product.category_key, total)
        .join(ReceiptItem, ReceiptItem.product_id == Product.id)
        .join(Receipt, ReceiptItem.receipt_id == Receipt.id)
    )
    if from_date is not None:
        query = query.filter(func.date(Receipt.effective_date) >= from_date)
    if to_date is not None:
        query = query.filter(func.date(Receipt.effective_date) <= to_date)

    return query.group_by(Product.category_key).order_by(total.desc()).all()


def get_price_trend(
    db: Session,
    product_id: int,
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[Product, list[PriceHistory], int, int, int] | None:
    """Return a product's price history with min/max/avg unit price (AC-004-03, AC-004-06)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        return None

    query = db.query(PriceHistory).filter(PriceHistory.product_id == product_id)
    if from_date is not None:
        query = query.filter(func.date(PriceHistory.recorded_date) >= from_date)
    if to_date is not None:
        query = query.filter(func.date(PriceHistory.recorded_date) <= to_date)

    points = query.order_by(PriceHistory.recorded_date.asc()).all()

    if not points:
        return product, points, 0, 0, 0

    prices = [point.unit_price_cents for point in points]
    min_price_cents = min(prices)
    max_price_cents = max(prices)
    avg_price_cents = round(sum(prices) / len(prices))
    return product, points, min_price_cents, max_price_cents, avg_price_cents


def get_spent_for_month(db: Session, month: str) -> int:
    """Return total spend for a given "YYYY-MM" month (AC-004-04, AC-004-06)."""
    spent = (
        db.query(func.coalesce(func.sum(ReceiptItem.line_total_cents), 0))
        .join(Receipt, ReceiptItem.receipt_id == Receipt.id)
        .filter(func.strftime("%Y-%m", Receipt.effective_date) == month)
        .scalar()
    )
    return spent


def get_summary(db: Session, today: date | None = None) -> Summary:
    """Return headline spending figures (AC-004-05, AC-004-06)."""
    today = today or date.today()

    total_spend_cents = db.query(func.coalesce(func.sum(ReceiptItem.line_total_cents), 0)).scalar()
    receipt_count = db.query(func.count(Receipt.id)).scalar()
    distinct_product_count = db.query(func.count(Product.id)).scalar()
    average_basket_cents = round(total_spend_cents / receipt_count) if receipt_count else 0
    current_month_spend_cents = get_spent_for_month(db, today.strftime("%Y-%m"))

    return Summary(
        total_spend_cents=total_spend_cents,
        receipt_count=receipt_count,
        distinct_product_count=distinct_product_count,
        average_basket_cents=average_basket_cents,
        current_month_spend_cents=current_month_spend_cents,
    )
