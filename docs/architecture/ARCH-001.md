# ARCH-001 — IMAP Email Polling and Receipt Storage Architecture

**Status:** draft  
**Created:** 2026-06-12  
**Traces:** REQ-001  
**Verified by:** TEST-001

## Summary

ARCH-001 defines the backend architecture for automatically polling Picnic emails from a Uberspace IMAP mailbox, validating them, and storing raw email data for later processing. The design focuses on reliability (error handling, duplicate prevention) and simplicity (no external services, SQLite storage).

---

## Design

### System Architecture Diagram

```
┌─────────────────────────────────────────────────────┐
│  FastAPI Application (backend/main.py)              │
│  ┌───────────────────────────────────────────────┐  │
│  │ Lifespan Manager (startup / shutdown)         │  │
│  │  - Initialize APScheduler                     │  │
│  │  - Schedule polling task every 30 min         │  │
│  └───────────────────────────────────────────────┘  │
│                        ↓                            │
│  ┌───────────────────────────────────────────────┐  │
│  │ APScheduler (background task runner)          │  │
│  │  - Interval: 30 minutes (POLLING_INTERVAL)    │  │
│  │  - Calls: poll_emails_task()                  │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                        ↓
┌─────────────────────────────────────────────────────┐
│  backend/imap/client.py — IMAPClient               │
│  ┌───────────────────────────────────────────────┐  │
│  │ IMAPClient (wrapper around imaplib.IMAP4_SSL) │  │
│  │                                               │  │
│  │ Methods:                                      │  │
│  │  - __init__(host, port, user, pwd, use_ssl)  │  │
│  │  - connect() → IMAP4_SSL instance            │  │
│  │  - fetch_new_emails() → List[email.Message] │  │
│  │  - disconnect()                               │  │
│  │  - _get_message_id(msg) → str                │  │
│  └───────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────┘
                        ↓
        ┌───────────────────────────┬──────────┐
        ↓                           ↓          ↓
┌──────────────────┐    ┌─────────────────┐  Check DB
│ Get Message-ID   │    │ Fetch Raw Email │  (message_id)
│ from IMAP        │    │ Full MIME text  │
└──────────────────┘    └─────────────────┘
        ↓                      ↓
        └──────────────────────┴────────────────┐
                               ↓                │
                     ┌─────────────────────┐    │
                     │ Duplicate Check     │    │
                     │ (query DB by msg_id)│    │
                     └─────────────────────┘    │
                        ↓         ↓             │
                   [Found]  [Not Found]         │
                        ↓         ↓             │
                      Log    ┌─────────────────┤
                      Skip   │ Insert Receipt  │
                             │ into SQLite     │
                             └─────────────────┘
                                    ↓
                      backend/models.py:
                      class Receipt(Base)
```

### Database Schema

**Table: `receipts`**

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| `id` | Integer | PRIMARY KEY, auto-increment | Unique receipt ID |
| `message_id` | String(255) | UNIQUE, NOT NULL, indexed | IMAP Message-ID header (dedup key) |
| `received_date` | DateTime | NOT NULL | Date header from email (when Picnic sent) |
| `from_address` | String(255) | NOT NULL | Sender email (e.g. noreply@picnic.app) |
| `raw_email_text` | Text | NOT NULL | Full MIME message (headers + body) |
| `created_at` | DateTime | NOT NULL, server_default=now() | When we stored it in DB |
| `processed` | Boolean | default=False | Flag for phase 2 (parsing) |

**Indexes:**
- `idx_message_id`: `(message_id)` — fast dedup lookup
- `idx_created_at`: `(created_at DESC)` — fast sorting by date
- `idx_processed`: `(processed)` — fast filtering for pending parse tasks

### IMAP Polling Logic

```python
# Pseudo-code (details in TEST-001)

def poll_emails_task():
    """Called by APScheduler every 30 minutes."""
    try:
        imap_client = IMAPClient(
            host=settings.IMAP_HOST,
            port=settings.IMAP_PORT,
            user=settings.IMAP_USERNAME,
            pwd=settings.IMAP_PASSWORD,
            use_ssl=settings.IMAP_USE_SSL
        )
        
        messages = imap_client.fetch_new_emails()
        
        new_count = 0
        dup_count = 0
        
        for msg in messages:
            msg_id = imap_client._get_message_id(msg)
            
            if db.query(Receipt).filter(Receipt.message_id == msg_id).first():
                # Duplicate
                logger.warning(f"Skipped duplicate email: {msg_id}")
                dup_count += 1
                continue
            
            # New email — store it
            receipt = Receipt(
                message_id=msg_id,
                received_date=parse_date_header(msg),
                from_address=msg["From"],
                raw_email_text=msg.as_string(),
                created_at=datetime.utcnow()
            )
            db.add(receipt)
            new_count += 1
        
        db.commit()
        logger.info(f"Polling complete: {new_count} new, {dup_count} duplicates")
        
    except IMAPError as e:
        logger.error(f"IMAP connection failed: {e}")
        # Do NOT raise — let task finish, retry next cycle
    except Exception as e:
        logger.error(f"Unexpected error in polling task: {e}")
        # Do NOT raise
```

### Configuration (from `.env`)

```bash
IMAP_HOST=localhost              # Uberspace mail server
IMAP_PORT=993                    # IMAPS (secure)
IMAP_USERNAME=user@example.com   # Uberspace email account
IMAP_PASSWORD=app_password       # App-specific password (not login pwd)
IMAP_USE_SSL=true                # Use IMAPS protocol
IMAP_MAILBOX=INBOX               # Folder to poll

POLLING_INTERVAL=1800            # Seconds (30 minutes)

DATABASE_URL=sqlite:///./picnic.db  # Local SQLite file
# Or: sqlite:////home/user/data/picnic.db (absolute path on Uberspace)
```

### Error Handling & Resilience

**Scenario: IMAP connection fails**
- Exception is caught in `poll_emails_task()`
- Error is logged with full traceback
- Task does NOT raise exception (allows daemon to continue)
- Next polling cycle (30 min later) retries

**Scenario: Database write fails (e.g. disk full)**
- SQLAlchemy raises exception
- Caught in task, logged
- Partial commits are rolled back
- Next cycle retries from scratch

**Scenario: Email has no Message-ID**
- Fallback to generating ID from (from_address, received_date, hash(body))
- Log warning
- Proceed with insert

---

## Key Decisions

### 1. Why `imaplib` over `IMAPClient` library?

**Decision:** Use Python stdlib `imaplib.IMAP4_SSL` with a thin wrapper.

**Rationale:**
- ✅ No external dependency (vs. `IMAPClient` package)
- ✅ Stable, battle-tested in production
- ✅ Sufficient for MVP (connect, SELECT, SEARCH, FETCH, IDLE)
- ❌ Slightly more verbose API
- ⚠️ If complexity grows (IDLE for push notifications), can switch to IMAPClient in Phase 2

### 2. Why store raw email text, not parsed?

**Decision:** Store full MIME message in `raw_email_text`; parsing is REQ-002 (separate).

**Rationale:**
- ✅ Single responsibility: this feature (polling) is separate from parsing
- ✅ Full email is available for debugging / re-parsing if parser fails
- ✅ Email source-of-truth; parsed data is derived
- ❌ Uses more disk space (but acceptable for ~100 emails/month)

### 3. Why APScheduler for polling, not Celery/RabbitMQ?

**Decision:** APScheduler with FastAPI lifespan (no separate queue).

**Rationale:**
- ✅ Simple, no external services (Celery requires Redis/RabbitMQ)
- ✅ Sufficient for low-frequency polling (every 30 min)
- ✅ Runs in-process with FastAPI app
- ❌ No task persistence (app restart = schedule resets, but next cycle runs soon)
- ⚠️ If we need high-frequency polling + task persistence, upgrade to Celery in Phase 2

### 4. Why no connection pooling?

**Decision:** Create new IMAP connection per polling cycle, then close.

**Rationale:**
- ✅ Simple, no state management
- ✅ IMAP polling is infrequent (30 min intervals)
- ✅ Connection is short-lived (~1 min to fetch emails)
- ❌ Slight overhead (SSL handshake per cycle)
- ⚠️ If polling becomes real-time, add connection pool in Phase 2

### 5. Why Message-ID for deduplication, not content hash?

**Decision:** Use IMAP `Message-ID` header as unique key (required by RFC 5322).

**Rationale:**
- ✅ Guaranteed unique per email
- ✅ Picnic always includes Message-ID
- ✅ No hash collision risk
- ✅ Fast indexed lookup
- ❌ Requires email to have Message-ID (fallback: generate from metadata)

---

## Out of Scope

- **Email parsing** → see REQ-002, ARCH-002
- **OAuth2 authentication** → Phase 2+ (username/password for MVP)
- **IMAP IDLE** (push notifications) → polling-only for MVP
- **Connection pooling / reconnection logic** → single connection per cycle
- **Email archiving / deletion** → emails stay in mailbox indefinitely
- **Multiple IMAP accounts** → single account per backend instance
- **Web UI for IMAP credentials** → .env-only for MVP
- **Rate limiting on IMAP server** → assumption: Uberspace allows polling

---

## Open Questions

1. **Should we support IMAP folders other than INBOX?**
   - Currently hardcoded to INBOX
   - Could add IMAP_MAILBOX to .env
   - Decision: INBOX only for MVP, add flexibility in Phase 2

2. **How many emails per Picnic account per month?**
   - Assumption: ~5-10 invoices/month
   - Current design handles 100s per month without issue
   - Future: if >10K/month, add pagination/batching

3. **Should we log to file or only stdout?**
   - MVP: stdout only (Uberspace can capture via supervisor/systemd)
   - Phase 2: add file logging (LOG_FILE env var)

4. **Backup strategy for SQLite file?**
   - Not in scope for MVP (single-user personal app)
   - Recommend: periodic backup via cron to /home/user/backups/
   - Decision: document in deployment guide, not in code

5. **What if IMAP credentials are wrong?**
   - Error logged on first polling cycle
   - User must fix .env and restart app (or wait for next cycle to retry)
   - No graceful recovery in MVP
   - Phase 2: add UI to reconfigure credentials without restart
