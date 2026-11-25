"""Aggregates every module's router under the versioned API prefix."""

from fastapi import APIRouter

from app.api.controller.health.health_controller import router as health_router
from app.api.controller.profile.router import router as profile_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(profile_router)
# api_router.include_router(<module>_router)
