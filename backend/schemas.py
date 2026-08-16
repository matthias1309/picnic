"""
Pydantic response schemas for the REST API.

Traces: ARCH-003, ARCH-006
"""

from datetime import datetime

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Request body for POST /api/auth/login (AC-006-01, AC-006-02)."""

    username: str
    password: str


class UserOut(BaseModel):
    """The currently authenticated user (AC-006-01, AC-006-03)."""

    id: int
    username: str


class ReceiptSummary(BaseModel):
    """A single entry in the receipt list (AC-003-01, AC-018-01)."""

    id: int
    received_date: datetime
    effective_date: datetime
    from_address: str
    item_count: int
    total_cents: int


class PaginatedReceipts(BaseModel):
    """Paginated response for GET /api/receipts (AC-003-01, AC-003-06)."""

    items: list[ReceiptSummary]
    total: int
    limit: int
    offset: int


class ReceiptItemOut(BaseModel):
    """A single line item within a receipt detail (AC-003-02)."""

    product_name: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int
    order_number: str | None = None


class ReceiptDetail(BaseModel):
    """Full receipt with its line items (AC-003-02, AC-018-02)."""

    id: int
    received_date: datetime
    effective_date: datetime
    from_address: str
    items: list[ReceiptItemOut]
    total_cents: int


class ProductOut(BaseModel):
    """A product with its purchase count (AC-003-03)."""

    id: int
    name: str
    purchase_count: int


class PriceHistoryPoint(BaseModel):
    """A single point in a product's price history (AC-003-04)."""

    date: datetime
    unit_price_cents: int
    quantity: int


class ProductPriceHistory(BaseModel):
    """Time-ordered price history for a product (AC-003-04)."""

    product_id: int
    product_name: str
    points: list[PriceHistoryPoint]


class SpendingBucket(BaseModel):
    """A single period's total spend (AC-004-01)."""

    period: str
    total_cents: int


class SpendingOverTime(BaseModel):
    """Spending grouped by period (AC-004-01)."""

    granularity: str
    buckets: list[SpendingBucket]


class TopItem(BaseModel):
    """A frequently purchased product with its totals (AC-004-02)."""

    product_id: int
    product_name: str
    total_quantity: int
    total_spend_cents: int


class PriceTrendPoint(BaseModel):
    """A single point in a product's price trend (AC-004-03)."""

    date: datetime
    unit_price_cents: int
    quantity: int


class PriceTrend(BaseModel):
    """Price trend time series with summary statistics (AC-004-03)."""

    product_id: int
    product_name: str
    points: list[PriceTrendPoint]
    min_price_cents: int
    max_price_cents: int
    avg_price_cents: int


class BudgetStatus(BaseModel):
    """Configured budget vs. actual spend for a month (AC-004-04)."""

    month: str
    budget_cents: int
    spent_cents: int
    remaining_cents: int


class BudgetSettingUpdate(BaseModel):
    """Request body for PUT /api/settings/budget (AC-011-03, AC-011-05)."""

    monthly_budget_cents: int = Field(ge=0)


class BudgetSettingOut(BaseModel):
    """Response body for PUT /api/settings/budget (AC-011-03)."""

    monthly_budget_cents: int


class SummaryStats(BaseModel):
    """Headline spending figures (AC-004-05)."""

    total_spend_cents: int
    receipt_count: int
    distinct_product_count: int
    average_basket_cents: int
    current_month_spend_cents: int
