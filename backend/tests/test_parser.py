"""
Unit tests for the Picnic invoice HTML parser.

Traces: ARCH-002
Verifies: REQ-002 (AC-002-01, AC-002-05, AC-002-06)
"""

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


# TC-002-03: Parse line items from an invoice email
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


# TC-002-04: Free ("gratis") items are parsed with zero price
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


# TC-002-06: Extract the stated order total ("Gesamtbetrag")
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
