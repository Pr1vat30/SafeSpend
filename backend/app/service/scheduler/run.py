"""Entry point of the Scheduler.

    uv run python -m app.service.scheduler.run          # one pass, then exit
    uv run python -m app.service.scheduler.run --loop   # one pass now, then every day at 00:05

The first pass at every start recovers the runs missed while the server was stopped (RNF_AF_6).
"""

import argparse
import asyncio
import logging
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from app.config.logging import get_logger
from app.service.scheduler.scheduler_service import run_daily

logger = get_logger(__name__)

ROME = ZoneInfo("Europe/Rome")
RUN_AT = time(0, 5)


def seconds_until_next_run(now: datetime, run_at: time = RUN_AT) -> float:
    """Seconds from `now` to the next time of day `run_at` (today if still ahead, else tomorrow)."""
    target = datetime.combine(now.date(), run_at, tzinfo=now.tzinfo)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


async def _run(loop_forever: bool) -> None:
    from app.service.scheduler.unit_of_work import database_unit_of_work

    await run_daily(database_unit_of_work)
    while loop_forever:
        await asyncio.sleep(seconds_until_next_run(datetime.now(ROME)))
        try:
            await run_daily(database_unit_of_work)
        except Exception:
            logger.exception("Scheduler: ciclo fallito, riprovo il giorno dopo")


def main() -> None:
    parser = argparse.ArgumentParser(description="SafeSpend daily Scheduler")
    parser.add_argument("--loop", action="store_true", help="keep running, once a day")
    args = parser.parse_args()
    if not logging.getLogger().handlers:
        logging.basicConfig(level=logging.INFO)
    asyncio.run(_run(args.loop))


if __name__ == "__main__":
    main()
