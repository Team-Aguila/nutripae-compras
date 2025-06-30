import logging
from typing import List
from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from pymongo.errors import ServerSelectionTimeoutError, ConfigurationError

from pae_menus.core.config import settings
from pae_menus.models import Ingredient, Dish, MenuCycle, MenuSchedule

# Setup logging
logger = logging.getLogger(__name__)

# Global MongoDB client instance
motor_client: AsyncIOMotorClient = None


async def init_db() -> None:
    """
    Initialize the MongoDB database and Beanie ODM.
    
    This function:
    1. Creates a connection to MongoDB using Motor
    2. Initializes Beanie with all document models
    3. Sets up database indexes
    
    Raises:
        Exception: If database connection or initialization fails
    """
    global motor_client
    
    try:
        logger.info(f"Connecting to MongoDB at {settings.mongo_host}:{settings.mongo_port}")
        
        # Create Motor client with connection settings
        motor_client = AsyncIOMotorClient(
            settings.mongo_url_without_db,
            serverSelectionTimeoutMS=5000,  # 5 second timeout
            connectTimeoutMS=5000,
            maxPoolSize=50,
            minPoolSize=10,
            maxIdleTimeMS=30000,
        )
        
        # Test the connection
        await motor_client.admin.command('ping')
        logger.info("Successfully connected to MongoDB")
        
        # Get the database
        database = motor_client[settings.mongo_db_name]
        
        # Initialize Beanie with all document models
        document_models = [
            Ingredient,
            Dish,
            MenuCycle,
            MenuSchedule,
        ]
        
        await init_beanie(
            database=database,
            document_models=document_models
        )
        
        logger.info(f"Successfully initialized Beanie ODM with database '{settings.mongo_db_name}'")
        logger.info(f"Registered document models: {[model.__name__ for model in document_models]}")
        
    except ServerSelectionTimeoutError as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        raise Exception(f"Could not connect to MongoDB at {settings.mongo_host}:{settings.mongo_port}. Make sure MongoDB is running.")
    
    except ConfigurationError as e:
        logger.error(f"MongoDB configuration error: {e}")
        raise Exception(f"MongoDB configuration error: {e}")
    
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise Exception(f"Database initialization failed: {e}")


async def close_db_connection() -> None:
    """
    Close the MongoDB connection gracefully.
    
    This function should be called during application shutdown
    to ensure proper cleanup of database connections.
    """
    global motor_client
    
    if motor_client:
        try:
            logger.info("Closing MongoDB connection...")
            motor_client.close()
            logger.info("MongoDB connection closed successfully")
        except Exception as e:
            logger.error(f"Error closing MongoDB connection: {e}")
    else:
        logger.warning("No MongoDB connection to close")


async def get_database():
    """
    Get the current database instance.
    
    Returns:
        AsyncIOMotorDatabase: The current database instance
        
    Raises:
        Exception: If no database connection exists
    """
    global motor_client
    
    if not motor_client:
        raise Exception("Database not initialized. Call init_db() first.")
    
    return motor_client[settings.mongo_db_name]


async def health_check() -> dict:
    """
    Perform a health check on the database connection.
    
    Returns:
        dict: Health status message
    """
    try:
        if not motor_client:
            logger.warning("Database health check failed: No database connection")
            return {"status": "unhealthy", "message": "Database connection not established"}
        
        # Try to ping the database
        await motor_client.admin.command('ping')
        
        # Get database stats for logging
        db = motor_client[settings.mongo_db_name]
        stats = await db.command('dbStats')
        
        # Log detailed database information
        logger.info(f"Database health check successful - "
                   f"Database: {settings.mongo_db_name}, "
                   f"Host: {settings.mongo_host}:{settings.mongo_port}, "
                   f"Collections: {stats.get('collections', 0)}, "
                   f"Data size: {stats.get('dataSize', 0)} bytes")
        
        return {
            "status": "healthy",
            "message": "Database connection established successfully"
        }
        
    except Exception as e:
        logger.error(f"Database health check failed: {str(e)}")
        return {
            "status": "unhealthy", 
            "message": "Database connection failed"
        }
