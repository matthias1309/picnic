# TEST-001 — IMAP Email Polling and Receipt Storage Tests

**Status:** approved  
**Created:** 2026-06-12  
**Traces:** ARCH-001  
**Verifies:** REQ-001 (AC-001-01, AC-001-02, AC-001-03, AC-001-04)

---

## Test Cases

### TC-001-01 — IMAP connection with valid credentials succeeds

**Maps to:** AC-001-01  
**Type:** unit (mocked IMAP server)  
**File:** `backend/tests/test_imap.py`

```gherkin
Given the FastAPI backend is running
When the user provides valid IMAP credentials (host, port, username, password)
Then the IMAP connection is established and tested
And credentials are stored securely in .env (not committed to git)
```

**Notes:**
- Mock `imaplib.IMAP4_SSL` to return successful connection
- Verify `IMAPClient.connect()` returns True
- Verify no exception is raised
- Test setup: fake credentials from pytest fixture

---

### TC-001-02 — IMAP connection with invalid credentials fails gracefully

**Maps to:** AC-001-01  
**Type:** unit  
**File:** `backend/tests/test_imap.py`

```gherkin
Given invalid IMAP credentials (wrong password)
When IMAPClient attempts to connect
Then IMAPAuthenticationError is raised
And the error is caught by polling task (does not crash)
```

**Notes:**
- Mock `imaplib.IMAP4_SSL.login()` to raise `IMAP4.error` (auth failure)
- Verify exception is caught and logged
- Verify polling task does not raise exception (returns gracefully)

---

### TC-001-03 — fetch_new_emails() retrieves emails from INBOX

**Maps to:** AC-001-02  
**Type:** unit  
**File:** `backend/tests/test_imap.py`

```gherkin
Given IMAP credentials are configured
When fetch_new_emails() is called
Then a list of email.Message objects is returned
And each message has Message-ID, From, Date headers
```

**Notes:**
- Mock IMAP server responses (SEARCH, FETCH commands)
- Generate 3 test email messages with all required headers
- Verify return type is `List[email.Message]`
- Verify headers are accessible

---

### TC-001-04 — New email is stored in SQLite with correct fields

**Maps to:** AC-001-02  
**Type:** integration (real SQLite, mocked IMAP)  
**File:** `backend/tests/test_imap.py`

```gherkin
Given a new email from Picnic (message_id=test123@picnic.app)
When the polling task stores it
Then a Receipt row is created in SQLite
And fields are populated: message_id, received_date, from_address, raw_email_text
```

**Notes:**
- Use in-memory SQLite (`:memory:`) for fast tests
- Mock IMAP to return 1 test email
- Verify DB row exists: `db.query(Receipt).filter_by(message_id='test123@picnic.app').first()`
- Verify all fields are not null

---

### TC-001-05 — Duplicate email is skipped (Message-ID deduplication)

**Maps to:** AC-001-03  
**Type:** integration  
**File:** `backend/tests/test_imap.py`

```gherkin
Given an email with Message-ID "abc123@picnic.app" is already in the database
When the same email arrives again
Then it is skipped and not re-processed
And a log entry records the duplicate detection
```

**Notes:**
- Insert 1 receipt with message_id='abc123@picnic.app'
- Mock IMAP to return same email again
- Run polling task
- Verify receipt count is still 1 (no duplicate insert)
- Verify log contains "Skipped duplicate"

---

### TC-001-06 — Polling task runs on schedule and completes

**Maps to:** AC-001-02  
**Type:** integration  
**File:** `backend/tests/test_imap.py`

```gherkin
Given APScheduler is configured with 30-minute interval
When the polling task runs
Then it completes without exception
And logs "Polling complete: X new, Y duplicates"
```

**Notes:**
- Mock IMAP to return 2 new + 1 duplicate email
- Run polling task synchronously (don't wait 30 min)
- Verify no exception is raised
- Verify log message contains correct counts

---

### TC-001-07 — Polling error (IMAP timeout) is logged and task continues

**Maps to:** AC-001-04  
**Type:** unit  
**File:** `backend/tests/test_imap.py`

```gherkin
Given IMAP connection times out during fetch
When the polling task encounters the error
Then the error is logged with timestamp and context
And the task continues (does not crash the background daemon)
And a retry happens in the next polling cycle
```

**Notes:**
- Mock IMAP to raise `socket.timeout` or `imaplib.IMAP4.abort`
- Verify exception is caught in polling task
- Verify log level is ERROR
- Verify task does not re-raise exception

---

### TC-001-08 — Email without Message-ID is handled (fallback ID generation)

**Maps to:** AC-001-02  
**Type:** unit  
**File:** `backend/tests/test_imap.py`

```gherkin
Given an email missing Message-ID header
When fetch_new_emails() or polling task processes it
Then a fallback ID is generated from (from_address, received_date, body_hash)
And the receipt is stored with fallback message_id
And a warning is logged
```

**Notes:**
- Create test email without Message-ID header
- Verify fallback ID generation logic
- Verify receipt stores fallback ID and can be queried
- Verify log contains "No Message-ID"

---

### TC-001-09 — Receipt table indexes are created correctly

**Maps to:** AC-001-02  
**Type:** unit  
**File:** `backend/tests/test_database.py`

```gherkin
Given a fresh SQLite database
When the Receipt table is created (via Alembic or __init__)
Then indexes exist on: message_id (unique), created_at (DESC), processed
```

**Notes:**
- Inspect SQLite schema: `PRAGMA index_list(receipts);`
- Verify `message_id` is unique and indexed
- Verify `created_at` and `processed` are indexed
- Verify index uniqueness constraint

---

### TC-001-10 — Configuration is loaded from .env

**Maps to:** AC-001-01  
**Type:** unit  
**File:** `backend/tests/test_config.py`

```gherkin
Given a .env file with IMAP_HOST, IMAP_PORT, IMAP_USERNAME, POLLING_INTERVAL set
When Pydantic Settings reads the .env file
Then all values are loaded into the settings object
And types are correct (int for PORT and INTERVAL, str for credentials)
```

**Notes:**
- Create temp .env with test values
- Load settings from it
- Verify `settings.IMAP_HOST == 'localhost'`
- Verify `settings.IMAP_PORT == 993` (int, not str)
- Verify `settings.POLLING_INTERVAL == 1800` (int)

---

## Test Fixtures & Mocks

**Fixtures needed (in `conftest.py`):**
- `test_env`: Temp .env file for config tests
- `db_session`: In-memory SQLite session
- `mock_imap`: Mock imaplib.IMAP4_SSL with test emails
- `test_email_message`: Construct email.Message with headers

**Mocking strategy:**
- Mock `imaplib.IMAP4_SSL` at module level: `@patch('imaplib.IMAP4_SSL')`
- Don't mock SQLAlchemy; use real in-memory DB for integration tests
- Use `unittest.mock.MagicMock` for IMAP responses

---

## Notes on Coverage

These test cases aim for **80%+ coverage** on:
- `backend/imap/client.py` (connect, fetch_new_emails, error handling)
- `backend/models.py` (Receipt model, indexes)
- `backend/config.py` (settings loading from .env)
- `backend/main.py` (polling task scheduling, error logging)

**Out of scope:**
- Email parsing logic (content extraction) → TEST-002, REQ-002
- REST API endpoints → TEST-003
- Frontend tests → TEST-004
