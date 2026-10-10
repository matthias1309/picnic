"""
Product categorisation tests (TEST-024).

Traces: ARCH-024
Verifies: REQ-024 (AC-024-01, AC-024-02, AC-024-03, AC-024-04, AC-024-05)
"""

import pytest

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
# Then it returns CategoryKey.CANNED, not DAIRY
# When categorize is called with "Tiefkühl-Pizza Margherita"
# Then it returns CategoryKey.READY_MEALS, not FROZEN
# When categorize is called with "TK-Erbsen 750g"
# Then it returns CategoryKey.VEGETABLES, not FROZEN
def test_rule_order_resolves_false_friends_and_overlaps():
    # Arrange / Act / Assert — each case pins one ordering constraint
    # in CATEGORY_RULES (ARCH-024 Key Decision 3).
    assert category_service.categorize("Kokosmilch 400ml") == CategoryKey.CANNED
    assert category_service.categorize("Tiefkühl-Pizza Margherita") == CategoryKey.READY_MEALS
    assert category_service.categorize("TK-Erbsen 750g") == CategoryKey.VEGETABLES

    # Regression (CR-024 findings 1 and 2): a bare "eis" keyword also matched
    # "Reis" and "Speiseöl", and the fruit keywords claimed juice and fruit
    # yoghurt before the beverage/dairy rules could.
    assert category_service.categorize("Basmati Reis 1kg") == CategoryKey.GRAINS
    assert category_service.categorize("Speiseöl 1L") == CategoryKey.CONDIMENTS
    assert category_service.categorize("Apfelsaft 1L") == CategoryKey.BEVERAGES
    assert category_service.categorize("Erdbeerjoghurt 150g") == CategoryKey.DAIRY
    assert category_service.categorize("Erdbeermarmelade") == CategoryKey.BREAKFAST


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


# --- TEST-026: finer shelf-stable categories (Traces: ARCH-026) -------------


def _seed_pre_split_products(db_session):
    """Rule-based products as the REQ-024 rules had categorised them."""
    db_session.add_all(
        [
            Product(name="Barilla Spaghetti", category_key=CategoryKey.PANTRY),
            Product(name="Paprika Chips", category_key=CategoryKey.SWEETS),
            Product(name="Passierte Tomaten", category_key=CategoryKey.VEGETABLES),
        ]
    )
    db_session.commit()


# TC-026-02
# Scenario Outline:
# Given no product named "<name>" exists
# When receipt_service._get_or_create_product(db, "<name>") is called
# Then the created product has category_key "<category>"
# And category_is_manual is False
@pytest.mark.parametrize(
    ("name", "category"),
    [
        ("Barilla Spaghetti No. 5", "grains"),
        ("Basmati Reis 1kg", "grains"),
        ("Rote Linsen 500g", "grains"),
        ("Kölln Haferflocken zart", "breakfast"),
        ("Erdbeer Konfitüre extra", "breakfast"),
        ("Nuss-Nougat-Creme 400g", "breakfast"),
        ("Weizenmehl Type 405", "baking"),
        ("Trockenhefe 3x7g", "baking"),
        ("Natives Olivenöl extra", "condiments"),
        ("Tomatenketchup", "condiments"),
        ("Gemüsebrühe Pulver", "condiments"),
        ("Passierte Tomaten 500g", "canned"),
        ("Kidneybohnen Dose", "canned"),
        ("Kokosmilch 400ml", "canned"),
        ("Paprika Chips", "snacks"),
        ("Salzstangen 250g", "snacks"),
        ("Gesalzene Erdnüsse", "snacks"),
        ("Reiswaffeln Natur", "snacks"),
    ],
)
def test_new_product_lands_in_its_shelf_stable_category(db_session, name, category):
    # Arrange
    assert db_session.query(Product).filter(Product.name == name).first() is None

    # Act
    product = receipt_service._get_or_create_product(db_session, name)

    # Assert
    assert product.category_key == category
    assert product.category_is_manual is False


# TC-026-03
# Scenario Outline:
# When category_service.categorize("<name>") is called
# Then it returns "<category>"
@pytest.mark.parametrize(
    ("name", "category"),
    [
        ("Ölsardinen in Olivenöl", "fish"),
        ("Preiselbeeren im Glas", "breakfast"),
        ("Milchreis Klassik", "sweets"),
        ("Kaffeebohnen Crema", "beverages"),
        ("Kichererbsen Dose", "grains"),
        ("Apfelessig naturtrüb", "condiments"),
        ("Rinderbrühe", "condiments"),
        ("Nektarinen 1kg", "fruit"),
        ("Wassereis Mix", "sweets"),
        ("Zahnpasta Sensitive", "personal_care"),
    ],
)
def test_short_keywords_do_not_misclassify_compound_names(name, category):
    # Arrange / Act
    result = category_service.categorize(name)

    # Assert
    assert result == category


# TC-026-04
# Given the product "Bio Dinkelgrieß" was manually assigned to "pantry"
# When category_service.apply_rules(db) runs
# Then the product still has category_key "pantry"
# And category_is_manual is still True
# And CATEGORY_LABELS[CategoryKey.PANTRY] is "Sonstige Trockenware"
def test_manual_pantry_assignment_survives_the_split(db_session):
    # Arrange — "grieß" would put this product into grains by rule
    product = Product(name="Bio Dinkelgrieß")
    db_session.add(product)
    db_session.commit()
    category_service.set_product_category(db_session, product.id, CategoryKey.PANTRY)

    # Act
    category_service.apply_rules(db_session)

    # Assert
    db_session.refresh(product)
    assert product.category_key == CategoryKey.PANTRY
    assert product.category_is_manual is True
    assert category_service.CATEGORY_LABELS[CategoryKey.PANTRY] == "Sonstige Trockenware"


# TC-026-05
# Given rule-based products stored with their pre-REQ-026 categories:
#   | name              | category_key |
#   | Barilla Spaghetti | pantry       |
#   | Paprika Chips     | sweets       |
#   | Passierte Tomaten | vegetables   |
# When category_service.apply_rules(db) runs
# Then it returns 3
# And "Barilla Spaghetti" has category_key "grains"
# And "Paprika Chips" has category_key "snacks"
# And "Passierte Tomaten" has category_key "canned"
# And every product still has category_is_manual False
def test_apply_rules_moves_rule_based_products_to_the_new_categories(db_session):
    # Arrange
    _seed_pre_split_products(db_session)

    # Act
    changed = category_service.apply_rules(db_session)

    # Assert
    by_name = {product.name: product for product in db_session.query(Product).all()}
    assert changed == 3
    assert by_name["Barilla Spaghetti"].category_key == CategoryKey.GRAINS
    assert by_name["Paprika Chips"].category_key == CategoryKey.SNACKS
    assert by_name["Passierte Tomaten"].category_key == CategoryKey.CANNED
    assert all(product.category_is_manual is False for product in by_name.values())


# TC-026-06
# Given the products from TC-026-05
# And category_service.apply_rules(db) has already run once
# When it runs a second time
# Then it returns 0
def test_recategorizing_backfill_is_idempotent(db_session):
    # Arrange
    _seed_pre_split_products(db_session)
    category_service.apply_rules(db_session)

    # Act
    changed = category_service.apply_rules(db_session)

    # Assert
    assert changed == 0


# TC-026-11
# Given CATEGORY_RULES
# When categorize(keyword) is called for every (keyword, category) rule
# Then every call returns that rule's own category
def test_no_keyword_rule_is_shadowed_by_an_earlier_rule():
    # Arrange
    rules = category_service.CATEGORY_RULES

    # Act
    shadowed = {
        keyword: category_service.categorize(keyword)
        for keyword, category in rules
        if category_service.categorize(keyword) != category
    }

    # Assert
    assert shadowed == {}


# TC-026-12
# Given CATEGORY_RULES
# Then every keyword occurs exactly once
def test_no_keyword_appears_twice():
    # Arrange
    keywords = [keyword for keyword, _ in category_service.CATEGORY_RULES]

    # Act
    duplicates = sorted({keyword for keyword in keywords if keywords.count(keyword) > 1})

    # Assert
    assert duplicates == []


# TC-027-01
# Scenario Outline:
# When category_service.categorize("<name>") is called
# Then it returns "canned"
@pytest.mark.parametrize(
    "name",
    [
        "Edeka Herzstücke Tomaten stückig mediterran",
        "Oro di Parma Bio Stückige Tomaten",
        "Gut&Günstig Tomaten passiert",
        "Gut&Günstig Getrocknete Tomaten in Öl",
        "Gut&Günstig Grüne Oliven mit Chili & Knoblauch",
        "Kühne Gewürzgurken",
        "Hengstenberg Sandwich Gurken",
        "Cornichons",
    ],
)
def test_preserved_tomato_olive_and_pickle_products_are_canned(name):
    # Arrange / Act
    result = category_service.categorize(name)

    # Assert
    assert result == CategoryKey.CANNED


# TC-027-02
# Scenario Outline:
# When category_service.categorize("<name>") is called
# Then it returns "<category>"
@pytest.mark.parametrize(
    ("name", "category"),
    [
        ("Gut&Günstig Mandeln gehackt", "snacks"),
        ("Meßmer Ingwer-Zitrone", "beverages"),
        ("Teekanne Türkischer Apfel", "beverages"),
        ("Mini Pflaumen Tomaten", "vegetables"),
        ("Herta Hähnchenbrust Butter-Chicken", "meat"),
        ("Dr. Oetker Chocolate Chunks", "baking"),
    ],
)
def test_general_keywords_do_not_win_inside_unrelated_products(name, category):
    # Arrange / Act
    result = category_service.categorize(name)

    # Assert
    assert result == category


# TC-027-03
# Scenario Outline:
# When category_service.categorize("<name>") is called
# Then it returns "<category>"
@pytest.mark.parametrize(
    ("name", "category"),
    [
        ("Rana Tortelloni", "ready_meals"),
        ("Steinhaus Tortelloni", "ready_meals"),
        ("Nissin Cup Noodles", "ready_meals"),
        ("Ostmann Paprika edelsüß", "condiments"),
        ("Top Taste Röstzwiebeln", "condiments"),
        ("Porree", "vegetables"),
    ],
)
def test_previously_unmatched_foods_reach_their_category(name, category):
    # Arrange / Act
    result = category_service.categorize(name)

    # Assert
    assert result == category


# TC-027-04
# Scenario Outline:
# When category_service.categorize("<name>") is called
# Then it returns "<category>"
@pytest.mark.parametrize(
    ("name", "category"),
    [
        ("Finish Spezial-Salz", "household"),
        ("Gut&Günstig Spezial Salz", "household"),
        ("Surig Essigspray", "household"),
        ("Drano Rohrfrei", "household"),
        ("Power Cell E-Block", "household"),
        ("Gut&Günstig Taschentücher Box 4-lagig", "personal_care"),
        ("Purina One Bifensis mit Lachs", "other"),
    ],
)
def test_non_food_products_leave_the_food_categories(name, category):
    # Arrange / Act
    result = category_service.categorize(name)

    # Assert
    assert result == category


# TC-027-05
# Scenario Outline:
# When category_service.categorize("<name>") is called
# Then it returns "<category>"
@pytest.mark.parametrize(
    ("name", "category"),
    [
        ("Natives Olivenöl extra", "condiments"),
        ("Ölsardinen in Olivenöl", "fish"),
        ("Thunfisch in Olivenöl", "fish"),
        ("Salatgurke", "vegetables"),
        ("Cherry Tomaten", "vegetables"),
        ("Tomatenketchup", "condiments"),
        ("Passierte Tomaten 500g", "canned"),
        ("Hackfleisch gemischt", "meat"),
        ("Teewurst fein", "meat"),
        ("Studentenfutter", "snacks"),
        ("Bio Butter 250g", "dairy"),
        ("Paprika rot", "vegetables"),
        ("Zwiebeln 1kg", "vegetables"),
        ("Schokolade Zartbitter", "sweets"),
        ("Speisesalz", "condiments"),
    ],
)
def test_new_rules_do_not_change_products_the_old_rules_got_right(name, category):
    # Arrange / Act
    result = category_service.categorize(name)

    # Assert
    assert result == category
