"""Import every model here so metadata is complete (e.g. for future migrations)."""

from app.models.common.base import Base
from app.models.recurring_rule.recurring_rule_model import RecurringRuleModel

__all__ = ["Base", "RecurringRuleModel"]
