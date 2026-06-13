"""
Business logic for turning raw receipt emails into structured purchase data.

Traces: ARCH-002
"""

import logging
from dataclasses import dataclass

from sqlalchemy.orm import Session

from backend.imap.parser import ParseError, ParsedReceipt, ReceiptParser
from backend.models import PriceHistory, Product, Receipt, ReceiptItem

logger = logging.getLogger(__name__)


@dataclass
class ParseSummary:
    """Outcome of a parse run, used for logging."""

    parsed: int
    failed: int
    items: int


def parse_pending_receipts(db: Session, parser: ReceiptParser | None = None) -> ParseSummary:
    """Parse all receipts with processed == False.

    Each receipt is parsed and committed in its own transaction, so a single
    malformed email does not affect the others (AC-002-05).
    """
    parser = parser or ReceiptParser()
    pending = db.query(Receipt).filter(Receipt.processed.is_(False)).all()

    parsed_count = 0
    failed_count = 0
    item_count = 0

    for receipt in pending:
        try:
            html = parser.extract_html(receipt.raw_email_text)
            parsed_receipt = parser.parse(html)
        except ParseError as error:
            logger.error(f"Failed to parse receipt {receipt.id}: {error}")
            failed_count += 1
            continue

        _store_parsed_receipt(db, receipt, parsed_receipt)
        _reconcile_total(receipt, parsed_receipt)

        receipt.processed = True
        db.commit()

        parsed_count += 1
        item_count += len(parsed_receipt.items)

    logger.info(
        f"Parsing complete: {parsed_count} parsed, {failed_count} failed, "
        f"{item_count} items stored"
    )
    return ParseSummary(parsed=parsed_count, failed=failed_count, items=item_count)


def _store_parsed_receipt(db: Session, receipt: Receipt, parsed_receipt: ParsedReceipt) -> None:
    for item in parsed_receipt.items:
        product = _get_or_create_product(db, item.name)

        db.add(
            ReceiptItem(
                receipt=receipt,
                product=product,
                quantity=item.quantity,
                unit_price_cents=item.unit_price_cents,
                line_total_cents=item.line_total_cents,
            )
        )
        db.add(
            PriceHistory(
                product=product,
                receipt_id=receipt.id,
                unit_price_cents=item.unit_price_cents,
                quantity=item.quantity,
                recorded_date=receipt.received_date,
            )
        )


def _get_or_create_product(db: Session, name: str) -> Product:
    """Look up a product by its exact name, creating it if it does not exist."""
    product = db.query(Product).filter(Product.name == name).first()
    if product is None:
        product = Product(name=name)
        db.add(product)
        db.flush()
    return product


def _reconcile_total(receipt: Receipt, parsed_receipt: ParsedReceipt) -> None:
    """Log a warning if the summed line totals do not match the stated total."""
    if parsed_receipt.stated_total_cents is None:
        return

    computed_total_cents = sum(item.line_total_cents for item in parsed_receipt.items)
    if computed_total_cents != parsed_receipt.stated_total_cents:
        logger.warning(
            f"Receipt {receipt.id}: computed total {computed_total_cents} cents does not "
            f"match stated total {parsed_receipt.stated_total_cents} cents"
        )
