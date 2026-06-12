"""
FastAPI application for Picnic Expense Tracker backend.

Includes:
- FastAPI app initialization
- Database setup
- IMAP polling task (APScheduler)
- CORS configuration
"""

import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from apscheduler.schedulers.background import BackgroundScheduler
from backend.config import settings
from backend.database import init_db, SessionLocal
from backend.models import Receipt
from backend.imap.client import IMAPClient
from datetime import datetime

# Configure logging
logging.basicConfig(
    level=settings.log_level,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global scheduler instance
scheduler: BackgroundScheduler = None


def poll_emails_task():
    """
    Background task to poll Picnic emails from IMAP and store raw data.

    Called by APScheduler every POLLING_INTERVAL seconds.
    """
    logger.info("Starting email polling task")

    try:
        # Connect to IMAP
        imap_client = IMAPClient(
            host=settings.imap_host,
            port=settings.imap_port,
            username=settings.imap_username,
            password=settings.imap_password,
            use_ssl=settings.imap_use_ssl,
        )

        imap_client.connect()

        # Fetch new emails
        messages = imap_client.fetch_new_emails(settings.imap_mailbox)

        # Store in database
        db = SessionLocal()
        new_count = 0
        dup_count = 0

        try:
            for msg in messages:
                msg_id = imap_client._get_message_id(msg)

                # Check for duplicate
                existing = db.query(Receipt).filter_by(message_id=msg_id).first()
                if existing:
                    logger.warning(f"Skipped duplicate email: {msg_id}")
                    dup_count += 1
                    continue

                # Extract email headers
                from_addr = msg.get("From", "unknown")
                received_date_str = msg.get("Date", str(datetime.utcnow()))

                # Parse received date (simple: use raw string if parse fails)
                try:
                    from email.utils import parsedate_to_datetime
                    received_date = parsedate_to_datetime(received_date_str)
                except Exception:
                    received_date = datetime.utcnow()

                # Store raw email
                receipt = Receipt(
                    message_id=msg_id,
                    received_date=received_date,
                    from_address=from_addr,
                    raw_email_text=msg.as_string(),
                    created_at=datetime.utcnow(),
                    processed=False,
                )

                db.add(receipt)
                new_count += 1

            db.commit()
            logger.info(f"Polling complete: {new_count} new, {dup_count} duplicates")

        except Exception as e:
            logger.error(f"Database error during polling: {e}")
            db.rollback()

        finally:
            db.close()
            imap_client.disconnect()

    except Exception as e:
        logger.error(f"Polling task failed: {e}")
        # Don't raise — let the scheduler retry next cycle


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI lifespan context manager.

    Startup: Initialize database, start APScheduler
    Shutdown: Stop APScheduler
    """
    # Startup
    logger.info("Starting Picnic Expense Tracker backend")

    init_db()

    # Initialize and start scheduler
    global scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        poll_emails_task,
        "interval",
        seconds=settings.polling_interval,
        id="poll_emails",
        name="Poll Picnic emails",
    )
    scheduler.start()
    logger.info(f"Email polling scheduled every {settings.polling_interval} seconds")

    yield

    # Shutdown
    logger.info("Shutting down backend")
    if scheduler and scheduler.running:
        scheduler.shutdown()
    logger.info("Backend shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Picnic Expense Tracker API",
    description="API for tracking Picnic grocery expenses",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with API info."""
    return {
        "title": "Picnic Expense Tracker API",
        "version": "0.1.0",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level=settings.log_level.lower(),
    )
