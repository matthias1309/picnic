# ARCH-010 — Filter Ingested Emails by Subject

**Status:** approved
**Created:** 2026-06-15
**Traces:** REQ-010
**Verified by:** TEST-010

## Summary

ARCH-010 restricts `IMAPClient.fetch_new_emails` to emails whose subject
matches a configurable filter (default `"Dein Bon"`), using the IMAP
`SEARCH SUBJECT` criterion instead of `SEARCH ALL`. The filter value is read
from a new setting and passed through from `poll_emails_task`.

---

## Design

### Data Flow

```
backend/config.py
  Settings.imap_subject_filter: str = "Dein Bon"
        ↓
backend/main.py:poll_emails_task()
  imap_client.fetch_new_emails(
      settings.imap_mailbox,
      subject_filter=settings.imap_subject_filter,
  )
        ↓
backend/imap/client.py:IMAPClient.fetch_new_emails(mailbox, subject_filter)
  if subject_filter:
      search(None, "SUBJECT", '"<subject_filter>"')
  else:
      search(None, "ALL")
```

### `fetch_new_emails` signature change

```python
def fetch_new_emails(
    self, mailbox: str = "INBOX", subject_filter: str | None = None
) -> List[Message]:
    ...
    if subject_filter:
        status, message_ids = self.connection.search(
            None, "SUBJECT", f'"{subject_filter}"'
        )
    else:
        status, message_ids = self.connection.search(None, "ALL")
```

`subject_filter` defaults to `None` (→ `SEARCH ALL`), preserving existing
behavior for any caller that does not pass it. `poll_emails_task` always
passes `settings.imap_subject_filter`, whose default is `"Dein Bon"`
(AC-010-04).

### Configuration

```python
# backend/config.py
class Settings(BaseSettings):
    ...
    imap_subject_filter: str = "Dein Bon"
```

```bash
# .env.example
IMAP_SUBJECT_FILTER=Dein Bon
```

### IMAP `SUBJECT` Search Semantics

The IMAP `SEARCH SUBJECT "<string>"` criterion (RFC 3501 §6.4.4) matches
messages whose decoded subject contains `<string>` as a substring,
case-insensitively. This satisfies AC-010-01/02/03 without any additional
client-side filtering — non-matching messages are never returned by
`search()`, so they are never fetched, never stored, and remain untouched in
the mailbox.

---

## Key Decisions

### 1. Filter at the IMAP `SEARCH` level, not client-side

**Decision:** Pass `SUBJECT "<filter>"` to `connection.search()` rather than
fetching all messages and discarding non-matching ones in Python.

**Rationale:**
- Non-matching emails are never downloaded (bandwidth, AC-010-03).
- No new `Receipt` rows are ever created for non-matching emails — nothing
  to filter or clean up downstream.
- IMAP `SUBJECT` search is case-insensitive substring matching by spec, so
  AC-010-02 requires no extra code.

### 2. Configurable via `.env`, default `"Dein Bon"`

**Decision:** Add `imap_subject_filter` to `Settings` with default
`"Dein Bon"`, consistent with how other IMAP settings (REQ-001) are
configured.

**Rationale:** Keeps the filter adjustable without a code change (e.g. if
Picnic changes the subject wording or a different locale is used), while
requiring zero configuration for the documented default.

### 3. `subject_filter` is an optional parameter, default `None`

**Decision:** `fetch_new_emails(mailbox, subject_filter=None)` falls back to
`SEARCH ALL` when `subject_filter` is falsy.

**Rationale:** Keeps `IMAPClient` a generic, reusable wrapper (it doesn't
hardcode Picnic-specific filtering), and avoids changing the meaning of
existing direct calls/tests that don't pass a filter.

---

## Module Layout

```
backend/
  config.py          # extended: imap_subject_filter setting
  imap/
    client.py         # extended: fetch_new_emails(mailbox, subject_filter=None)
  main.py             # extended: poll_emails_task passes settings.imap_subject_filter
.env.example          # extended: IMAP_SUBJECT_FILTER
```

---

## Out of Scope

- Cleaning up previously stored non-matching `Receipt` rows (REQ-010 Notes).
- Sender-address filtering.
- UI for configuring the filter.
</content>
