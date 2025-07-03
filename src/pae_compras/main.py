# pae_core/main.py
import logging
from fastapi import FastAPI
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie

from .core.config import settings
from .api import api_router
from .models import (
    PurchaseOrder,
    Provider,
    Product,
    InventoryItem,
    IngredientReceipt,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

document_models = []

def register_models(models: list):
    """Register models for Beanie initialization."""
    document_models.extend(models)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handle startup and shutdown events.
    """
    logger.info("Starting up...")
    app.mongodb_client = AsyncIOMotorClient(settings.mongo_url)
    app.mongodb = app.mongodb_client[settings.mongo_db_name]

    await init_beanie(
        database=app.mongodb,
        document_models=document_models
    )
    logger.info("Database and Beanie initialized.")
    
    yield
    
    logger.info("Shutting down...")
    app.mongodb_client.close()
    logger.info("MongoDB connection closed.")


app = FastAPI(
    title="PAE Compras API",
    description="API for managing purchase orders in the PAE system.",
    version="1.0.0",
    lifespan=lifespan
)

# Register purchase-specific models
register_models([PurchaseOrder, Provider, Product, InventoryItem, IngredientReceipt])

# Include purchase-specific routes
app.include_router(api_router, prefix="/api/v1/compras", tags=["Compras"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the PAE Compras API"}

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "PAE Compras API"}

@app.get("/health/database")
async def database_health_check():
    """Check database connection health"""
    try:
        # Simple database connection test
        await app.mongodb.list_collection_names()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "database": "disconnected", "error": str(e)}
