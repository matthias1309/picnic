"""
One-off maintenance script: re-parse a single already-processed receipt.

Use this when a receipt was imported with an older parser version that
produced incorrect line items (e.g. zero prices), so it needs to be parsed
again with the current parser without re-fetching it from IMAP.

Usage:
    python -m scripts.reprocess_receipt <receipt_id>
"""

import sys

from backend.database import SessionLocal
from backend.imap.parser import ParseError, ReceiptParser
from backend.models import PriceHistory, Receipt
from backend.services.receipt_service import _reconcile_total, _store_parsed_receipt


def reprocess_receipt(receipt_id: int) -> None:
    db = SessionLocal()
    try:
        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
        if receipt is None:
            raise SystemExit(f"Receipt {receipt_id} not found")

        parser = ReceiptParser()
        html = parser.extract_html(receipt.raw_email_text)
        parsed_receipt = parser.parse(html)

        db.query(PriceHistory).filter(PriceHistory.receipt_id == receipt.id).delete()
        receipt.items.clear()
        db.flush()

        _store_parsed_receipt(db, receipt, parsed_receipt)
        _reconcile_total(receipt, parsed_receipt)
        receipt.processed = True

        db.commit()
        print(f"Reprocessed receipt {receipt_id}: {len(parsed_receipt.items)} items stored")
    except ParseError as error:
        db.rollback()
        raise SystemExit(f"Failed to parse receipt {receipt_id}: {error}")
    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python -m scripts.reprocess_receipt <receipt_id>")

    reprocess_receipt(int(sys.argv[1]))
