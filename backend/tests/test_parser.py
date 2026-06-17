"""
Unit tests for the Picnic invoice HTML parser.

Traces: ARCH-002
Verifies: REQ-002 (AC-002-01, AC-002-05, AC-002-06)
"""

from datetime import date

import pytest

from backend.imap.parser import ParseError, ReceiptParser


# TC-002-01: Extract the text/html part from a raw MIME email
def test_extract_html_returns_html_part(make_raw_email, picnic_receipt_html):
    """
    Given a raw MIME email with a text/html part containing the invoice
    When ReceiptParser.extract_html() is called
    Then the HTML body of the text/html part is returned
    """
    # Arrange
    raw_email = make_raw_email(picnic_receipt_html)
    parser = ReceiptParser()

    # Act
    html = parser.extract_html(raw_email)

    # Assert
    assert "Max Premium Pistazien" in html


# TC-002-02: extract_html() raises ParseError when no HTML part exists
def test_extract_html_raises_when_no_html_part(make_raw_email):
    """
    Given a raw MIME email with only a text/plain part
    When ReceiptParser.extract_html() is called
    Then ParseError is raised
    """
    # Arrange
    raw_email = make_raw_email(html=None)
    parser = ReceiptParser()

    # Act & Assert
    with pytest.raises(ParseError):
        parser.extract_html(raw_email)


# TC-002-03, TC-008-03: Parse line items from an invoice email (regression: non-wrapped HTML)
def test_parse_extracts_line_items(picnic_receipt_html):
    """
    Given the HTML of a Picnic invoice (fixture: picnic_receipt.html)
    When ReceiptParser.parse() is called
    Then 5 items are returned
    And "Max Premium Pistazien" has quantity=1 and line_total_cents=454
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    parsed = parser.parse(picnic_receipt_html)

    # Assert
    assert len(parsed.items) == 5

    pistazien = next(item for item in parsed.items if item.name == "Max Premium Pistazien")
    assert pistazien.quantity == 1
    assert pistazien.line_total_cents == 454
    assert pistazien.unit_price_cents == 454


# TC-002-04, TC-008-03: Free ("gratis") items are parsed with zero price (regression: non-wrapped HTML)
def test_parse_handles_free_gratis_item(picnic_receipt_html):
    """
    Given an invoice item that is part of a "2+1 gratis" promotion and shows no price
    When ReceiptParser.parse() is called
    Then the item "CORNY Müsliriegel Schoko Banane" has unit_price_cents=0 and
    line_total_cents=0
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    parsed = parser.parse(picnic_receipt_html)

    # Assert
    free_item = next(
        item for item in parsed.items if item.name == "CORNY Müsliriegel Schoko Banane"
    )
    assert free_item.quantity == 2
    assert free_item.unit_price_cents == 0
    assert free_item.line_total_cents == 0


# TC-012-01: Parse line items in the current invoice format
def test_parse_current_format_extracts_items(picnic_receipt_current_html):
    """
    Given an invoice whose item rows use "border-bottom: 1px solid #EBEBEB"
    (space after the colon, uppercase hex; fixture: picnic_receipt_current.html)
    When ReceiptParser.parse() is called
    Then 3 items are returned with the expected quantities and totals
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    parsed = parser.parse(picnic_receipt_current_html)

    # Assert
    assert len(parsed.items) == 3

    eins = next(item for item in parsed.items if item.name == "Testprodukt Eins")
    assert eins.quantity == 1
    assert eins.line_total_cents == 250

    zwei = next(item for item in parsed.items if item.name == "Testprodukt Zwei")
    assert zwei.quantity == 2
    assert zwei.line_total_cents == 358


# TC-012-02: Non-product summary rows are ignored
def test_parse_current_format_ignores_summary_rows(picnic_receipt_current_html):
    """
    Given an invoice whose Pfand summary row carries the item-row border style
    but has no product image (fixture: picnic_receipt_current.html)
    When ReceiptParser.parse() is called
    Then no parsed item is derived from that summary row and parse() does not raise
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    parsed = parser.parse(picnic_receipt_current_html)

    # Assert
    assert all(item.name != "Pfand" for item in parsed.items)


# TC-012-04, TC-012-03: End-to-end regression on a real production invoice email
def test_parse_original_email_extracts_all_items(picnic_receipt_original_raw):
    """
    Given the raw MIME of a real, anonymized Picnic "Dein Bon" email that
    previously failed to parse in production (fixture: picnic_receipt_original.html)
    When ReceiptParser.extract_html() then parse() are called
    Then all 33 line items are extracted, grouped under the two order numbers
    "209-521-1175" and "204-701-1435", summing to 6542 cents
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    html = parser.extract_html(picnic_receipt_original_raw)
    parsed = parser.parse(html)

    # Assert
    assert len(parsed.items) == 33
    assert {item.order_number for item in parsed.items} == {"209-521-1175", "204-701-1435"}
    assert sum(item.line_total_cents for item in parsed.items) == 6542


# TC-013-01: Parser assigns each item its order number
def test_parse_assigns_order_numbers(picnic_receipt_current_html):
    """
    Given an invoice with two Bestellnr sections (fixture: picnic_receipt_current.html)
    When ReceiptParser.parse() is called
    Then each item carries the order_number of the section it appears in
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    parsed = parser.parse(picnic_receipt_current_html)

    # Assert
    order_by_name = {item.name: item.order_number for item in parsed.items}
    assert order_by_name["Testprodukt Eins"] == "209-521-1175"
    assert order_by_name["Testprodukt Zwei"] == "209-521-1175"
    assert order_by_name["Testprodukt Drei"] == "204-701-1435"


# TC-013-02: Single-order invoice assigns its order number to every item
def test_parse_single_order_number(picnic_receipt_html):
    """
    Given the picnic_receipt.html fixture (single Bestellnr 102-651-1311)
    When ReceiptParser.parse() is called
    Then every parsed item has order_number "102-651-1311"
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    parsed = parser.parse(picnic_receipt_html)

    # Assert
    assert parsed.items
    assert all(item.order_number == "102-651-1311" for item in parsed.items)


# TC-014-01: Parser extracts the delivery date from the invoice body
def test_parse_extracts_delivery_date(picnic_receipt_current_html):
    """
    Given an invoice whose body states "Lieferung von Freitag 15 Mai 2026"
    (fixture: picnic_receipt_current.html)
    When ReceiptParser.parse() is called
    Then ParsedReceipt.delivery_date == date(2026, 5, 15)
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    parsed = parser.parse(picnic_receipt_current_html)

    # Assert
    assert parsed.delivery_date == date(2026, 5, 15)


# TC-014-02: All German month names are recognised
@pytest.mark.parametrize(
    "month_name, expected_month",
    [
        ("Januar", 1),
        ("Februar", 2),
        ("März", 3),
        ("April", 4),
        ("Mai", 5),
        ("Juni", 6),
        ("Juli", 7),
        ("August", 8),
        ("September", 9),
        ("Oktober", 10),
        ("November", 11),
        ("Dezember", 12),
    ],
)
def test_parse_recognises_all_german_month_names(
    picnic_receipt_current_html, month_name, expected_month
):
    """
    Given the delivery sentence rendered with each German month name
    When ReceiptParser.parse() is called
    Then delivery_date.month equals the corresponding 1..12 value
    """
    # Arrange
    html = picnic_receipt_current_html.replace("15 Mai 2026", f"15 {month_name} 2026")
    parser = ReceiptParser()

    # Act
    parsed = parser.parse(html)

    # Assert
    assert parsed.delivery_date == date(2026, expected_month, 15)


# TC-014-03: Missing delivery date yields None without affecting other parsing
def test_parse_without_delivery_sentence_yields_none(picnic_receipt_html):
    """
    Given an invoice with no "Lieferung von ..." sentence (fixture: picnic_receipt.html)
    When ReceiptParser.parse() is called
    Then delivery_date is None
    And the items and stated total are still extracted (no regression)
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    parsed = parser.parse(picnic_receipt_html)

    # Assert
    assert parsed.delivery_date is None
    assert len(parsed.items) == 5
    assert parsed.stated_total_cents == 1320


# TC-014-01 (real data): the delivery date is parsed from a real production email
def test_parse_original_email_extracts_delivery_date(picnic_receipt_original_raw):
    """
    Given the raw MIME of a real, anonymized Picnic email whose body states
    "deiner Lieferung von Montag 15 Juni 2026"
    When ReceiptParser.extract_html() then parse() are called
    Then delivery_date == date(2026, 6, 15)
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    html = parser.extract_html(picnic_receipt_original_raw)
    parsed = parser.parse(html)

    # Assert
    assert parsed.delivery_date == date(2026, 6, 15)


# TC-002-05: parse() raises ParseError on malformed invoice HTML
def test_parse_raises_on_malformed_html(picnic_receipt_malformed_html):
    """
    Given HTML that does not contain any Picnic item rows (fixture:
    picnic_receipt_malformed.html)
    When ReceiptParser.parse() is called
    Then ParseError is raised
    """
    # Arrange
    parser = ReceiptParser()

    # Act & Assert
    with pytest.raises(ParseError):
        parser.parse(picnic_receipt_malformed_html)


# TC-002-06, TC-008-03: Extract the stated order total ("Gesamtbetrag") (regression: non-wrapped HTML)
def test_parse_extracts_stated_total(picnic_receipt_html):
    """
    Given the HTML of a Picnic invoice containing a "Gesamtbetrag" total of 13,20€
    When ReceiptParser.parse() is called
    Then ParsedReceipt.stated_total_cents == 1320
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    parsed = parser.parse(picnic_receipt_html)

    # Assert
    assert parsed.stated_total_cents == 1320


# TC-008-01: Prices are extracted when price table rows are wrapped in <tbody>
def test_parse_extracts_prices_with_tbody_wrapped_rows(picnic_receipt_forwarded_html):
    """
    Given the HTML of a Picnic invoice where the price table's <tr> rows are
    wrapped in a <tbody> element (fixture: picnic_receipt_forwarded.html)
    When ReceiptParser.parse() is called
    Then "Max Premium Pistazien" has quantity=1, unit_price_cents=454 and
    line_total_cents=454, matching the non-wrapped HTML (TC-002-03)
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    parsed = parser.parse(picnic_receipt_forwarded_html)

    # Assert
    pistazien = next(item for item in parsed.items if item.name == "Max Premium Pistazien")
    assert pistazien.quantity == 1
    assert pistazien.line_total_cents == 454
    assert pistazien.unit_price_cents == 454


# TC-008-02: "Gratis" items remain zero-priced with <tbody>-wrapped tables
def test_parse_handles_free_gratis_item_with_tbody_wrapped_rows(picnic_receipt_forwarded_html):
    """
    Given the HTML of a Picnic invoice where tables are wrapped in <tbody>
    elements and one item is part of a "2+1 gratis" promotion with no price
    table rows (fixture: picnic_receipt_forwarded.html)
    When ReceiptParser.parse() is called
    Then that item has unit_price_cents=0 and line_total_cents=0
    """
    # Arrange
    parser = ReceiptParser()

    # Act
    parsed = parser.parse(picnic_receipt_forwarded_html)

    # Assert
    free_item = next(
        item for item in parsed.items if item.name == "CORNY Müsliriegel Schoko Banane"
    )
    assert free_item.quantity == 2
    assert free_item.unit_price_cents == 0
    assert free_item.line_total_cents == 0
