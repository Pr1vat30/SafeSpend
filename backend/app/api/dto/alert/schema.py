"""DTOs of the alerts (RF_CG_3). Alerts are created by the system, never by the user."""

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

AlertType = Literal["risk_level", "impending_expense", "sts_drop"]
AlertStatus = Literal["active", "read", "resolved"]


class AlertRead(BaseModel):
    """Response body. `from_attributes` allows validating ORM objects directly."""

    model_config = ConfigDict(from_attributes=True)

    id_alert: int
    type: AlertType
    message: str
    trigger_date: date
    status: AlertStatus
    created_at: datetime
    resolved_at: datetime | None
