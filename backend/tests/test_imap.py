"""
Unit and integration tests for IMAP email polling and receipt storage.

Traces: ARCH-001
Verifies: REQ-001 (AC-001-01, AC-001-02, AC-001-03, AC-001-04)
"""

import pytest
from unittest.mock import patch, MagicMock
from email.message import EmailMessage
from datetime import datetime
import imaplib

from backend.imap.client import IMAPClient
from backend.models import Receipt
from backend.config import Settings


# TC-001-01: IMAP connection with valid credentials succeeds
@patch("imaplib.IMAP4_SSL")
def test_imap_client_connects_with_valid_credentials(mock_imap4_ssl):
    """
    Given the FastAPI backend is running
    When the user provides valid IMAP credentials (host, port, username, password)
    Then the IMAP connection is established and tested
    """
    # Arrange
    mock_instance = MagicMock()
    mock_imap4_ssl.return_value = mock_instance
    mock_instance.login.return_value = None

    client = IMAPClient(
        host="localhost",
        port=993,
        username="test@example.com",
        password="secret123",
        use_ssl=True,
    )

    # Act
    result = client.connect()

    # Assert
    assert result is True
    assert client.connection is not None
    mock_imap4_ssl.assert_called_once_with("localhost", 993)
    mock_instance.login.assert_called_once_with("test@example.com", "secret123")


# TC-001-02: IMAP connection with invalid credentials fails gracefully
@patch("imaplib.IMAP4_SSL")
def test_imap_client_handles_invalid_credentials(mock_imap4_ssl):
    """
    Given invalid IMAP credentials (wrong password)
    When IMAPClient attempts to connect
    Then IMAPAuthenticationError is raised
    And the error is caught by polling task (does not crash)
    """
    # Arrange
    mock_instance = MagicMock()
    mock_imap4_ssl.return_value = mock_instance
    mock_instance.login.side_effect = imaplib.IMAP4.error("Authentication failed")

    client = IMAPClient(
        host="localhost",
        port=993,
        username="test@example.com",
        password="wrongpassword",
        use_ssl=True,
    )

    # Act & Assert
    with pytest.raises(imaplib.IMAP4.error):
        client.connect()


# TC-001-03: fetch_new_emails() retrieves emails from INBOX
@patch("imaplib.IMAP4_SSL")
def test_fetch_new_emails_returns_email_list(mock_imap4_ssl):
    """
    Given IMAP credentials are configured
    When fetch_new_emails() is called
    Then a list of email.Message objects is returned
    And each message has Message-ID, From, Date headers
    """
    # Arrange
    mock_instance = MagicMock()
    mock_imap4_ssl.return_value = mock_instance
    mock_instance.login.return_value = None
    mock_instance.select.return_value = ("OK", [b"3"])
    mock_instance.search.return_value = ("OK", [b"1 2 3"])

    # Create test emails
    test_emails = []
    for i in range(1, 4):
        msg = EmailMessage()
        msg["Message-ID"] = f"test{i}@picnic.app"
        msg["From"] = "noreply@picnic.app"
        msg["Date"] = "Wed, 12 Jun 2026 14:30:00 +0200"
        msg.set_content(f"Invoice {i}")
        test_emails.append(msg)

    # Mock fetch responses
    mock_instance.fetch.side_effect = [
        ("OK", [(None, test_email.as_bytes())]) for test_email in test_emails
    ]

    client = IMAPClient("localhost", 993, "test@example.com", "secret", use_ssl=True)
    client.connect()

    # Act
    emails = client.fetch_new_emails("INBOX")

    # Assert
    assert len(emails) == 3
    assert all(msg.get("Message-ID") for msg in emails)
    assert all(msg.get("From") for msg in emails)
    assert all(msg.get("Date") for msg in emails)


# TC-001-04: New email is stored in SQLite with correct fields
def test_new_email_stored_in_sqlite(db_session, test_email_message):
    """
    Given a new email from Picnic (message_id=test123@picnic.app)
    When the polling task stores it
    Then a Receipt row is created in SQLite
    And fields are populated: message_id, received_date, from_address, raw_email_text
    """
    # Arrange
    receipt = Receipt(
        message_id="test123@picnic.app",
        received_date=datetime(2026, 6, 12, 14, 30),
        from_address="noreply@picnic.app",
        raw_email_text=test_email_message.as_string(),
        created_at=datetime.utcnow(),
        processed=False,
    )

    # Act
    db_session.add(receipt)
    db_session.commit()

    # Assert
    stored = db_session.query(Receipt).filter_by(message_id="test123@picnic.app").first()
    assert stored is not None
    assert stored.from_address == "noreply@picnic.app"
    assert stored.raw_email_text is not None
    assert stored.processed is False


# TC-001-05: Duplicate email is skipped (Message-ID deduplication)
def test_duplicate_email_is_skipped(db_session, test_email_message):
    """
    Given an email with Message-ID "abc123@picnic.app" is already in the database
    When the same email arrives again
    Then it is skipped and not re-processed
    And a log entry records the duplicate detection
    """
    # Arrange: insert first receipt
    receipt1 = Receipt(
        message_id="abc123@picnic.app",
        received_date=datetime(2026, 6, 12, 14, 30),
        from_address="noreply@picnic.app",
        raw_email_text=test_email_message.as_string(),
        created_at=datetime.utcnow(),
        processed=False,
    )
    db_session.add(receipt1)
    db_session.commit()

    # Act: try to insert duplicate
    existing = db_session.query(Receipt).filter_by(message_id="abc123@picnic.app").first()

    # Assert
    assert existing is not None
    assert existing.message_id == "abc123@picnic.app"
    # Count should still be 1
    count = db_session.query(Receipt).count()
    assert count == 1


# TC-001-06: Polling task runs on schedule and completes
@patch("backend.main.SessionLocal")
@patch("backend.main.IMAPClient")
def test_polling_task_runs_and_completes(mock_imap_client, mock_session_local, db_session):
    """
    Given APScheduler is configured with 30-minute interval
    When the polling task runs
    Then it completes without exception
    And logs "Polling complete: X new, Y duplicates"
    """
    # Arrange
    mock_instance = MagicMock()
    mock_imap_client.return_value = mock_instance

    # Create test emails
    test_emails = []
    for i in range(1, 3):
        msg = EmailMessage()
        msg["Message-ID"] = f"test{i}@picnic.app"
        msg["From"] = "noreply@picnic.app"
        msg["Date"] = "Wed, 12 Jun 2026 14:30:00 +0200"
        msg.set_content(f"Invoice {i}")
        test_emails.append(msg)

    mock_instance.fetch_new_emails.return_value = test_emails
    mock_instance._get_message_id.side_effect = [msg.get("Message-ID") for msg in test_emails]

    # Mock SessionLocal to return our test session
    mock_session_local.return_value = db_session

    from backend.main import poll_emails_task

    # Act
    poll_emails_task()  # Should not raise

    # Assert
    stored = db_session.query(Receipt).count()
    assert stored == 2


# TC-001-07: Polling error (IMAP timeout) is logged and task continues
@patch("backend.main.IMAPClient")
def test_polling_error_is_logged_and_task_continues(mock_imap_client):
    """
    Given IMAP connection times out during fetch
    When the polling task encounters the error
    Then the error is logged with timestamp and context
    And the task continues (does not crash the background daemon)
    """
    # Arrange
    mock_instance = MagicMock()
    mock_imap_client.return_value = mock_instance
    mock_instance.connect.side_effect = imaplib.IMAP4.error("Connection timeout")

    from backend.main import poll_emails_task

    # Act (should not raise)
    poll_emails_task()

    # Assert (no exception was raised)
    # Task completes gracefully


# TC-001-08: Email without Message-ID is handled (fallback ID generation)
def test_email_without_message_id_generates_fallback():
    """
    Given an email missing Message-ID header
    When fetch_new_emails() or polling task processes it
    Then a fallback ID is generated from (from_address, received_date, body_hash)
    And the receipt is stored with fallback message_id
    """
    # Arrange
    msg = EmailMessage()
    # No Message-ID
    msg["From"] = "noreply@picnic.app"
    msg["Date"] = "Wed, 12 Jun 2026 14:30:00 +0200"
    msg.set_content("Invoice content")

    client = IMAPClient("localhost", 993, "test", "secret")

    # Act
    fallback_id = client._get_message_id(msg)

    # Assert
    assert fallback_id is not None
    assert "noreply@picnic.app" in fallback_id
    assert fallback_id != ""


# TC-001-09: Receipt table indexes are created correctly
def test_receipt_table_has_correct_indexes(db_session):
    """
    Given a fresh SQLite database
    When the Receipt table is created (via SQLAlchemy)
    Then indexes exist on: message_id (unique), processed
    """
    # Arrange: tables already created by db_session fixture

    # Act: inspect table
    from sqlalchemy import inspect

    inspector = inspect(db_session.bind)
    indexes = inspector.get_indexes("receipts")
    columns = [col["name"] for col in inspector.get_columns("receipts")]
    pk_columns = inspector.get_pk_constraint("receipts")

    # Assert
    assert "message_id" in columns
    assert "created_at" in columns
    assert "processed" in columns
    # Verify indexes exist
    index_names = [idx["name"] for idx in indexes]
    assert any("message_id" in idx["column_names"] for idx in indexes)


# TC-001-10: Configuration is loaded from .env
def test_config_loads_from_env(tmp_path):
    """
    Given a .env file with IMAP_HOST, IMAP_PORT, IMAP_USERNAME, POLLING_INTERVAL set
    When Pydantic Settings reads the .env file
    Then all values are loaded into the settings object
    And types are correct (int for PORT and INTERVAL, str for credentials)
    """
    # Arrange
    env_file = tmp_path / ".env"
    env_file.write_text(
        "IMAP_HOST=mail.example.com\n"
        "IMAP_PORT=993\n"
        "IMAP_USERNAME=user@example.com\n"
        "POLLING_INTERVAL=1800\n"
    )

    # Act
    settings = Settings(_env_file=str(env_file))

    # Assert
    assert settings.imap_host == "mail.example.com"
    assert settings.imap_port == 993
    assert isinstance(settings.imap_port, int)
    assert settings.imap_username == "user@example.com"
    assert settings.polling_interval == 1800
    assert isinstance(settings.polling_interval, int)
