from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator


class Settings(BaseSettings):
    """Application settings with MongoDB configuration"""
     
    # MongoDB Configuration
    DB_HOST: str = Field(default="localhost", description="MongoDB host")
    DB_PORT: int = Field(default=27018, description="MongoDB port")
    DB_USER: str = Field(default="root", description="MongoDB username")
    DB_PASSWORD: str = Field(default="example", description="MongoDB password")
    DB_NAME: str = Field(default="pae_compras", description="MongoDB database name")
    DB_AUTH_NAME: str = Field(default="admin", description="MongoDB authentication database")

    MONGO_URL: str | None = None
    MONGO_URL_WITHOUT_DB: str | None = None
    
    @field_validator("MONGO_URL", mode='before')
    @classmethod
    def assemble_mongo_url(cls, v: str | None, values) -> any:
        if isinstance(v, str):
            return v
        
        data = values.data
        return f"mongodb://{data.get('DB_USER')}:{data.get('DB_PASSWORD')}@{data.get('DB_HOST')}:{data.get('DB_PORT')}/{data.get('DB_NAME')}?authSource={data.get('DB_AUTH_NAME')}"
    
    @field_validator("MONGO_URL_WITHOUT_DB", mode='before')
    @classmethod
    def assemble_mongo_url_without_db(cls, v: str | None, values) -> any:
        if isinstance(v, str):
            return v
        
        data = values.data
        return f"mongodb://{data.get('DB_USER')}:{data.get('DB_PASSWORD')}@{data.get('DB_HOST')}:{data.get('DB_PORT')}/?authSource={data.get('DB_AUTH_NAME')}"
    
    # Environment-specific settings
    ENV_STATE: str
    APP_NAME: str
    API_PREFIX_STR: str
    MODULE_IDENTIFIER: str

    # External Services Configuration
    NUTRIPAE_AUTH_HOST: str
    NUTRIPAE_AUTH_PORT: int
    NUTRIPAE_AUTH_PREFIX_STR: str = "/api/v1"
    NUTRIPAE_AUTH_URL: str | None = None

    @field_validator("NUTRIPAE_AUTH_URL", mode='before')
    @classmethod
    def assemble_nutripae_auth_url(cls, v: str | None, values) -> any:
        if isinstance(v, str):
            return v
        
        data = values.data
        return f"http://{data.get('NUTRIPAE_AUTH_HOST')}:{data.get('NUTRIPAE_AUTH_PORT')}{data.get('NUTRIPAE_AUTH_PREFIX_STR')}"
    
    NUTRIPAE_COVERAGE_HOST: str
    NUTRIPAE_COVERAGE_PORT: int
    NUTRIPAE_COVERAGE_PREFIX_STR: str = "/api/v1"
    NUTRIPAE_COVERAGE_URL: str | None = None

    @field_validator("NUTRIPAE_COVERAGE_URL", mode='before')
    @classmethod
    def assemble_nutripae_coverage_url(cls, v: str | None, values) -> any:
        if isinstance(v, str):
            return v
        
        data = values.data
        return f"http://{data.get('NUTRIPAE_COVERAGE_HOST')}:{data.get('NUTRIPAE_COVERAGE_PORT')}{data.get('NUTRIPAE_COVERAGE_PREFIX_STR')}"
    
    NUTRIPAE_MENU_HOST: str
    NUTRIPAE_MENU_PORT: int
    NUTRIPAE_MENU_PREFIX_STR: str = "/api/v1"
    NUTRIPAE_MENU_URL: str | None = None

    @field_validator("NUTRIPAE_MENU_URL", mode='before')
    @classmethod
    def assemble_nutripae_menu_url(cls, v: str | None, values) -> any:
        if isinstance(v, str):
            return v
        
        data = values.data
        return f"http://{data.get('NUTRIPAE_MENU_HOST')}:{data.get('NUTRIPAE_MENU_PORT')}{data.get('NUTRIPAE_MENU_PREFIX_STR')}"

    OTLP_GRPC_ENDPOINT: str

    
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="ignore"
    )


# Global settings instance
settings = Settings()
