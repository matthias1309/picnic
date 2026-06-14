"""
Shared pytest fixtures for Picnic backend tests.

Fixtures:
- db_session: In-memory SQLite session for integration tests
- test_email_message: Sample email.Message for test data
- picnic_receipt_html: HTML of a sample "Dein Bon" invoice
- picnic_receipt_malformed_html: HTML without a recognizable invoice structure
- make_raw_email: builds a raw MIME message string with a given HTML body
- client: FastAPI TestClient backed by the db_session fixture's database
"""

from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from email.message import EmailMessage
from fastapi.testclient import TestClient

from backend.database import get_db
from backend.main import app
from backend.models import Base

FIXTURES_DIR = Path(__file__).parent / "fixtures"


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
    # Create in-memory SQLite. check_same_thread=False + StaticPool are required
    # because the FastAPI TestClient (via the `client` fixture) executes requests
    # on a different thread, and in-memory SQLite databases are per-connection.
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

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
    msg["Message-ID"] = "test123@picnic.app"
    msg["From"] = "noreply@picnic.app"
    msg["To"] = "user@example.com"
    msg["Subject"] = "Your Picnic Invoice #12345"
    msg["Date"] = "Wed, 12 Jun 2026 14:30:00 +0200"
    msg.set_content("Invoice details here...")
    return msg


@pytest.fixture
def picnic_receipt_html() -> str:
    """HTML body of a sample Picnic "Dein Bon" invoice (anonymized excerpt)."""
    return (FIXTURES_DIR / "picnic_receipt.html").read_text(encoding="utf-8")


@pytest.fixture
def picnic_receipt_malformed_html() -> str:
    """HTML without any recognizable Picnic invoice item rows."""
    return (FIXTURES_DIR / "picnic_receipt_malformed.html").read_text(encoding="utf-8")


@pytest.fixture
def make_raw_email():
    """Factory for building a raw MIME email string with an HTML body."""

    def _make(html: str | None, subject: str = "Dein Bon") -> str:
        msg = EmailMessage()
        msg["Message-ID"] = "bon@picnic.app"
        msg["From"] = "info@service.picnic.de"
        msg["To"] = "user@example.com"
        msg["Subject"] = subject
        msg["Date"] = "Mon, 1 Jun 2026 20:45:00 +0200"
        msg.set_content("Hier ist der Bon zu deiner Bestellung.")
        if html is not None:
            msg.add_alternative(html, subtype="html")
        return msg.as_string()

    return _make


@pytest.fixture
def client(db_session: Session) -> TestClient:
    """FastAPI TestClient with the `get_db` dependency overridden to use db_session."""

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.pop(get_db, None)
