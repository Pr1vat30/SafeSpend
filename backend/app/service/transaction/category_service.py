"""Category business logic: default/custom categories and safe deletion."""

from app.core.exceptions import AppException, ConflictError, NotFoundError
from app.dao.transaction.category_dao import CategoryDAO
from app.models.transaction.category_model import Category
from app.service.transaction import messages
from app.service.transaction.exceptions import ForbiddenError

FALLBACK_NAME = "Altro"
TRANSACTION_TYPES = ("income", "expense")


class CategoryService:
    def __init__(self, dao: CategoryDAO):
        self.dao = dao

    async def list_categories(self, user_id: int) -> list[Category]:
        return await self.dao.list_visible(user_id)

    async def create_category(self, user_id: int, name: str, category_type: str) -> Category:
        await self._ensure_name_available(user_id, name, category_type)
        return await self.dao.create(user_id, name, category_type)

    async def rename_category(self, user_id: int, category_id: int, name: str) -> Category:
        category = await self._get_custom(user_id, category_id)
        await self._ensure_name_available(user_id, name, category.type, exclude_id=category_id)
        return await self.dao.rename(category, name)

    async def delete_category(self, user_id: int, category_id: int) -> int:
        """Delete a custom category. Its transactions move to the default «Altro» of their type.

        Returns the number of reassigned transactions.
        """
        category = await self._get_custom(user_id, category_id)
        rules, planned = await self.dao.count_references(category_id)
        if rules or planned:
            # Data of other modules is never altered: the category simply stays in place.
            raise ConflictError(messages.category_in_use(category.name, rules, planned))

        fallbacks = {}
        for transaction_type in TRANSACTION_TYPES:
            fallback = await self.dao.get_default(FALLBACK_NAME, transaction_type)
            if fallback is None:
                raise AppException(messages.CATEGORY_FALLBACK_MISSING)
            fallbacks[transaction_type] = fallback

        reassigned = 0
        for transaction_type, fallback in fallbacks.items():
            reassigned += await self.dao.reassign_transactions(
                user_id, category_id, transaction_type, fallback.id_category
            )
        await self.dao.delete(category)
        return reassigned

    async def _get_custom(self, user_id: int, category_id: int) -> Category:
        category = await self.dao.get_visible(user_id, category_id)
        if category is None:
            raise NotFoundError(messages.CATEGORY_NOT_FOUND)
        if category.is_default:
            raise ForbiddenError(messages.CATEGORY_DEFAULT_PROTECTED)
        return category

    async def _ensure_name_available(
        self, user_id: int, name: str, category_type: str, exclude_id: int | None = None
    ) -> None:
        """A name clashes with a visible category of the same type (or of type `both`)."""
        for existing in await self.dao.find_by_name(user_id, name):
            if existing.id_category == exclude_id:
                continue
            if "both" in (existing.type, category_type) or existing.type == category_type:
                raise ConflictError(messages.CATEGORY_DUPLICATE)
