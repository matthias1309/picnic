"""
Backfill product categories from the keyword rules (AC-024-05).

Run after the REQ-024 migration, and again whenever CATEGORY_RULES is
extended. Products with a manual assignment are never touched, and a second
run reports 0 changes.

Usage:
    python -m backend.scripts.categorize_products
"""

from backend.database import SessionLocal
from backend.services import category_service


def main() -> None:
    db = SessionLocal()
    try:
        changed = category_service.apply_rules(db)
        print(f"Categorized {changed} product(s).")
    finally:
        db.close()


if __name__ == "__main__":
    main()
