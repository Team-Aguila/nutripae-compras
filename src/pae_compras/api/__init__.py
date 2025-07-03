# pae_compras/api/__init__.py
from fastapi import APIRouter
from . import purchase_orders
from . import ingredient_receipts

api_router = APIRouter()
api_router.include_router(purchase_orders.router, prefix="/purchase-orders", tags=["Purchase Orders"])
api_router.include_router(ingredient_receipts.router, prefix="/ingredient-receipts", tags=["Ingredient Receipts"]) 