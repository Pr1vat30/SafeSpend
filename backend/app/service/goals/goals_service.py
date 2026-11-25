import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.api.dto.goals.goals_dto import (
    GoalCreateDTO,
    GoalExtendDeadlineDTO,
    GoalListResponseDTO,
    GoalResponseDTO,
    GoalUpdateDTO,
)
from app.dao.goals.goal_dao import GoalDAO
from app.models.goals.goal_model import Goal

# -- DA DECOMMENTARE QUANDO I MODULI DEI COLLEGHI SARANNO SU MAIN --
# from app.service.what_if_simulator import WhatIfSimulator
# from app.dao.recurring_rule_dao import RecurringRuleDAO
# ------------------------------------------------------------------

ROME_TZ = ZoneInfo("Europe/Rome")


class GoalService:
    """
    SS5 - Gestione Obiettivi di Risparmio (RF_OBI_1 .. RF_OBI_4).
    """

    def __init__(
        self,
        goal_dao: GoalDAO,
        what_if_simulator=None,
        recurring_rule_dao=None,
    ):
        self.goal_dao = goal_dao
        self.what_if_simulator = what_if_simulator
        self.recurring_rule_dao = recurring_rule_dao

    async def list_goals(self, user_id: int) -> GoalListResponseDTO:
        goals = await self.goal_dao.get_all_by_user(user_id)
        today = datetime.now(ROME_TZ).date()

        dto_list: list[GoalResponseDTO] = []
        total_saved = Decimal("0.00")
        total_target = Decimal("0.00")

        for g in goals:
            saved = await self.goal_dao.get_saved_amount(g.id_goal, user_id)
            rule_id = await self.goal_dao.get_linked_rule_id(g.id_goal, user_id)
            dto_list.append(
                self._to_response_dto(g, today, saved_amount=saved, id_recurring_rule=rule_id)
            )
            total_saved += saved
            total_target += g.target_amount

        return GoalListResponseDTO(
            goals=dto_list,
            total_saved=total_saved,
            total_target=total_target,
        )

    async def create_goal(self, user_id: int, payload: GoalCreateDTO) -> GoalResponseDTO:
        today = datetime.now(ROME_TZ).date()

        buffer_warning = await self._check_buffer_impact(
            user_id=user_id,
            installment_amount=payload.installment_amount,
            installment_frequency=payload.installment_frequency,
            deadline=payload.deadline,
        )

        new_goal = Goal(
            id_user=user_id,
            name=payload.name,
            target_amount=payload.target_amount,
            deadline=payload.deadline,
            installment_frequency=payload.installment_frequency,
            installment_amount=payload.installment_amount,
            status="active",
        )
        saved_goal = await self.goal_dao.create(new_goal)

        # -- DA SINCRONIZZARE CON RECURRING RULE (quando PR #33 va su main) --
        recurring_rule_id: int | None = None
        if payload.create_recurring_rule and self.recurring_rule_dao:
            rule = await self.recurring_rule_dao.create_goal_saving_rule(
                user_id=user_id,
                goal_id=saved_goal.id_goal,
                name=f"Accantonamento: {payload.name}",
                amount=payload.installment_amount,
                frequency=payload.installment_frequency,
                start_date=today,
                end_date=payload.deadline,
            )
            recurring_rule_id = rule.id_recurring_rule
        # -------------------------------------------------------------------

        return self._to_response_dto(
            saved_goal,
            today,
            saved_amount=Decimal("0.00"),
            id_recurring_rule=recurring_rule_id,
            buffer_warning=buffer_warning,
        )

    async def update_goal(
        self, user_id: int, goal_id: int, payload: GoalUpdateDTO
    ) -> GoalResponseDTO:
        goal = await self._get_user_goal_or_404(goal_id, user_id)
        today = datetime.now(ROME_TZ).date()

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(goal, field, value)

        if goal.installment_amount > goal.target_amount:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="La rata di accantonamento non può superare l'importo target.",
            )

        saved_amount = await self.goal_dao.get_saved_amount(goal.id_goal, user_id)
        if saved_amount >= goal.target_amount:
            goal.status = "completed"
        elif goal.status == "expired" and goal.deadline > today:
            goal.status = "active"

        buffer_warning = await self._check_buffer_impact(
            user_id=user_id,
            installment_amount=goal.installment_amount,
            installment_frequency=goal.installment_frequency,
            deadline=goal.deadline,
        )

        updated = await self.goal_dao.update(goal)
        rule_id = await self.goal_dao.get_linked_rule_id(updated.id_goal, user_id)
        return self._to_response_dto(
            updated,
            today,
            saved_amount=saved_amount,
            id_recurring_rule=rule_id,
            buffer_warning=buffer_warning,
        )

    async def extend_deadline(
        self, user_id: int, goal_id: int, payload: GoalExtendDeadlineDTO
    ) -> GoalResponseDTO:
        """
        RF_OBI_4: Proroga la scadenza di un obiettivo scaduto o in ritardo
        e riattiva lo stato se non ancora completato.
        """
        goal = await self._get_user_goal_or_404(goal_id, user_id)
        today = datetime.now(ROME_TZ).date()

        if payload.new_deadline <= goal.deadline:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="La nuova scadenza deve essere successiva alla scadenza attuale.",
            )

        goal.deadline = payload.new_deadline
        saved_amount = await self.goal_dao.get_saved_amount(goal.id_goal, user_id)
        if saved_amount < goal.target_amount:
            goal.status = "active"

        updated = await self.goal_dao.update(goal)
        rule_id = await self.goal_dao.get_linked_rule_id(updated.id_goal, user_id)
        return self._to_response_dto(
            updated, today, saved_amount=saved_amount, id_recurring_rule=rule_id
        )

    async def delete_goal(self, user_id: int, goal_id: int) -> None:
        goal = await self._get_user_goal_or_404(goal_id, user_id)
        await self.goal_dao.delete(goal)

    # --- Metodi privati di supporto ---

    async def _get_user_goal_or_404(self, goal_id: int, user_id: int) -> Goal:
        goal = await self.goal_dao.get_by_id(goal_id, user_id)
        if not goal:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Obiettivo con id={goal_id} non trovato.",
            )
        return goal

    async def _check_buffer_impact(
        self,
        user_id: int,
        installment_amount: Decimal,
        installment_frequency: str,
        deadline: date,
    ) -> str | None:
        """
        RF_OBI_2: Se WhatIfSimulator (B-05) è collegato, verifica se l'accantonamento
        periodico porta il saldo previsto sotto il Safety Buffer entro la scadenza.
        """
        if not self.what_if_simulator or installment_amount <= Decimal("0.00"):
            return None

        sim_result = await self.what_if_simulator.simulate_recurring_expense(
            user_id=user_id,
            amount=installment_amount,
            frequency=installment_frequency,
            end_date=deadline,
        )
        if getattr(sim_result, "breaches_safety_buffer", False):
            return (
                "Attenzione: questo accantonamento periodico potrebbe portare il tuo saldo "
                "al di sotto del Safety Buffer prima della scadenza."
            )
        return None

    def _to_response_dto(
        self,
        goal: Goal,
        today: date,
        saved_amount: Decimal = Decimal("0.00"),
        id_recurring_rule: int | None = None,
        buffer_warning: str | None = None,
    ) -> GoalResponseDTO:
        remaining = max(goal.target_amount - saved_amount, Decimal("0.00"))

        if goal.target_amount > Decimal("0.00"):
            raw_pct = float((saved_amount / goal.target_amount) * Decimal("100"))
            progress_pct = round(min(raw_pct, 100.0), 2)
        else:
            progress_pct = 100.0

        estimated_date: date | None = None
        if remaining == Decimal("0.00"):
            estimated_date = today
        elif goal.installment_amount > Decimal("0.00"):
            periods_needed = math.ceil(float(remaining / goal.installment_amount))
            period_days = 7 if goal.installment_frequency == "weekly" else 30
            estimated_date = today + timedelta(days=periods_needed * period_days)

        is_overdue = goal.deadline < today and remaining > Decimal("0.00")
        effective_status = "expired" if (is_overdue and goal.status == "active") else goal.status

        return GoalResponseDTO(
            id_goal=goal.id_goal,
            name=goal.name,
            target_amount=goal.target_amount,
            saved_amount=saved_amount,
            remaining_amount=remaining,
            installment_frequency=goal.installment_frequency,  # type: ignore[arg-type]
            installment_amount=goal.installment_amount,
            deadline=goal.deadline,
            status=effective_status,  # type: ignore[arg-type]
            progress_percentage=progress_pct,
            estimated_completion_date=estimated_date,
            is_overdue=is_overdue,
            buffer_warning=buffer_warning,
            id_recurring_rule=id_recurring_rule,
            created_at=goal.created_at,
        )
