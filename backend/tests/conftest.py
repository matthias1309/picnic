"""
Shared pytest fixtures for Picnic backend tests.

Fixtures:
- db_session: In-memory SQLite session for integration tests
- mock_imap: Mocked imaplib.IMAP4_SSL for unit tests
- test_email_message: Sample email.Message for test data
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from email.message import EmailMessage
from datetime import datetime


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

    # TODO: Create tables (import models, run Base.metadata.create_all(engine))
    # from backend.models import Base
    # Base.metadata.create_all(engine)

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    yield session

    session.close()


# Mock IMAP server
@pytest.fixture
def mock_imap():
    """
    Provides a mocked imaplib.IMAP4_SSL for unit tests.

    Usage:
        def test_something(mock_imap):
            mock_imap.login.return_value = None  # simulate successful login
            mock_imap.select.return_value = (b'OK', [b'5'])  # 5 emails in INBOX
    """
    from unittest.mock import MagicMock
    return MagicMock()


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


# Temp .env file for config tests
@pytest.fixture
def tmp_env_file(tmp_path):
    """
    Provides a temporary .env file for testing settings loading.

    Usage:
        def test_something(tmp_env_file):
            env_file = tmp_env_file
            # env_file is a Path object
            # Write test values: env_file.write_text("IMAP_HOST=localhost\n...")
    """
    env_file = tmp_path / ".env"
    return env_file
