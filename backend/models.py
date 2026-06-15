"""
SQLAlchemy ORM models for Picnic Expense Tracker.

Models:
- Receipt: Raw invoice email data
- Product: Catalog of distinct products seen across receipts
- ReceiptItem: A parsed line item, linking a Receipt to a Product
- PriceHistory: Denormalized per-purchase price points for charting
"""

from sqlalchemy import (
    Column,
    ForeignKey,
    Integer,
    String,
    Text,
    DateTime,
    Boolean,
    Index,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class Receipt(Base):
    """Raw Picnic invoice email stored for processing."""

    __tablename__ = "receipts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    message_id = Column(String(255), unique=True, nullable=False, index=True)
    received_date = Column(DateTime, nullable=False)
    from_address = Column(String(255), nullable=False)
    raw_email_text = Column(Text, nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )
    processed = Column(Boolean, default=False, nullable=False, index=True)

    items = relationship("ReceiptItem", back_populates="receipt", cascade="all, delete-orphan")

    # Additional indexes for common queries
    __table_args__ = (Index("idx_created_at", "created_at"),)

    def __repr__(self):
        return (
            f"<Receipt(id={self.id}, message_id={self.message_id}, "
            f"received_date={self.received_date})>"
        )


class Product(Base):
    """A distinct product, identified by its exact name (no fuzzy matching)."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(512), unique=True, nullable=False, index=True)
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    receipt_items = relationship("ReceiptItem", back_populates="product")
    price_history = relationship("PriceHistory", back_populates="product")

    def __repr__(self):
        return f"<Product(id={self.id}, name={self.name!r})>"


class ReceiptItem(Base):
    """A single parsed line item of a receipt."""

    __tablename__ = "receipt_items"

    id = Column(Integer, primary_key=True, autoincrement=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=False, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    quantity = Column(Integer, nullable=False)
    unit_price_cents = Column(Integer, nullable=False)
    line_total_cents = Column(Integer, nullable=False)

    receipt = relationship("Receipt", back_populates="items")
    product = relationship("Product", back_populates="receipt_items")

    def __repr__(self):
        return (
            f"<ReceiptItem(id={self.id}, receipt_id={self.receipt_id}, "
            f"product_id={self.product_id}, quantity={self.quantity})>"
        )


class User(Base):
    """A household account that can log in to the dashboard."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<User(id={self.id}, username={self.username!r})>"


class UserSession(Base):
    """A logged-in session, identified by a hashed token in an httponly cookie."""

    __tablename__ = "sessions"

    token_hash = Column(String(64), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(
        DateTime, nullable=False, default=datetime.utcnow, server_default=func.now()
    )

    user = relationship("User", back_populates="sessions")

    def __repr__(self):
        return f"<UserSession(user_id={self.user_id}, expires_at={self.expires_at})>"


class LoginAttempt(Base):
    """Tracks failed login attempts for rate limiting (lockout)."""

    __tablename__ = "login_attempts"

    username = Column(String(255), primary_key=True)
    failed_count = Column(Integer, nullable=False, default=0)
    first_failed_at = Column(DateTime, nullable=False)
    locked_until = Column(DateTime, nullable=True)

    def __repr__(self):
        return (
            f"<LoginAttempt(username={self.username!r}, failed_count={self.failed_count}, "
            f"locked_until={self.locked_until})>"
        )


class PriceHistory(Base):
    """Denormalized per-purchase price point, for efficient price-trend charts."""

    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, index=True)
    receipt_id = Column(Integer, ForeignKey("receipts.id"), nullable=False)
    unit_price_cents = Column(Integer, nullable=False)
    quantity = Column(Integer, nullable=False)
    recorded_date = Column(DateTime, nullable=False)

    product = relationship("Product", back_populates="price_history")

    __table_args__ = (Index("idx_price_history_product_date", "product_id", "recorded_date"),)

    def __repr__(self):
        return (
            f"<PriceHistory(product_id={self.product_id}, "
            f"unit_price_cents={self.unit_price_cents}, recorded_date={self.recorded_date})>"
        )


class BudgetSetting(Base):
    """Singleton row holding the configured monthly budget (AC-011-06)."""

    __tablename__ = "budget_settings"

    id = Column(Integer, primary_key=True)
    monthly_budget_cents = Column(Integer, nullable=False)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        server_default=func.now(),
    )

    def __repr__(self):
        return f"<BudgetSetting(monthly_budget_cents={self.monthly_budget_cents})>"
