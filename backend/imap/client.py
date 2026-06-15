"""
IMAP client for polling Picnic emails from Uberspace mailbox.

Provides IMAPClient wrapper around imaplib.IMAP4_SSL for reliable email fetching.
"""

import imaplib
import logging
import hashlib
from email import message_from_bytes
from email.message import Message
from datetime import datetime
from typing import Optional, List

logger = logging.getLogger(__name__)


class IMAPClient:
    """Wrapper around imaplib.IMAP4_SSL for fetching emails."""

    def __init__(self, host: str, port: int, username: str, password: str, use_ssl: bool = True):
        """
        Initialize IMAP client with credentials.

        Args:
            host: IMAP server hostname
            port: IMAP server port (usually 993 for SSL)
            username: IMAP username/email
            password: IMAP password
            use_ssl: Use SSL/TLS (default True)
        """
        self.host = host
        self.port = port
        self.username = username
        self.password = password
        self.use_ssl = use_ssl
        self.connection: Optional[imaplib.IMAP4_SSL] = None

    def connect(self) -> bool:
        """
        Establish connection to IMAP server and authenticate.

        Returns:
            True if successful, False otherwise

        Raises:
            imaplib.IMAP4.error: If connection or authentication fails
        """
        try:
            if self.use_ssl:
                self.connection = imaplib.IMAP4_SSL(self.host, self.port)
            else:
                self.connection = imaplib.IMAP4(self.host, self.port)

            self.connection.login(self.username, self.password)
            logger.info(f"IMAP connection established: {self.username}@{self.host}")
            return True

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP authentication failed: {e}")
            raise

    def disconnect(self):
        """Close IMAP connection."""
        if self.connection:
            try:
                self.connection.close()
                logger.info("IMAP connection closed")
            except Exception as e:
                logger.warning(f"Error closing IMAP connection: {e}")
            finally:
                self.connection = None

    def fetch_new_emails(
        self, mailbox: str = "INBOX", subject_filter: str | None = None
    ) -> List[Message]:
        """
        Fetch emails from mailbox, optionally restricted to a subject filter.

        Args:
            mailbox: Mailbox folder name (default INBOX)
            subject_filter: If given, only emails whose subject contains this
                string (case-insensitive substring match, per IMAP SEARCH
                SUBJECT semantics) are fetched. If None, all emails are
                fetched.

        Returns:
            List of email.Message objects

        Raises:
            imaplib.IMAP4.error: If IMAP operation fails
        """
        if not self.connection:
            raise RuntimeError("IMAP connection not established. Call connect() first.")

        emails = []

        try:
            # Select mailbox
            status, message_count = self.connection.select(mailbox)
            if status != "OK":
                logger.warning(f"Failed to select mailbox {mailbox}")
                return emails

            # Search for matching emails
            if subject_filter:
                status, message_ids = self.connection.search(None, "SUBJECT", f'"{subject_filter}"')
            else:
                status, message_ids = self.connection.search(None, "ALL")
            if status != "OK":
                logger.warning("Failed to search emails")
                return emails

            # Fetch each email
            message_list = message_ids[0].split()
            for msg_id in message_list:
                try:
                    status, msg_data = self.connection.fetch(msg_id, "(RFC822)")
                    if status != "OK":
                        logger.warning(f"Failed to fetch message {msg_id}")
                        continue

                    # Parse email
                    msg = message_from_bytes(msg_data[0][1])
                    emails.append(msg)

                except Exception as e:
                    logger.warning(f"Error parsing email {msg_id}: {e}")
                    continue

            logger.info(f"Fetched {len(emails)} emails from {mailbox}")
            return emails

        except imaplib.IMAP4.error as e:
            logger.error(f"IMAP fetch failed: {e}")
            raise

    def _get_message_id(self, msg: Message) -> str:
        """
        Extract Message-ID from email, or generate fallback ID if missing.

        Args:
            msg: email.Message object

        Returns:
            Message-ID string (unique identifier for the email)
        """
        message_id = msg.get("Message-ID")

        if message_id:
            return message_id.strip()

        # Fallback: generate ID from From, Date, and body hash
        from_addr = msg.get("From", "unknown")
        received_date = msg.get("Date", str(datetime.utcnow()))
        payload = msg.get_payload(decode=True)
        body = payload if isinstance(payload, bytes) else str(msg.get_payload())

        if isinstance(body, bytes):
            body_hash = hashlib.sha256(body).hexdigest()[:16]
        else:
            body_hash = hashlib.sha256(body.encode()).hexdigest()[:16]

        fallback_id = f"{from_addr}_{received_date}_{body_hash}"
        logger.warning(f"Email missing Message-ID, generated fallback: {fallback_id}")

        return fallback_id
