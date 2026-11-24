import math
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from fastapi import HTTPException, status

from app.api.dto.goals.goals_dto import (
    GoalContributionDTO,
    GoalCreateDTO,
    GoalExtendDeadlineDTO,
    GoalListResponseDTO,
    GoalResponseDTO,
    GoalUpdateDTO,
)

# from app.models.goals import Goal -- DA DEFINIRE INSIEME AI DAO


# -- STUB TEMPORANEO DA RIMUOVERE QUANDO SI IMPORTA IL MODELLO ORM --
class Goal:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


# ------------------------------------------------------------------

# -- DA DECOMMENTARE QUANDO I MODULI SARANNO DISPONIBILI --
# from app.dao.goal_dao import GoalDAO
# from app.service.what_if_simulator import WhatIfSimulator
# from app.dao.recurring_rule_dao import RecurringRuleDAO
# --------------------------------------------------------

ROME_TZ = ZoneInfo("Europe/Rome")


class GoalService:
    """
    SS5 - Gestione Obiettivi di Risparmio (RF_OBI_1 .. RF_OBI_4).
    """

    def __init__(self, goal_dao, what_if_simulator=None, recurring_rule_dao=None):
        self.goal_dao = goal_dao
        self.what_if_simulator = what_if_simulator
        self.recurring_rule_dao = recurring_rule_dao

    async def list_goals(self, user_id: int) -> GoalListResponseDTO:
        goals = await self.goal_dao.get_all_by_user(user_id)
        today = datetime.now(ROME_TZ).date()

        dto_list = [self._to_response_dto(g, today) for g in goals]
        total_saved = sum((g.saved_amount for g in goals), Decimal("0.00"))
        total_target = sum((g.target_amount for g in goals), Decimal("0.00"))

        return GoalListResponseDTO(
            goals=dto_list,
            total_saved=total_saved,
            total_target=total_target,
        )

    async def create_goal(self, user_id: int, payload: GoalCreateDTO) -> GoalResponseDTO:
        today = datetime.now(ROME_TZ).date()

        # Verifica opzionale impatto sul Safety Buffer tramite WhatIfSimulator
        buffer_warning = await self._check_buffer_impact(
            user_id=user_id,
            monthly_amount=payload.monthly_contribution,
            deadline=payload.deadline,
        )

        # -- DA SINCRONIZZARE CON RECURRING RULE --
        recurring_rule_id = None
        if (
            payload.create_recurring_rule
            and payload.monthly_contribution > Decimal("0.00")
            and self.recurring_rule_dao
        ):
            # Crea regola ricorrente mensile collegata all'accantonamento
            rule = await self.recurring_rule_dao.create_goal_saving_rule(
                user_id=user_id,
                name=f"Accantonamento: {payload.name}",
                amount=payload.monthly_contribution,
                start_date=today,
                end_date=payload.deadline,
            )
            recurring_rule_id = rule.id_recurring_rule
        # ------------------------------------

        initial_status = "COMPLETED" if payload.saved_amount >= payload.target_amount else "ACTIVE"

        new_goal = Goal(
            id_user=user_id,
            id_recurring_rule=recurring_rule_id,
            name=payload.name,
            target_amount=payload.target_amount,
            saved_amount=payload.saved_amount,
            monthly_contribution=payload.monthly_contribution,
            deadline=payload.deadline,
            priority=payload.priority,
            status=initial_status,
        )
        saved_goal = await self.goal_dao.create(new_goal)
        return self._to_response_dto(saved_goal, today, buffer_warning=buffer_warning)

    async def update_goal(
        self, user_id: int, goal_id: int, payload: GoalUpdateDTO
    ) -> GoalResponseDTO:
        goal = await self._get_user_goal_or_404(goal_id, user_id)
        today = datetime.now(ROME_TZ).date()

        update_data = payload.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(goal, field, value)

        if goal.saved_amount >= goal.target_amount:
            goal.status = "COMPLETED"
        elif goal.status == "EXPIRED" and goal.deadline > today:
            goal.status = "ACTIVE"

        buffer_warning = await self._check_buffer_impact(
            user_id=user_id,
            monthly_amount=goal.monthly_contribution,
            deadline=goal.deadline,
        )

        updated = await self.goal_dao.update(goal)
        return self._to_response_dto(updated, today, buffer_warning=buffer_warning)

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
        if goal.saved_amount < goal.target_amount:
            goal.status = "ACTIVE"

        updated = await self.goal_dao.update(goal)
        return self._to_response_dto(updated, today)

    async def add_contribution(
        self, user_id: int, goal_id: int, payload: GoalContributionDTO
    ) -> GoalResponseDTO:
        """
        RF_OBI_3: Registra un accantonamento sull'obiettivo e aggiorna l'avanzamento.
        """
        goal = await self._get_user_goal_or_404(goal_id, user_id)
        today = datetime.now(ROME_TZ).date()

        updated = await self.goal_dao.add_contribution(goal, payload.amount)
        return self._to_response_dto(updated, today)

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
        self, user_id: int, monthly_amount: Decimal, deadline: date
    ) -> str | None:
        """
        RF_OBI_2: Se WhatIfSimulator (B-05) è collegato, verifica se l'accantonamento
        mensile porta il saldo previsto sotto il Safety Buffer entro la scadenza.
        """
        if not self.what_if_simulator or monthly_amount <= Decimal("0.00"):
            return None

        # -- DA SINCRONIZZARE CON WHAT-IF --
        sim_result = await self.what_if_simulator.simulate_recurring_expense(
            user_id=user_id,
            amount=monthly_amount,
            end_date=deadline,
        )
        if getattr(sim_result, "breaches_safety_buffer", False):
            return (
                "Attenzione: questo accantonamento mensile potrebbe portare il tuo saldo "
                "al di sotto del Safety Buffer prima della scadenza."
            )
        return None

    def _to_response_dto(
        self, goal: Goal, today: date, buffer_warning: str | None = None
    ) -> GoalResponseDTO:
        remaining = max(goal.target_amount - goal.saved_amount, Decimal("0.00"))

        if goal.target_amount > Decimal("0.00"):
            raw_pct = float((goal.saved_amount / goal.target_amount) * Decimal("100"))
            progress_pct = round(min(raw_pct, 100.0), 2)
        else:
            progress_pct = 100.0

        # Calcolo data stimata di raggiungimento
        estimated_date: date | None = None
        if remaining == Decimal("0.00"):
            estimated_date = today
        elif goal.monthly_contribution > Decimal("0.00"):
            months_needed = math.ceil(float(remaining / goal.monthly_contribution))
            estimated_date = today + timedelta(days=months_needed * 30)

        # Verifica scadenza superata senza completamento
        is_overdue = goal.deadline < today and remaining > Decimal("0.00")
        effective_status = "EXPIRED" if (is_overdue and goal.status == "ACTIVE") else goal.status

        return GoalResponseDTO(
            id_goal=goal.id_goal,
            name=goal.name,
            target_amount=goal.target_amount,
            saved_amount=goal.saved_amount,
            remaining_amount=remaining,
            monthly_contribution=goal.monthly_contribution,
            deadline=goal.deadline,
            priority=goal.priority,
            status=effective_status,
            progress_percentage=progress_pct,
            estimated_completion_date=estimated_date,
            is_overdue=is_overdue,
            buffer_warning=buffer_warning,
            id_recurring_rule=goal.id_recurring_rule,
            created_at=goal.created_at,
        )
