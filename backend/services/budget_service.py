"""
Persisted monthly budget configuration.

Traces: ARCH-011
"""

from sqlalchemy.orm import Session

from backend.config import settings
from backend.models import BudgetSetting

BUDGET_SETTING_ID = 1


def get_monthly_budget_cents(db: Session) -> int:
    """Return the persisted monthly budget, or the .env default if unset (AC-011-06)."""
    row = db.get(BudgetSetting, BUDGET_SETTING_ID)
    if row is None:
        return settings.monthly_budget_cents
    return row.monthly_budget_cents


def set_monthly_budget_cents(db: Session, monthly_budget_cents: int) -> int:
    """Create or update the persisted monthly budget, returning the new value (AC-011-06)."""
    row = db.get(BudgetSetting, BUDGET_SETTING_ID)
    if row is None:
        row = BudgetSetting(id=BUDGET_SETTING_ID, monthly_budget_cents=monthly_budget_cents)
        db.add(row)
    else:
        row.monthly_budget_cents = monthly_budget_cents
    db.commit()
    return row.monthly_budget_cents
