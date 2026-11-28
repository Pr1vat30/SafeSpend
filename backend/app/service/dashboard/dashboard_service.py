from datetime import date, timedelta
from decimal import Decimal

from app.api.dto.cashflow.schema import ProjectionRead
from app.api.dto.dashboard.schema import DashboardAlertRead, DashboardRead, UpcomingExpenseRead
from app.core.exceptions import ConflictError
from app.dao.cashflow.cashflow_dao import CashFlowDAO, PlannedMovement
from app.dao.dashboard.dashboard_dao import DashboardDAO
from app.models.recurring_rule.recurring_rule_model import RecurringRuleModel
from app.service.cashflow.cashflow_service import CashFlowService
from app.service.cashflow.recurrences import expand_occurrences


class DashboardService:
    def __init__(self, cashflow_dao: CashFlowDAO, dashboard_dao: DashboardDAO):
        self.cashflow_dao = cashflow_dao
        self.dashboard_dao = dashboard_dao
        self.cashflow_service = CashFlowService(cashflow_dao)

    async def get_dashboard(self, id_user: int, as_of: date) -> DashboardRead:
        async with self.cashflow_dao.projection_reader() as reader:
            reconciled = await reader.get_reconciled_balance(id_user, as_of)
            if reconciled is None:
                raise ConflictError("Inserisci il saldo iniziale per visualizzare la dashboard.")

            result = await self.cashflow_service.calculate_cash_flow_result(
                id_user, as_of, reader=reader
            )
            alert_rows = await self.dashboard_dao.get_visible_alerts(id_user, session=reader.db)

        end_date = result.projection.daily_balances[-1].date

        return DashboardRead(
            reconciled_balance=reconciled.amount,
            reconciliation_date=reconciled.reconciliation_date,
            safety_buffer=result.safety_buffer,
            projection=result.projection,
            sts_from_planned_income=self.get_sts_from_planned_income(
                result.projection, result.safety_buffer, result.planned_movements
            ),
            upcoming_expenses=self.get_upcoming_expenses(
                result.planned_movements, result.recurring_rules, as_of, end_date
            ),
            alerts=[DashboardAlertRead.model_validate(row) for row in alert_rows],
        )

    @staticmethod
    def get_upcoming_expenses(
        planned_movements: list[PlannedMovement],
        recurring_rules: list[RecurringRuleModel],
        start_date: date,
        end_date: date,
    ) -> list[UpcomingExpenseRead]:
        expenses = []

        for movement in planned_movements:
            if movement.type == "expense" and start_date <= movement.planned_date <= end_date:
                expenses.append(
                    UpcomingExpenseRead(
                        date=movement.planned_date,
                        name=movement.name,
                        amount=movement.amount,
                        source="planned",
                        source_id=movement.id_planned_transaction,
                    )
                )

        for rule in recurring_rules:
            if rule.type not in ("expense", "saving"):
                continue

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

            for day in dates:
                expenses.append(
                    UpcomingExpenseRead(
                        date=day,
                        name=rule.name,
                        amount=rule.amount,
                        source="recurring",
                        source_id=rule.id_recurring_rule,
                    )
                )

        expenses.sort(key=lambda expense: (expense.date, expense.source, expense.source_id))
        return expenses[:5]

    @staticmethod
    def get_sts_from_planned_income(
        projection: ProjectionRead,
        safety_buffer: Decimal,
        planned_movements: list[PlannedMovement],
    ) -> Decimal:
        income_by_date: dict[date, Decimal] = {}
        for movement in planned_movements:
            if movement.type == "income":
                day = movement.planned_date
                income_by_date[day] = income_by_date.get(day, Decimal("0.00")) + movement.amount

        cumulative_income = Decimal("0.00")
        balances_without_income = []

        for daily_balance in projection.daily_balances:
            cumulative_income += income_by_date.get(daily_balance.date, Decimal("0.00"))
            balances_without_income.append(daily_balance.balance - cumulative_income)

        sts_without_income = CashFlowService.calculate_sts(
            min(balances_without_income), safety_buffer
        )
        return projection.safe_to_spend - sts_without_income
