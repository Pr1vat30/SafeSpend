from decimal import Decimal
from zoneinfo import ZoneInfo
from datetime import date, datetime, timedelta
from app.api.dto.achievements.achievements_dto import AchievementStatusDTO

# -- DA AGGIUNGERE QUANDO I DAO SARANNO REALIZZATI --
#from app.dao.achievement_dao import AchievementDAO
#from app.dao.profile_dao import ProfileDAO
#from app.dao.snapshot_dao import BalanceSnapshotDAO
#from app.service.cashflow_engine import CashFlowEngine
# ---------------------------------------------------

ROME_TZ = ZoneInfo("Europe/Rome")

class AchievementService:
    """
    SS4 - Gestione Achievements (RF_PRE_6).
    Gestisce:
    1. Consultazione catalogo + avanzamento per la UI (get_user_achievements).
    2. Verifica deterministica giornaliera delle regole fisse per lo Scheduler (check_and_unlock_for_user):
       - 'Buffer intatto': saldo reale mai sotto il Safety Buffer negli ultimi 30 giorni.
       - 'Saldo allineato': almeno una riconciliazione a settimana per 4 settimane consecutive.
    """

    def __init__(self, achievement_dao, snapshot_dao, profile_dao, cashflow_engine):
        self.achievement_dao = achievement_dao
        self.snapshot_dao = snapshot_dao
        self.profile_dao = profile_dao
        self.cashflow_engine = cashflow_engine

    async def get_user_achievements(self, user_id: int) -> list[AchievementStatusDTO]:
        """
        Restituisce tutti gli achievement del catalogo con lo stato di sblocco
        e l'avanzamento corrente per l'utente (SS4 - getAchievements).
        """
        today = datetime.now(ROME_TZ).date()
        catalog = await self.achievement_dao.get_all_definitions()
        # Mappa {id_achievement: unlocked_at} per gli achievement già sbloccati dall'utente
        unlocked_map: dict[int, datetime] = await self.achievement_dao.get_unlocked_map(user_id)

        results: list[AchievementStatusDTO] = []

        for ach in catalog:
            rule_type = ach.criterion.get("type")
            target = int(ach.criterion.get("target", 1))
            unlocked_at = unlocked_map.get(ach.id_achievement)
            is_unlocked = unlocked_at is not None

            if is_unlocked:
                current = target
            else:
                current = await self._compute_current_progress(user_id, rule_type, target, today)

            results.append(
                AchievementStatusDTO(
                    id_achievement=ach.id_achievement,
                    name=ach.name,
                    description=ach.description,
                    badge_path=ach.badge_path,
                    unlocked=is_unlocked,
                    unlocked_at=unlocked_at,
                    progress_current=min(current, target),
                    progress_target=target,
                )
            )

        return results

    async def check_and_unlock_for_user(
            self, user_id: int, reference_date: date | None = None
    ) -> list[int]:
        """
        Invocato dallo Scheduler giornaliero (RF_PRE_6, RNF_AF_6).
        Verifica le regole fisse e sblocca in modo idempotente i traguardi raggiunti.
        """
        today = reference_date or datetime.now(ROME_TZ).date()
        catalog = await self.achievement_dao.get_all_definitions()
        unlocked_map = await self.achievement_dao.get_unlocked_map(user_id)

        newly_unlocked: list[int] = []

        for ach in catalog:
            if ach.id_achievement in unlocked_map:
                continue

            rule_type = ach.criterion.get("type")
            target = int(ach.criterion.get("target", 1))
            current = await self._compute_current_progress(user_id, rule_type, target, today)

            if current >= target:
                # INSERT ... ON CONFLICT (id_user, id_achievement) DO NOTHING (RNF_AF_6)
                inserted = await self.achievement_dao.unlock_if_not_exists(
                    user_id=user_id,
                    achievement_id=ach.id_achievement,
                    unlocked_at=datetime.now(ROME_TZ),
                )
                if inserted:
                    newly_unlocked.append(ach.id_achievement)

        return newly_unlocked

    async def _compute_current_progress(
            self, user_id: int, rule_type: str | None, target: int, today: date
    ) -> int:
        if rule_type == "buffer_intact_30d":
            return await self._count_consecutive_days_above_buffer(user_id, today, max_days=target)
        if rule_type == "reconciled_4_weeks":
            return await self._count_consecutive_reconciled_weeks(user_id, today, max_weeks=target)
        return 0

    # -- DA SINCRONIZZARE METODI DAO --
    async def _count_consecutive_days_above_buffer(
            self, user_id: int, today: date, max_days: int = 30
    ) -> int:
        """
        Regola 1 (RF_PRE_6): 'Buffer intatto'
        Conta quanti giorni consecutivi fino a oggi il saldo reale/storico
        non è mai sceso sotto il Safety Buffer.
        """
        profile = await self.profile_dao.get_by_user_id(user_id)
        if not profile or profile.safety_buffer <= Decimal("0.00"):
            return 0

        start_date = today - timedelta(days=max_days - 1)

        daily_history: dict[date, Decimal] = await self.cashflow_engine.get_historical_daily_balances(
            user_id=user_id, start_date=start_date, end_date=today
        )

        streak = 0
        for offset in range(max_days):
            day = today - timedelta(days=offset)
            bal = daily_history.get(day)
            if bal is None or bal < profile.safety_buffer:
                break
            streak += 1

        return streak

    # -- DA SINCRONIZZARE METODI DAO --
    async def _count_consecutive_reconciled_weeks(
            self, user_id: int, today: date, max_weeks: int = 4
    ) -> int:
        """
        Regola 2 (RF_PRE_6): 'Saldo allineato'
        Conta quante settimane consecutive (a ritroso da oggi) contengono
        almeno una riconciliazione nella tabella balance_snapshot.
        """
        snapshots = await self.snapshot_dao.find_between_dates(
            user_id=user_id,
            start_date=today - timedelta(days=max_weeks * 7),
            end_date=today,
        )
        reconciliation_dates = {s.reconciliation_date for s in snapshots}

        consecutive_weeks = 0
        for w in range(max_weeks):
            window_end = today - timedelta(days=w * 7)
            window_start = window_end - timedelta(days=6)
            has_recon = any(window_start <= d <= window_end for d in reconciliation_dates)
            if not has_recon:
                break
            consecutive_weeks += 1

        return consecutive_weeks