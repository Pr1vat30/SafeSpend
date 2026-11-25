"""Single router of the transaction module (transactions, categories and reconciliations)."""

from fastapi import APIRouter

from app.api.controller.transaction.category_controller import router as category_router
from app.api.controller.transaction.reconciliation_controller import router as reconciliation_router
from app.api.controller.transaction.transaction_controller import router as transaction_router

router = APIRouter()
router.include_router(category_router)
router.include_router(reconciliation_router)
router.include_router(transaction_router)
