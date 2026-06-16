"""
Parser for Picnic "Dein Bon" invoice emails.

Extracts line items (product name, quantity, prices) and the stated order
total from the HTML invoice table embedded in the raw MIME email.
"""

import re
from dataclasses import dataclass
from datetime import date
from email import message_from_string

from bs4 import BeautifulSoup
from bs4.element import Tag


class ParseError(Exception):
    """Raised when an email does not match the expected invoice structure."""


@dataclass(frozen=True)
class ParsedItem:
    """A single line item extracted from a Picnic invoice."""

    name: str
    quantity: int
    unit_price_cents: int
    line_total_cents: int
    order_number: str | None = None


@dataclass(frozen=True)
class ParsedReceipt:
    """The result of parsing a Picnic invoice email."""

    items: list[ParsedItem]
    stated_total_cents: int | None
    delivery_date: date | None = None


# Style fragments used by Picnic's invoice template to mark structural elements.
_ITEM_ROW_STYLE = "border-bottom:1px solid #ebebeb"
_QUANTITY_BADGE_STYLE = "border:1px solid #234314"
_STRUCK_THROUGH_STYLE = "line-through"
_TOTAL_LABEL = "Gesamtbetrag"

# Order section header, e.g. "Bestellnr 209-521-1175".
_ORDER_NUMBER_RE = re.compile(r"Bestellnr\s+(\d{3}-\d{3}-\d{4})")

# German month names as they appear in the invoice body.
_GERMAN_MONTHS = {
    "januar": 1,
    "februar": 2,
    "märz": 3,
    "april": 4,
    "mai": 5,
    "juni": 6,
    "juli": 7,
    "august": 8,
    "september": 9,
    "oktober": 10,
    "november": 11,
    "dezember": 12,
}

# Delivery sentence, e.g. "Lieferung von Montag 15 Juni 2026". The weekday only
# anchors the match and is discarded; the day may carry a trailing period.
_DELIVERY_DATE_RE = re.compile(
    r"Lieferung von\s+\w+\s+(\d{1,2})\.?\s+([A-Za-zÄÖÜäöüß]+)\s+(\d{4})",
    re.IGNORECASE,
)


def _normalize_style(style: str | None) -> str:
    """Lowercase a style attribute and strip spaces for tolerant comparison.

    Picnic's template varies the spelling of declarations across versions
    (e.g. ``border-bottom:1px solid #ebebeb`` vs.
    ``border-bottom: 1px solid #EBEBEB``); normalizing absorbs whitespace and
    case differences so style markers match regardless.
    """
    return (style or "").replace(" ", "").lower()


_ITEM_ROW_STYLE_NORMALIZED = _normalize_style(_ITEM_ROW_STYLE)


class ReceiptParser:
    """Parses Picnic invoice emails into structured data."""

    def extract_html(self, raw_email_text: str) -> str:
        """Return the text/html MIME part of the raw email.

        Raises:
            ParseError: if the email has no text/html part.
        """
        message = message_from_string(raw_email_text)

        if message.get_content_type() == "text/html":
            return self._decode_payload(message)

        for part in message.walk():
            if part.get_content_type() == "text/html":
                return self._decode_payload(part)

        raise ParseError("Email has no text/html part")

    def parse(self, html: str) -> ParsedReceipt:
        """Parse the invoice HTML into structured items and the stated total.

        Raises:
            ParseError: if no item rows can be found in the HTML.
        """
        soup = BeautifulSoup(html, "html.parser")

        rows = [
            cell
            for cell in soup.find_all("td")
            if _ITEM_ROW_STYLE_NORMALIZED in _normalize_style(cell.get("style"))
            and cell.select_one("img[alt]") is not None
        ]
        if not rows:
            raise ParseError("No item rows found in invoice HTML")

        items = [self._parse_item_row(row) for row in rows]
        stated_total_cents = self._extract_stated_total(soup)
        delivery_date = self._extract_delivery_date(soup)

        return ParsedReceipt(
            items=items,
            stated_total_cents=stated_total_cents,
            delivery_date=delivery_date,
        )

    def _extract_delivery_date(self, soup: BeautifulSoup) -> date | None:
        """Best-effort extraction of the delivery date from the invoice body.

        Picnic states the delivery in a sentence such as "… Lieferung von
        Montag 15 Juni 2026". Returns None when the sentence is absent or its
        month name is unknown, so the caller falls back to the email date
        instead of failing the whole parse.
        """
        text = soup.get_text(" ", strip=True)
        match = _DELIVERY_DATE_RE.search(text)
        if match is None:
            return None

        day, month_name, year = match.groups()
        month = _GERMAN_MONTHS.get(month_name.lower())
        if month is None:
            return None

        try:
            return date(int(year), month, int(day))
        except ValueError:
            return None

    def _parse_item_row(self, row: Tag) -> ParsedItem:
        image = row.select_one("img[alt]")
        if image is None:
            raise ParseError("Item row has no product image/name")
        name = image["alt"]

        quantity_cell = row.select_one(f'td[align="left"][style*="{_QUANTITY_BADGE_STYLE}"]')
        if quantity_cell is None:
            raise ParseError(f"Item row for '{name}' has no quantity badge")
        quantity = int(quantity_cell.get_text(strip=True))

        price_table = row.select_one('td[align="right"] > table')
        prices = self._extract_prices(price_table) if price_table else []

        if prices:
            euro, cent, _ = prices[-1]
            line_total_cents = self._to_cents(euro, cent)
        else:
            # Free item (e.g. part of a "2+1 gratis" promotion)
            line_total_cents = 0

        unit_price_cents = round(line_total_cents / quantity) if quantity else 0

        return ParsedItem(
            name=name,
            quantity=quantity,
            unit_price_cents=unit_price_cents,
            line_total_cents=line_total_cents,
            order_number=self._extract_order_number(row),
        )

    def _extract_order_number(self, row: Tag) -> str | None:
        """Return the order number of the section this item row belongs to.

        Picnic groups items under "Bestellnr NNN-NNN-NNNN" headers; an item
        belongs to the nearest such header that precedes it. Items that appear
        before any header (or in emails without order numbers) return None.
        """
        for text in row.find_all_previous(string=_ORDER_NUMBER_RE):
            match = _ORDER_NUMBER_RE.search(text)
            if match:
                return match.group(1)
        return None

    def _extract_prices(self, price_table: Tag) -> list[tuple[str, str, bool]]:
        """Extract (euro, cent, is_struck_through) tuples from a price table.

        Picnic renders each price as two stacked `<td>`s: a large euro part and
        a smaller cent part. A struck-through row shows the pre-discount price.
        """
        prices = []
        for row in self._direct_rows(price_table):
            cells = row.find_all("td", recursive=False)
            if len(cells) != 2:
                continue

            euro_cell, cent_table_cell = cells
            euro = euro_cell.get_text(strip=True)
            if not euro.isdigit():
                continue

            cent_cells = cent_table_cell.select("td")
            cent = cent_cells[0].get_text(strip=True) if cent_cells else "0"
            is_struck = _STRUCK_THROUGH_STYLE in (euro_cell.get("style") or "")

            prices.append((euro, cent, is_struck))

        return prices

    def _extract_stated_total(self, soup: BeautifulSoup) -> int | None:
        """Best-effort extraction of the order total ("Gesamtbetrag").

        Returns None if the total cannot be found, in which case reconciliation
        (AC-002-06) is skipped.
        """
        for cell in soup.find_all("td"):
            if cell.get_text(strip=True) != _TOTAL_LABEL:
                continue

            price_cell = cell.find_next_sibling("td")
            price_table = price_cell.select_one("table") if price_cell else None
            if price_table is None:
                continue

            prices = self._extract_prices(price_table)
            if prices:
                euro, cent, _ = prices[-1]
                return self._to_cents(euro, cent)

        return None

    @staticmethod
    def _direct_rows(table: Tag) -> list[Tag]:
        """Return a table's <tr> children, looking through an optional <tbody>.

        Some email clients (e.g. Gmail, on forward) wrap a table's <tr>
        elements in an implicit <tbody> that Picnic's original HTML does not
        have.
        """
        rows = table.find_all("tr", recursive=False)
        if rows:
            return rows

        rows = []
        for tbody in table.find_all("tbody", recursive=False):
            rows.extend(tbody.find_all("tr", recursive=False))
        return rows

    @staticmethod
    def _to_cents(euro: str, cent: str) -> int:
        return int(euro) * 100 + int(cent or 0)

    @staticmethod
    def _decode_payload(part) -> str:
        payload = part.get_payload(decode=True)
        charset = part.get_content_charset() or "utf-8"
        return payload.decode(charset, errors="replace")
