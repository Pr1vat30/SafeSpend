"""All routes of SS1 (profile module): /auth and /profile."""

from fastapi import APIRouter

from app.api.controller.profile.auth_controller import router as auth_router
from app.api.controller.profile.profile_controller import router as profile_router

router = APIRouter()
router.include_router(auth_router)
router.include_router(profile_router)
