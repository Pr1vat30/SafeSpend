from calendar import monthrange
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal

from app.api.dto.cashflow.schema import DailyBalanceRead, ProjectionRead
from app.core.exceptions import ConflictError
from app.dao.cashflow.cashflow_dao import CashFlowDAO, PlannedMovement
from app.models.recurring_rule.recurring_rule_model import RecurringRuleModel
from app.service.cashflow.recurrences import expand_occurrences


class CashFlowService:
    def __init__(self, dao: CashFlowDAO):
        self.dao = dao

    async def calculate_cash_flow(
        self,
        id_user: int,
        as_of: date,
        *,
        forecast_expenses: dict[date, Decimal] | None = None,
    ) -> ProjectionRead:
        async with self.dao.projection_reader() as reader:
            settings = await reader.get_projection_settings(id_user)
            if settings is None:
                raise ConflictError("Completa il profilo finanziario per calcolare la proiezione.")

            starting_balance = await reader.get_starting_balance(id_user, as_of)
            if starting_balance is None:
                raise ConflictError("Inserisci il saldo iniziale per calcolare la proiezione.")

            end_date = as_of + timedelta(days=settings.horizon_days - 1)
            planned_movements = await reader.get_planned_transactions(id_user, as_of, end_date)
            recurring_rules = await reader.get_recurring_rules(id_user, as_of, end_date)
            income_rules = await reader.get_income_rules(id_user, as_of)

        daily_changes = self.build_daily_changes(
            planned_movements, recurring_rules, as_of, end_date
        )
        next_income_date = self.get_next_income_date(income_rules, as_of)

        monthly_estimate = settings.estimated_variable_expenses
        estimate_missing = forecast_expenses is None and monthly_estimate is None

        if forecast_expenses is not None:
            variable_expenses = forecast_expenses
        elif monthly_estimate is not None:
            variable_expenses = self.distribute_monthly_estimate(
                monthly_estimate, as_of, settings.horizon_days
            )
        else:
            variable_expenses = {}

        daily_balances = self.project_daily_balances(
            starting_balance, as_of, settings.horizon_days, daily_changes, variable_expenses
        )
        projection = self.summarize_projection(
            daily_balances, settings.safety_buffer, next_income_date
        )
        projection.variable_expense_estimate_missing = estimate_missing
        return projection

    @staticmethod
    def classify_risk(
        minimum_balance: Decimal, safety_buffer: Decimal
    ) -> Literal["Sostenibile", "Attenzione", "Critico"]:
        if minimum_balance < 0:
            return "Critico"
        if minimum_balance < safety_buffer:
            return "Attenzione"
        return "Sostenibile"

    @staticmethod
    def project_daily_balances(
        starting_balance: Decimal,
        start_date: date,
        horizon_days: int,
        daily_changes: dict[date, Decimal],
        variable_expenses: dict[date, Decimal],
    ) -> list[DailyBalanceRead]:
        balance = starting_balance
        projection = []

        for offset in range(horizon_days):
            day = start_date + timedelta(days=offset)
            balance += daily_changes.get(day, Decimal("0.00"))
            balance -= variable_expenses.get(day, Decimal("0.00"))
            projection.append(DailyBalanceRead(date=day, balance=balance))

        return projection

    @staticmethod
    def build_daily_changes(
        planned_movements: list[PlannedMovement],
        recurring_rules: list[RecurringRuleModel],
        start_date: date,
        end_date: date,
    ) -> dict[date, Decimal]:
        daily_changes: dict[date, Decimal] = {}

        for movement in planned_movements:
            day = movement.planned_date
            amount = movement.amount if movement.type == "income" else -movement.amount
            daily_changes[day] = daily_changes.get(day, Decimal("0.00")) + amount

        for rule in recurring_rules:
            first_unprocessed = start_date
            if rule.last_processed_occurrence_date is not None:
                first_unprocessed = max(
                    start_date,
                    rule.last_processed_occurrence_date + timedelta(days=1),
                )

            dates = expand_occurrences(
                first=rule.first_occurrence_date,
                frequency=rule.frequency,
                start=first_unprocessed,
                stop=end_date,
                end=rule.end_date,
            )

            amount = rule.amount if rule.type == "income" else -rule.amount
            for day in dates:
                daily_changes[day] = daily_changes.get(day, Decimal("0.00")) + amount

        return daily_changes

    def summarize_projection(
        self,
        daily_balances: list[DailyBalanceRead],
        safety_buffer: Decimal,
        next_income_date: date | None,
    ) -> ProjectionRead:
        minimum_day = min(daily_balances, key=lambda day: (day.balance, day.date))
        safe_to_spend = max(Decimal("0.00"), minimum_day.balance - safety_buffer)

        days = len(daily_balances)
        if next_income_date is not None:
            days = (next_income_date - daily_balances[0].date).days

        daily_safe_to_spend = (safe_to_spend / days).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )

        return ProjectionRead(
            daily_balances=daily_balances,
            minimum_balance=minimum_day.balance,
            critical_date=minimum_day.date,
            safe_to_spend=safe_to_spend,
            daily_safe_to_spend=daily_safe_to_spend,
            risk_level=self.classify_risk(minimum_day.balance, safety_buffer),
        )

    @staticmethod
    def get_next_income_date(income_rules: list[RecurringRuleModel], as_of: date) -> date | None:
        next_income_date = None
        max_days_between_occurrences = {"weekly": 7, "monthly": 31, "yearly": 366}

        for rule in income_rules:
            start = max(as_of + timedelta(days=1), rule.first_occurrence_date)

            if rule.last_processed_occurrence_date is not None:
                start = max(start, rule.last_processed_occurrence_date + timedelta(days=1))

            stop = start + timedelta(days=max_days_between_occurrences[rule.frequency])
            dates = expand_occurrences(
                first=rule.first_occurrence_date,
                frequency=rule.frequency,
                start=start,
                stop=stop,
                end=rule.end_date,
            )

            if dates and (next_income_date is None or dates[0] < next_income_date):
                next_income_date = dates[0]

        return next_income_date

    @staticmethod
    def distribute_monthly_estimate(
        monthly_estimate: Decimal,
        start_date: date,
        horizon_days: int,
    ) -> dict[date, Decimal]:
        monthly_cents = int(monthly_estimate * 100)
        estimates = {}

        for offset in range(horizon_days):
            day = start_date + timedelta(days=offset)
            days_in_month = monthrange(day.year, day.month)[1]
            daily_cents, remainder = divmod(monthly_cents, days_in_month)

            if day.day <= remainder:
                daily_cents += 1

            estimates[day] = Decimal(daily_cents).scaleb(-2)

        return estimates
