"""Liveness and readiness probes."""

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.dto import APIResponse
from app.constants.messages import HEALTH_PREFIX, HEALTH_TAG
from app.core.dependencies import DbSession

router = APIRouter(prefix=HEALTH_PREFIX, tags=[HEALTH_TAG])


@router.get("", response_model=APIResponse[dict])
async def liveness():
    """The process is up. Does not touch the database."""
    return APIResponse.ok({"status": "ok"})


@router.get("/db", response_model=APIResponse[dict])
async def readiness(db: DbSession):
    """The database is reachable."""
    try:
        await db.execute(text("SELECT 1"))
    except Exception:
        body = APIResponse.fail("Database unavailable").model_dump()
        return JSONResponse(status_code=503, content=body)
    return APIResponse.ok({"status": "ok", "database": "ok"})
