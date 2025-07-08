from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with MongoDB configuration"""
    
    # Server Configuration
    server_host: str = Field(default="0.0.0.0", description="Server host")
    server_port: int = Field(default=8002, description="Server port")
    
    # MongoDB Configuration
    mongo_host: str = Field(default="localhost", description="MongoDB host")
    mongo_port: int = Field(default=27018, description="MongoDB port")
    mongo_user: str = Field(default="root", description="MongoDB username")
    mongo_password: str = Field(default="example", description="MongoDB password")
    mongo_db_name: str = Field(default="pae_compras", description="MongoDB database name")
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
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        env_prefix="PAE_COMPRAS_",
        extra="ignore"
    )


# Global settings instance
settings = Settings()
