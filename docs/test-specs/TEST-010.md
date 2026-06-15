# TEST-010 — Filter Ingested Emails by Subject Tests

**Status:** draft
**Created:** 2026-06-15
**Traces:** ARCH-010
**Verifies:** REQ-010 (AC-010-01, AC-010-02, AC-010-03, AC-010-04)

---

## Test Cases

### TC-010-01 — `fetch_new_emails` searches by subject when a filter is given

**Maps to:** AC-010-01, AC-010-02, AC-010-03
**Type:** unit (mocked IMAP server)
**File:** `backend/tests/test_imap.py`

```gherkin
Given an IMAPClient is connected
When fetch_new_emails(mailbox, subject_filter="Dein Bon") is called
Then connection.search is called with SUBJECT "Dein Bon"
And connection.search is not called with "ALL"
```

**Notes:**
- Mock `connection.search` to return `("OK", [b""])` (no matches needed).
- Assert `mock_instance.search.assert_called_once_with(None, "SUBJECT", '"Dein Bon"')`.

---

### TC-010-02 — `fetch_new_emails` falls back to `SEARCH ALL` without a filter

**Maps to:** AC-010-04 (default/backward-compatible behavior)
**Type:** unit (mocked IMAP server)
**File:** `backend/tests/test_imap.py`

```gherkin
Given an IMAPClient is connected
When fetch_new_emails(mailbox) is called without a subject_filter
Then connection.search is called with "ALL"
```

**Notes:**
- Existing TC-001-03 test continues to pass unchanged (no `subject_filter`
  argument), demonstrating backward compatibility.

---

### TC-010-03 — Only matching emails are returned and stored

**Maps to:** AC-010-01, AC-010-03
**Type:** unit (mocked IMAP server)
**File:** `backend/tests/test_imap.py`

```gherkin
Given the IMAP server's SEARCH SUBJECT "Dein Bon" returns only message IDs
  for emails with "Dein Bon" in the subject
When fetch_new_emails(mailbox, subject_filter="Dein Bon") is called
Then only those messages are fetched and returned
And no FETCH is issued for non-matching message IDs
```

**Notes:**
- Mock `search` to return a subset of message IDs (simulating the IMAP
  server having already excluded non-matching emails).
- Assert `connection.fetch` is called only for the returned IDs and the
  result list has the expected length.

---

### TC-010-04 — `poll_emails_task` passes the configured subject filter

**Maps to:** AC-010-04
**Type:** unit (mocked IMAPClient)
**File:** `backend/tests/test_imap.py`

```gherkin
Given settings.imap_subject_filter is "Dein Bon" (default)
When poll_emails_task() runs
Then imap_client.fetch_new_emails is called with subject_filter="Dein Bon"
```

**Notes:**
- Mock `IMAPClient` as in TC-001-06; assert on
  `mock_instance.fetch_new_emails.call_args`.

---

### TC-010-05 — `imap_subject_filter` setting defaults to "Dein Bon" and is configurable

**Maps to:** AC-010-04
**Type:** unit
**File:** `backend/tests/test_imap.py`

```gherkin
Given no IMAP_SUBJECT_FILTER is set in .env
When Settings are loaded
Then settings.imap_subject_filter == "Dein Bon"
```

```gherkin
Given .env sets IMAP_SUBJECT_FILTER=Custom Subject
When Settings are loaded
Then settings.imap_subject_filter == "Custom Subject"
```

---

## Test Fixtures & Mocks

- Reuses the `@patch("imaplib.IMAP4_SSL")` pattern from TEST-001
  (`test_imap_client_connects_with_valid_credentials`,
  `test_fetch_new_emails_returns_email_list`).
- Reuses the `@patch("backend.main.IMAPClient")` /
  `@patch("backend.main.SessionLocal")` pattern from TC-001-06 for TC-010-04.
- TC-010-05 reuses the `tmp_path`-based `.env` fixture pattern from
  TC-001-10/TC-001-11.

---

## Notes on Coverage

These test cases extend coverage on:
- `backend/imap/client.py::fetch_new_emails` (new `subject_filter` parameter)
- `backend/config.py` (new `imap_subject_filter` setting)
- `backend/main.py::poll_emails_task` (passes the configured filter)

**Out of scope:**
- Email parsing logic — unchanged, see TEST-002.
- Cleanup of previously stored non-matching receipts — out of scope per
  REQ-010.
</content>
