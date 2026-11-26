from datetime import date, timedelta
from decimal import Decimal

from app.dao.cashflow.cashflow_dao import CashFlowDAO
from app.service.cashflow.forecast_strategy import ForecastStrategy


class ForecastEngine:
    def __init__(self, dao: CashFlowDAO, strategy: ForecastStrategy):
        self.dao = dao
        self.strategy = strategy

    async def forecast_daily_expenses(
        self, id_user: int, as_of: date, horizon_days: int
    ) -> dict[date, Decimal] | None:
        first_date = await self.dao.get_first_reconciliation_date(id_user, as_of)
        if first_date is None:
            return None

        start_date = max(first_date, as_of - timedelta(days=90))
        observed_days = (as_of - start_date).days
        if observed_days < 30:
            return None

        totals = await self.dao.get_daily_variable_expenses(id_user, start_date, as_of)
        history_dates = [start_date + timedelta(days=i) for i in range(observed_days)]
        category_ids = {category_id for _, category_id in totals}

        daily_forecast = Decimal("0.00")
        for category_id in category_ids:
            daily_expenses = [
                totals.get((day, category_id), Decimal("0.00")) for day in history_dates
            ]
            daily_forecast += self.strategy.estimate(daily_expenses)

        return {as_of + timedelta(days=i): daily_forecast for i in range(horizon_days)}
