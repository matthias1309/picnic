"""
Business logic for turning raw receipt emails into structured purchase data.

Traces: ARCH-002
"""

import logging
from dataclasses import dataclass
from datetime import date

from sqlalchemy import func, update
from sqlalchemy.orm import Session, selectinload

from backend.imap.parser import ParseError, ParsedReceipt, ReceiptParser
from backend.models import PriceHistory, Product, Receipt, ReceiptItem
from backend.services import category_service

logger = logging.getLogger(__name__)


@dataclass
class ParseSummary:
    """Outcome of a parse run, used for logging."""

    parsed: int
    failed: int
    items: int


def _claim_receipt_for_processing(db: Session, receipt_id: int) -> bool:
    """Atomically flip one receipt from pending to claimed.

    Returns False if the receipt was no longer processed == False by the time
    this statement ran — i.e. another session (a different Gunicorn worker's
    scheduler tick, or a concurrent manual re-parse) already claimed it. The
    caller must not store items in that case (REQ-016).

    A plain read-then-write (SELECT processed, then UPDATE) would let two
    sessions both observe processed == False before either commits. This is
    a single UPDATE ... WHERE statement instead: SQLite serializes writers at
    the file level, so only one of two concurrent claims on the same row can
    ever see rowcount == 1.
    """
    result = db.execute(
        update(Receipt)
        .where(Receipt.id == receipt_id, Receipt.processed.is_(False))
        .values(processed=True)
    )
    db.commit()
    return result.rowcount == 1


def parse_pending_receipts(db: Session, parser: ReceiptParser | None = None) -> ParseSummary:
    """Parse all receipts with processed == False.

    Each receipt is claimed, parsed, and committed in its own transaction, so
    a single malformed email does not affect the others (AC-002-05), and a
    receipt already claimed by a concurrent caller is skipped rather than
    parsed twice (AC-016-01).
    """
    parser = parser or ReceiptParser()
    pending_ids = [
        receipt_id
        for (receipt_id,) in db.query(Receipt.id).filter(Receipt.processed.is_(False)).all()
    ]

    parsed_count = 0
    failed_count = 0
    item_count = 0

    for receipt_id in pending_ids:
        if not _claim_receipt_for_processing(db, receipt_id):
            continue

        receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()

        try:
            html = parser.extract_html(receipt.raw_email_text)
            parsed_receipt = parser.parse(html)
        except ParseError as error:
            logger.error(f"Failed to parse receipt {receipt.id}: {error}")
            receipt.processed = False  # release the claim so a later run retries it
            db.commit()
            failed_count += 1
            continue

        receipt.delivery_date = parsed_receipt.delivery_date
        _store_parsed_receipt(db, receipt, parsed_receipt)
        _reconcile_total(receipt, parsed_receipt)
        db.commit()

        parsed_count += 1
        item_count += len(parsed_receipt.items)

    logger.info(
        f"Parsing complete: {parsed_count} parsed, {failed_count} failed, {item_count} items stored"
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
                order_number=item.order_number,
            )
        )
        db.add(
            PriceHistory(
                product=product,
                receipt_id=receipt.id,
                unit_price_cents=item.unit_price_cents,
                quantity=item.quantity,
                recorded_date=receipt.effective_date,
            )
        )


def _get_or_create_product(db: Session, name: str) -> Product:
    """Look up a product by its exact name, creating it if it does not exist."""
    product = db.query(Product).filter(Product.name == name).first()
    if product is None:
        product = Product(name=name, category_key=category_service.categorize(name))
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


def list_receipts(
    db: Session,
    limit: int,
    offset: int,
    from_date: date | None = None,
    to_date: date | None = None,
) -> tuple[list[Receipt], int]:
    """Return a page of receipts (newest first) and the total matching count."""
    query = db.query(Receipt)
    if from_date is not None:
        query = query.filter(func.date(Receipt.effective_date) >= from_date)
    if to_date is not None:
        query = query.filter(func.date(Receipt.effective_date) <= to_date)

    total = query.count()
    receipts = (
        query.options(selectinload(Receipt.items))
        .order_by(Receipt.effective_date.desc())
        .limit(limit)
        .offset(offset)
        .all()
    )
    return receipts, total


def get_receipt_with_items(db: Session, receipt_id: int) -> Receipt | None:
    """Return a receipt with its items and their products eagerly loaded."""
    return (
        db.query(Receipt)
        .options(selectinload(Receipt.items).selectinload(ReceiptItem.product))
        .filter(Receipt.id == receipt_id)
        .first()
    )


def list_products(db: Session) -> list[tuple[Product, int]]:
    """Return all products with their purchase counts, ordered by name (AC-003-03)."""
    return (
        db.query(Product, func.count(ReceiptItem.id))
        .outerjoin(ReceiptItem, ReceiptItem.product_id == Product.id)
        .group_by(Product.id)
        .order_by(Product.name)
        .all()
    )


def count_product_purchases(db: Session, product_id: int) -> int:
    """Return how many receipt items reference a product.

    A COUNT query rather than len(product.receipt_items): the relationship
    would load every line item just to size the list.
    """
    return (
        db.query(func.count(ReceiptItem.id)).filter(ReceiptItem.product_id == product_id).scalar()
    )


def delete_receipt(db: Session, receipt_id: int) -> bool:
    """Delete a receipt, its items, and its price history (AC-009-04).

    Returns False without making changes if no receipt with the given id
    exists (AC-009-05).
    """
    receipt = db.query(Receipt).filter(Receipt.id == receipt_id).first()
    if receipt is None:
        return False

    db.query(PriceHistory).filter(PriceHistory.receipt_id == receipt_id).delete()
    db.delete(receipt)
    db.commit()
    return True


def get_product_with_price_history(
    db: Session, product_id: int
) -> tuple[Product, list[PriceHistory]] | None:
    """Return a product and its price history, ordered oldest-first (AC-003-04)."""
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        return None

    history = (
        db.query(PriceHistory)
        .filter(PriceHistory.product_id == product_id)
        .order_by(PriceHistory.recorded_date.asc())
        .all()
    )
    return product, history
