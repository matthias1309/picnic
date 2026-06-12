"""
Shared pytest fixtures for Picnic backend tests.

Fixtures:
- db_session: In-memory SQLite session for integration tests
- test_email_message: Sample email.Message for test data
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from email.message import EmailMessage
from datetime import datetime

from backend.models import Base


# In-memory SQLite for integration tests
@pytest.fixture
def db_session() -> Session:
    """
    Provides an in-memory SQLite database session for tests.

    Usage:
        def test_something(db_session):
            # db_session is ready to use
            db_session.query(Receipt).all()
    """
    # Create in-memory SQLite
    engine = create_engine("sqlite:///:memory:")

    # Create all tables from models
    Base.metadata.create_all(bind=engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()


# Sample email message
@pytest.fixture
def test_email_message() -> EmailMessage:
    """
    Provides a sample EmailMessage with typical Picnic invoice headers.

    Usage:
        def test_something(test_email_message):
            msg = test_email_message
            assert msg['Message-ID'] == 'test123@picnic.app'
    """
    msg = EmailMessage()
    msg['Message-ID'] = 'test123@picnic.app'
    msg['From'] = 'noreply@picnic.app'
    msg['To'] = 'user@example.com'
    msg['Subject'] = 'Your Picnic Invoice #12345'
    msg['Date'] = 'Wed, 12 Jun 2026 14:30:00 +0200'
    msg.set_content('Invoice details here...')
    return msg
