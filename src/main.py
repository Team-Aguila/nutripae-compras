import logging
import uvicorn

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from fastapi.openapi.utils import get_openapi
from utils.telemetrics import PrometheusMiddleware, metrics, setting_otlp
from core.config import settings
from api import api_router
from models import (
    PurchaseOrder,
    Provider,
    Product,
    Inventory,
    IngredientReceipt,
    InventoryMovement,
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
    app.mongodb_client = AsyncIOMotorClient(settings.MONGO_URL)
    app.mongodb = app.mongodb_client[settings.DB_NAME]

    await init_beanie(
        database=app.mongodb,
        document_models=document_models
    )
    logger.info("Database and Beanie initialized.")
    
    yield
    
    logger.info("Shutting down...")
    app.mongodb_client.close()
    logger.info("MongoDB connection closed.")


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="API de Compras PAE",
        version="1.0.0",
        description="Backend para la gestión de compras en el sistema PAE.",
        routes=app.routes,
    )
    
    # Define the security scheme for JWT Bearer tokens
    openapi_schema["components"]["securitySchemes"] = {
        "HTTPBearer": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Enter your JWT token obtained from the NutriPAE-AUTH service /auth/login endpoint"
        }
    }
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

app = FastAPI(
    title="PAE Compras API",
    description="API for managing purchase orders in the PAE system.",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(PrometheusMiddleware, app_name=settings.APP_NAME)
app.add_route("/metrics", metrics)
# Setting OpenTelemetry exporter
setting_otlp(app, settings.APP_NAME, settings.OTLP_GRPC_ENDPOINT)

class EndpointFilter(logging.Filter):
    # Uvicorn endpoint access log filter
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("GET /metrics") == -1


# Filter out /endpoint
logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
# Set custom OpenAPI schema
app.openapi = custom_openapi

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permite todas las origenes
    allow_credentials=True,
    allow_methods=["*"],  # Permite todos los métodos
    allow_headers=["*"],  # Permite todos los headers
)

# Register purchase-specific models
register_models([PurchaseOrder, Provider, Product, Inventory, IngredientReceipt, InventoryMovement])

# Include purchase-specific routes
app.include_router(api_router, prefix=settings.API_PREFIX_STR, tags=["Compras"])

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

if __name__ == "__main__":
    import os
    
    # Crear el directorio de logs si no existe
    log_dir = "/var/log/containers"
    os.makedirs(log_dir, exist_ok=True)
    
    # Configurar logging básico para la aplicación
    import logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] - %(message)s",
        handlers=[
            logging.StreamHandler(),  # Para mostrar en consola
            logging.FileHandler("/var/log/containers/nutripae-auth.log", mode="a")
        ]
    )
    
    # update uvicorn access logger format
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"][
        "fmt"
    ] = "%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] [trace_id=%(otelTraceID)s span_id=%(otelSpanID)s resource.service.name=%(otelServiceName)s] - %(message)s"
    
    # Configurar handler para archivo de logs
    log_config["handlers"]["file"] = {
        "class": "logging.FileHandler",
        "filename": "/var/log/containers/nutripae-auth.log",
        "formatter": "access",
        "mode": "a"
    }
    
    # Asegurar que los handlers existan antes de modificar
    for logger_name in ["uvicorn.access", "uvicorn"]:
        if logger_name in log_config["loggers"]:
            if "handlers" not in log_config["loggers"][logger_name]:
                log_config["loggers"][logger_name]["handlers"] = ["default"]
            if "file" not in log_config["loggers"][logger_name]["handlers"]:
                log_config["loggers"][logger_name]["handlers"].append("file")
    
    # Configurar el logger raíz para también escribir al archivo
    if "root" not in log_config["loggers"]:
        log_config["loggers"]["root"] = {
            "level": "INFO",
            "handlers": ["default", "file"]
        }
    else:
        if "handlers" not in log_config["loggers"]["root"]:
            log_config["loggers"]["root"]["handlers"] = ["default"]
        if "file" not in log_config["loggers"]["root"]["handlers"]:
            log_config["loggers"]["root"]["handlers"].append("file")
    
    # Log de inicio
    logger = logging.getLogger(__name__)
    logger.info("Iniciando NutriPAE-AUTH con configuración de logging mejorada...")
    
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)