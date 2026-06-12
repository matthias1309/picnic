"""
SQLAlchemy ORM models for Picnic Expense Tracker.

Models:
- Receipt: Raw invoice email data
- Product: (Phase 2) extracted products from receipts
- Item: (Phase 2) items in receipts
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Index, func
from sqlalchemy.ext.declarative import declarative_base
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
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow, server_default=func.now())
    processed = Column(Boolean, default=False, nullable=False, index=True)

    # Additional indexes for common queries
    __table_args__ = (
        Index("idx_created_at", "created_at"),
    )

    def __repr__(self):
        return f"<Receipt(id={self.id}, message_id={self.message_id}, received_date={self.received_date})>"
