from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with MongoDB configuration"""
    
    # Server Configuration
    server_host: str = Field(default="0.0.0.0", description="Server host")
    server_port: int = Field(default=8001, description="Server port")
    
    # MongoDB Configuration
    mongo_host: str = Field(default="localhost", description="MongoDB host")
    mongo_port: int = Field(default=27017, description="MongoDB port")
    mongo_user: str = Field(default="root", description="MongoDB username")
    mongo_password: str = Field(default="example", description="MongoDB password")
    mongo_db_name: str = Field(default="pae_menus", description="MongoDB database name")
    mongo_auth_db: str = Field(default="admin", description="MongoDB authentication database")
    
    # Environment-specific settings
    environment: str = Field(default="development", description="Application environment")
    debug: bool = Field(default=True, description="Debug mode")
    
    @property
    def mongo_url(self) -> str:
        """Construct MongoDB connection URL"""
        if self.mongo_user and self.mongo_password:
            return f"mongodb://{self.mongo_user}:{self.mongo_password}@{self.mongo_host}:{self.mongo_port}/{self.mongo_db_name}?authSource={self.mongo_auth_db}"
        else:
            return f"mongodb://{self.mongo_host}:{self.mongo_port}/{self.mongo_db_name}"
    
    @property
    def mongo_url_without_db(self) -> str:
        """Construct MongoDB connection URL without database name (for initial connection)"""
        if self.mongo_user and self.mongo_password:
            return f"mongodb://{self.mongo_user}:{self.mongo_password}@{self.mongo_host}:{self.mongo_port}/?authSource={self.mongo_auth_db}"
        else:
            return f"mongodb://{self.mongo_host}:{self.mongo_port}/"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        # Allow environment variables to override settings
        env_prefix = "PAE_MENUS_"


# Global settings instance
settings = Settings()
