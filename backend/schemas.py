"""
Pydantic response schemas for the REST API.

Traces: ARCH-003
"""

from datetime import datetime

from pydantic import BaseModel


class ReceiptSummary(BaseModel):
    """A single entry in the receipt list (AC-003-01)."""

    id: int
    received_date: datetime
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


class ReceiptDetail(BaseModel):
    """Full receipt with its line items (AC-003-02)."""

    id: int
    received_date: datetime
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
