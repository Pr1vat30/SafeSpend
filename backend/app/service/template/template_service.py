"""Template service. Copy to `app/service/<module>/<module>_service.py` and rename.

Services hold business logic, call the DAO and raise exceptions from `app.core.exceptions`
(not `HTTPException`).
"""

from app.dao.template.template_dao import TemplateDAO


class TemplateService:
    def __init__(self, dao: TemplateDAO):
        self.dao = dao
