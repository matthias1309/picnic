"""
Product categorisation: the fixed category set, the keyword rules that assign
it, and the read/write helpers around Product.category_key.

Traces: ARCH-024
"""

from enum import StrEnum

from sqlalchemy.orm import Session

from backend.models import Product


class CategoryKey(StrEnum):
    """The fixed set of product categories (AC-024-06)."""

    FRUIT = "fruit"
    VEGETABLES = "vegetables"
    DAIRY = "dairy"
    BAKERY = "bakery"
    MEAT = "meat"
    FISH = "fish"
    FROZEN = "frozen"
    READY_MEALS = "ready_meals"
    BEVERAGES = "beverages"
    PANTRY = "pantry"
    SWEETS = "sweets"
    PERSONAL_CARE = "personal_care"
    HOUSEHOLD = "household"
    OTHER = "other"


CATEGORY_LABELS: dict[CategoryKey, str] = {
    CategoryKey.FRUIT: "Obst",
    CategoryKey.VEGETABLES: "Gemüse",
    CategoryKey.DAIRY: "Milchprodukte",
    CategoryKey.BAKERY: "Backwaren",
    CategoryKey.MEAT: "Fleisch",
    CategoryKey.FISH: "Fisch",
    CategoryKey.FROZEN: "Tiefkühl",
    CategoryKey.READY_MEALS: "Fertiggerichte",
    CategoryKey.BEVERAGES: "Getränke",
    CategoryKey.PANTRY: "Trockenware",
    CategoryKey.SWEETS: "Süßwaren",
    CategoryKey.PERSONAL_CARE: "Körperpflege",
    CategoryKey.HOUSEHOLD: "Haushalt",
    CategoryKey.OTHER: "Sonstiges",
}

UNCATEGORIZED_LABEL = "Nicht zugeordnet"

# Ordered: the first keyword found in the product name wins.
#
# Two ordering constraints are load-bearing and covered by TC-024-04:
#   1. False friends come before the general keyword they contain
#      ("kokosmilch" before "milch").
#   2. What a product *is* beats how it is stored: a frozen pizza is a ready
#      meal, frozen peas are vegetables. So type keywords precede the
#      storage keywords, and FROZEN only catches what nothing else claims.
CATEGORY_RULES: tuple[tuple[str, CategoryKey], ...] = (
    # -- false friends, before their general keyword --------------------
    ("kokosmilch", CategoryKey.PANTRY),
    ("mandelmilch", CategoryKey.BEVERAGES),
    ("hafermilch", CategoryKey.BEVERAGES),
    ("sojamilch", CategoryKey.BEVERAGES),
    ("milchreis", CategoryKey.SWEETS),
    ("milchschnitte", CategoryKey.SWEETS),
    ("erdnussbutter", CategoryKey.PANTRY),
    ("buttermilch", CategoryKey.DAIRY),
    ("fischstäbchen", CategoryKey.FISH),
    ("seife", CategoryKey.PERSONAL_CARE),
    ("spülmittel", CategoryKey.HOUSEHOLD),
    # -- compounds whose first word belongs elsewhere ---------------------
    # "Apfelsaft" is a beverage, not fruit; "Erdbeerjoghurt" is dairy, not
    # fruit. These must precede the fruit keywords they start with.
    ("saft", CategoryKey.BEVERAGES),
    ("nektar", CategoryKey.BEVERAGES),
    ("joghurt", CategoryKey.DAIRY),
    ("quark", CategoryKey.DAIRY),
    ("skyr", CategoryKey.DAIRY),
    ("marmelade", CategoryKey.PANTRY),
    ("konfitüre", CategoryKey.PANTRY),
    ("eis am stiel", CategoryKey.SWEETS),
    # -- ready meals, before the frozen/storage keywords -----------------
    ("pizza", CategoryKey.READY_MEALS),
    ("fertiggericht", CategoryKey.READY_MEALS),
    ("auflauf", CategoryKey.READY_MEALS),
    ("lasagne", CategoryKey.READY_MEALS),
    ("maultaschen", CategoryKey.READY_MEALS),
    ("suppe", CategoryKey.READY_MEALS),
    ("salatbowl", CategoryKey.READY_MEALS),
    # -- fruit ----------------------------------------------------------
    ("apfel", CategoryKey.FRUIT),
    ("äpfel", CategoryKey.FRUIT),
    ("banane", CategoryKey.FRUIT),
    ("birne", CategoryKey.FRUIT),
    ("erdbeer", CategoryKey.FRUIT),
    ("heidelbeer", CategoryKey.FRUIT),
    ("himbeer", CategoryKey.FRUIT),
    ("trauben", CategoryKey.FRUIT),
    ("orange", CategoryKey.FRUIT),
    ("mandarine", CategoryKey.FRUIT),
    ("zitrone", CategoryKey.FRUIT),
    ("limette", CategoryKey.FRUIT),
    ("mango", CategoryKey.FRUIT),
    ("avocado", CategoryKey.FRUIT),
    ("melone", CategoryKey.FRUIT),
    ("kiwi", CategoryKey.FRUIT),
    ("pfirsich", CategoryKey.FRUIT),
    ("nektarine", CategoryKey.FRUIT),
    ("pflaume", CategoryKey.FRUIT),
    ("ananas", CategoryKey.FRUIT),
    # -- vegetables ------------------------------------------------------
    ("erbsen", CategoryKey.VEGETABLES),
    ("tomate", CategoryKey.VEGETABLES),
    ("gurke", CategoryKey.VEGETABLES),
    ("paprika", CategoryKey.VEGETABLES),
    ("zwiebel", CategoryKey.VEGETABLES),
    ("knoblauch", CategoryKey.VEGETABLES),
    ("kartoffel", CategoryKey.VEGETABLES),
    ("möhre", CategoryKey.VEGETABLES),
    ("karotte", CategoryKey.VEGETABLES),
    ("salat", CategoryKey.VEGETABLES),
    ("spinat", CategoryKey.VEGETABLES),
    ("brokkoli", CategoryKey.VEGETABLES),
    ("blumenkohl", CategoryKey.VEGETABLES),
    ("zucchini", CategoryKey.VEGETABLES),
    ("aubergine", CategoryKey.VEGETABLES),
    ("champignon", CategoryKey.VEGETABLES),
    ("pilze", CategoryKey.VEGETABLES),
    ("lauch", CategoryKey.VEGETABLES),
    ("sellerie", CategoryKey.VEGETABLES),
    ("kohlrabi", CategoryKey.VEGETABLES),
    ("rucola", CategoryKey.VEGETABLES),
    ("kürbis", CategoryKey.VEGETABLES),
    ("gemüse", CategoryKey.VEGETABLES),
    # -- dairy ------------------------------------------------------------
    ("milch", CategoryKey.DAIRY),
    ("joghurt", CategoryKey.DAIRY),
    ("quark", CategoryKey.DAIRY),
    ("käse", CategoryKey.DAIRY),
    ("gouda", CategoryKey.DAIRY),
    ("mozzarella", CategoryKey.DAIRY),
    ("feta", CategoryKey.DAIRY),
    ("butter", CategoryKey.DAIRY),
    ("sahne", CategoryKey.DAIRY),
    ("schmand", CategoryKey.DAIRY),
    ("frischkäse", CategoryKey.DAIRY),
    ("skyr", CategoryKey.DAIRY),
    ("ei ", CategoryKey.DAIRY),
    ("eier", CategoryKey.DAIRY),
    # -- bakery ------------------------------------------------------------
    ("brot", CategoryKey.BAKERY),
    ("brötchen", CategoryKey.BAKERY),
    ("baguette", CategoryKey.BAKERY),
    ("toast", CategoryKey.BAKERY),
    ("croissant", CategoryKey.BAKERY),
    ("knäcke", CategoryKey.BAKERY),
    ("zwieback", CategoryKey.BAKERY),
    # -- meat ---------------------------------------------------------------
    ("hähnchen", CategoryKey.MEAT),
    ("hühner", CategoryKey.MEAT),
    ("pute", CategoryKey.MEAT),
    ("rind", CategoryKey.MEAT),
    ("schwein", CategoryKey.MEAT),
    ("hack", CategoryKey.MEAT),
    ("wurst", CategoryKey.MEAT),
    ("schinken", CategoryKey.MEAT),
    ("salami", CategoryKey.MEAT),
    ("speck", CategoryKey.MEAT),
    ("steak", CategoryKey.MEAT),
    ("schnitzel", CategoryKey.MEAT),
    # -- fish ----------------------------------------------------------------
    ("lachs", CategoryKey.FISH),
    ("thunfisch", CategoryKey.FISH),
    ("forelle", CategoryKey.FISH),
    ("garnele", CategoryKey.FISH),
    ("shrimp", CategoryKey.FISH),
    ("hering", CategoryKey.FISH),
    ("makrele", CategoryKey.FISH),
    ("kabeljau", CategoryKey.FISH),
    ("fisch", CategoryKey.FISH),
    # -- beverages ------------------------------------------------------------
    ("wasser", CategoryKey.BEVERAGES),
    ("saft", CategoryKey.BEVERAGES),
    ("cola", CategoryKey.BEVERAGES),
    ("limonade", CategoryKey.BEVERAGES),
    ("bier", CategoryKey.BEVERAGES),
    ("wein", CategoryKey.BEVERAGES),
    ("kaffee", CategoryKey.BEVERAGES),
    ("espresso", CategoryKey.BEVERAGES),
    ("tee", CategoryKey.BEVERAGES),
    ("smoothie", CategoryKey.BEVERAGES),
    ("schorle", CategoryKey.BEVERAGES),
    # -- sweets ----------------------------------------------------------------
    ("schokolade", CategoryKey.SWEETS),
    ("schoko", CategoryKey.SWEETS),
    ("keks", CategoryKey.SWEETS),
    ("bonbon", CategoryKey.SWEETS),
    ("gummibär", CategoryKey.SWEETS),
    ("chips", CategoryKey.SWEETS),
    ("eiscreme", CategoryKey.SWEETS),
    ("speiseeis", CategoryKey.SWEETS),
    ("wassereis", CategoryKey.SWEETS),
    ("kuchen", CategoryKey.SWEETS),
    ("riegel", CategoryKey.SWEETS),
    ("waffel", CategoryKey.SWEETS),
    # -- pantry -----------------------------------------------------------------
    ("nudel", CategoryKey.PANTRY),
    ("pasta", CategoryKey.PANTRY),
    ("spaghetti", CategoryKey.PANTRY),
    ("reis", CategoryKey.PANTRY),
    ("mehl", CategoryKey.PANTRY),
    ("zucker", CategoryKey.PANTRY),
    ("salz", CategoryKey.PANTRY),
    ("pfeffer", CategoryKey.PANTRY),
    ("öl", CategoryKey.PANTRY),
    ("essig", CategoryKey.PANTRY),
    ("linsen", CategoryKey.PANTRY),
    ("bohnen", CategoryKey.PANTRY),
    ("haferflocken", CategoryKey.PANTRY),
    ("müsli", CategoryKey.PANTRY),
    ("honig", CategoryKey.PANTRY),
    ("marmelade", CategoryKey.PANTRY),
    ("ketchup", CategoryKey.PANTRY),
    ("senf", CategoryKey.PANTRY),
    ("mayonnaise", CategoryKey.PANTRY),
    ("passierte tomaten", CategoryKey.PANTRY),
    ("konserve", CategoryKey.PANTRY),
    # -- personal care -------------------------------------------------------------
    ("shampoo", CategoryKey.PERSONAL_CARE),
    ("duschgel", CategoryKey.PERSONAL_CARE),
    ("zahnpasta", CategoryKey.PERSONAL_CARE),
    ("zahnbürste", CategoryKey.PERSONAL_CARE),
    ("deo", CategoryKey.PERSONAL_CARE),
    ("rasier", CategoryKey.PERSONAL_CARE),
    ("creme", CategoryKey.PERSONAL_CARE),
    ("windel", CategoryKey.PERSONAL_CARE),
    ("binden", CategoryKey.PERSONAL_CARE),
    ("tampon", CategoryKey.PERSONAL_CARE),
    ("taschentuch", CategoryKey.PERSONAL_CARE),
    # -- household -------------------------------------------------------------------
    ("waschmittel", CategoryKey.HOUSEHOLD),
    ("weichspüler", CategoryKey.HOUSEHOLD),
    ("reiniger", CategoryKey.HOUSEHOLD),
    ("müllbeutel", CategoryKey.HOUSEHOLD),
    ("toilettenpapier", CategoryKey.HOUSEHOLD),
    ("küchenrolle", CategoryKey.HOUSEHOLD),
    ("alufolie", CategoryKey.HOUSEHOLD),
    ("frischhaltefolie", CategoryKey.HOUSEHOLD),
    ("batterie", CategoryKey.HOUSEHOLD),
    ("kerze", CategoryKey.HOUSEHOLD),
    # -- storage form, last: only what nothing else claimed ---------------------------
    ("tiefkühl", CategoryKey.FROZEN),
    ("tk-", CategoryKey.FROZEN),
)


def categorize(name: str) -> CategoryKey | None:
    """Return the first category whose keyword occurs in the product name."""
    haystack = name.casefold()
    for keyword, category in CATEGORY_RULES:
        if keyword in haystack:
            return category
    return None


def set_product_category(db: Session, product_id: int, category_key: CategoryKey) -> Product | None:
    """Assign a category by hand, marking it manual so rules never override it.

    Returns None if no product with the given id exists (AC-024-03).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if product is None:
        return None

    product.category_key = category_key
    product.category_is_manual = True
    db.commit()
    return product


def apply_rules(db: Session) -> int:
    """Categorize every product without a manual assignment (AC-024-05).

    Returns how many products actually changed, which makes a second run
    report 0 without needing a separate "already done" flag.
    """
    products = db.query(Product).filter(Product.category_is_manual.is_(False)).all()

    changed = 0
    for product in products:
        category = categorize(product.name)
        if category is not None and product.category_key != category:
            product.category_key = category
            changed += 1

    if changed:
        db.commit()
    return changed
