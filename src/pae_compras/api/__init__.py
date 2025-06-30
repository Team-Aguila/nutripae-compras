# pae_compras/api/__init__.py
from fastapi import APIRouter
from . import purchase_orders

api_router = APIRouter()
api_router.include_router(purchase_orders.router) 