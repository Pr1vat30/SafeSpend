"""Database unit of work of the Scheduler (it runs outside HTTP requests)."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.config.database import AsyncSessionLocal
from app.dao.scheduler.scheduler_dao import SchedulerDAO


@asynccontextmanager
async def database_unit_of_work() -> AsyncIterator[SchedulerDAO]:
    """Open a session, commit on success, roll back on error (RNF_AF_2)."""
    async with AsyncSessionLocal() as session:
        try:
            yield SchedulerDAO(session)
            await session.commit()
        except Exception:
            await session.rollback()
            raise
