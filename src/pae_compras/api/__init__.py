# pae_compras/api/__init__.py
from fastapi import APIRouter
from . import purchase_orders
from . import ingredient_receipts
from . import inventory
from . import inventory_movements
from . import products

api_router = APIRouter()
api_router.include_router(purchase_orders.router, prefix="/purchase-orders", tags=["Purchase Orders"])
api_router.include_router(ingredient_receipts.router, prefix="/ingredient-receipts", tags=["Ingredient Receipts"]) 
api_router.include_router(inventory.router, prefix="/inventory", tags=["Inventory"]) 
api_router.include_router(inventory_movements.router, prefix="/inventory-movements", tags=["Inventory Movements"])
api_router.include_router(products.router, prefix="/products", tags=["Products"]) 