"""
Product categorisation tests (TEST-024).

Traces: ARCH-024
Verifies: REQ-024 (AC-024-01, AC-024-02, AC-024-03, AC-024-04, AC-024-05)
"""

from backend.models import Product
from backend.services import category_service, receipt_service
from backend.services.category_service import CategoryKey


# TC-024-01
# Given no product named "Bio Vollmilch 3,8% 1L" exists
# And a keyword rule maps "milch" to the category "dairy"
# When a receipt containing "Bio Vollmilch 3,8% 1L" is parsed
# Then the created product has category_key "dairy"
# And the assignment is marked as rule-based, not manual
def test_new_product_is_categorized_by_rule_on_creation(db_session):
    # Arrange
    assert db_session.query(Product).filter(Product.name == "Bio Vollmilch 3,8% 1L").first() is None

    # Act
    product = receipt_service._get_or_create_product(db_session, "Bio Vollmilch 3,8% 1L")

    # Assert
    assert product.category_key == CategoryKey.DAIRY
    assert product.category_is_manual is False


# TC-024-02
# Given no keyword rule matches the product name "Ahoi-Brause Sortiment"
# When a receipt containing that article is parsed
# Then the created product has category_key None
def test_product_without_matching_rule_stays_uncategorized(db_session):
    # Arrange
    name = "Ahoi-Brause Sortiment"

    # Act
    product = receipt_service._get_or_create_product(db_session, name)

    # Assert
    assert product.category_key is None
    assert product.category_is_manual is False


# TC-024-03
# Given the rule ("milch", "dairy")
# When categorize is called with "MILCH 1L", "Bio Vollmilch" and "vollmilch bio"
# Then every call returns CategoryKey.DAIRY
def test_categorize_ignores_case_and_position():
    # Arrange
    names = ["MILCH 1L", "Bio Vollmilch", "vollmilch bio"]

    # Act
    results = [category_service.categorize(name) for name in names]

    # Assert
    assert results == [CategoryKey.DAIRY] * 3


# TC-024-04
# Given the ordered rule table
# When categorize is called with "Kokosmilch 400ml"
# Then it returns CategoryKey.PANTRY, not DAIRY
# When categorize is called with "Tiefkühl-Pizza Margherita"
# Then it returns CategoryKey.READY_MEALS, not FROZEN
# When categorize is called with "TK-Erbsen 750g"
# Then it returns CategoryKey.VEGETABLES, not FROZEN
def test_rule_order_resolves_false_friends_and_overlaps():
    # Arrange / Act / Assert — each case pins one ordering constraint
    # in CATEGORY_RULES (ARCH-024 Key Decision 3).
    assert category_service.categorize("Kokosmilch 400ml") == CategoryKey.PANTRY
    assert category_service.categorize("Tiefkühl-Pizza Margherita") == CategoryKey.READY_MEALS
    assert category_service.categorize("TK-Erbsen 750g") == CategoryKey.VEGETABLES


# TC-024-05
# Given the product "Ahoi-Brause Sortiment" is uncategorised
# When category_service.set_product_category(db, product.id, CategoryKey.SWEETS) is called
# Then the product has category_key "sweets"
# And category_is_manual is True
def test_set_product_category_marks_the_assignment_manual(db_session):
    # Arrange
    product = Product(name="Ahoi-Brause Sortiment")
    db_session.add(product)
    db_session.commit()

    # Act
    updated = category_service.set_product_category(db_session, product.id, CategoryKey.SWEETS)

    # Assert
    assert updated.category_key == CategoryKey.SWEETS
    assert updated.category_is_manual is True


# TC-024-06
# Given the product "Kokosmilch 400ml" was manually assigned to "pantry"
# When category_service.apply_rules(db) runs
# Then the product still has category_key "pantry"
# And category_is_manual is still True
def test_apply_rules_never_overwrites_a_manual_assignment(db_session):
    # Arrange — a name that a rule would otherwise claim
    product = Product(name="Kokosmilch 400ml")
    db_session.add(product)
    db_session.commit()
    category_service.set_product_category(db_session, product.id, CategoryKey.PANTRY)

    # Act
    category_service.apply_rules(db_session)

    # Assert
    db_session.refresh(product)
    assert product.category_key == CategoryKey.PANTRY
    assert product.category_is_manual is True


# TC-024-07
# Given products exist with category_key None
# When category_service.apply_rules(db) runs
# Then every product whose name matches a rule receives that category
# And the number of changed products is returned
def test_apply_rules_categorizes_existing_products(db_session):
    # Arrange
    db_session.add_all(
        [
            Product(name="Bio Vollmilch 3,8% 1L"),
            Product(name="Bananen 1kg"),
            Product(name="Ahoi-Brause Sortiment"),
        ]
    )
    db_session.commit()

    # Act
    changed = category_service.apply_rules(db_session)

    # Assert
    by_name = {product.name: product for product in db_session.query(Product).all()}
    assert changed == 2
    assert by_name["Bio Vollmilch 3,8% 1L"].category_key == CategoryKey.DAIRY
    assert by_name["Bananen 1kg"].category_key == CategoryKey.FRUIT
    assert by_name["Ahoi-Brause Sortiment"].category_key is None


# TC-024-08
# Given category_service.apply_rules(db) has already run
# When it runs a second time
# Then it reports 0 changed products
# And no product's category_key or category_is_manual differs from the first run
def test_apply_rules_is_idempotent(db_session):
    # Arrange
    db_session.add_all([Product(name="Bio Vollmilch 3,8% 1L"), Product(name="Bananen 1kg")])
    db_session.commit()
    category_service.apply_rules(db_session)
    before = {
        product.name: (product.category_key, product.category_is_manual)
        for product in db_session.query(Product).all()
    }

    # Act
    changed = category_service.apply_rules(db_session)

    # Assert
    after = {
        product.name: (product.category_key, product.category_is_manual)
        for product in db_session.query(Product).all()
    }
    assert changed == 0
    assert after == before
