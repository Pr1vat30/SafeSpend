"""Template controller. Copy to `app/api/controller/<module>/<module>_controller.py` and rename.

Controllers declare routes, validate input via DTOs and delegate to the service.
Register the router in `app/api/router.py`. Return `APIResponse.ok(...)` from each route.
"""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.core.dependencies import DbSession
from app.dao.template.template_dao import TemplateDAO
from app.service.template.template_service import TemplateService

router = APIRouter(prefix="/template", tags=["Template"])


def get_template_service(db: DbSession) -> TemplateService:
    return TemplateService(TemplateDAO(db))


Service = Annotated[TemplateService, Depends(get_template_service)]
