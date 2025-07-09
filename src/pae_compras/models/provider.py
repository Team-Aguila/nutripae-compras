from datetime import datetime
from typing import Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field, EmailStr


class Provider(Document):
    """Provider DB Model"""
    name: Indexed(str) = Field(description="Name of the provider")
    nit: Indexed(str, unique=True) = Field(description="Provider's tax identification number")
    address: str = Field(description="Physical address of the provider")
    responsible_name: str = Field(description="Name of the primary contact person")
    email: EmailStr = Field(description="Contact email")
    phone_number: str = Field(description="Contact phone number")
    is_local_provider: bool = Field(default=True, description="Flag to indicate if the provider is local")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of document creation")
    updated_at: Optional[datetime] = Field(default=None, description="Timestamp of the last update")
    deleted_at: Optional[datetime] = Field(default=None, description="For soft deletes. Null if not deleted")

    class Settings:
        name = "providers"
        indexes = [
            "name",
            "nit",
            "is_local_provider",
            "deleted_at"
        ]


class ProviderCreate(BaseModel):
    """Model for creating a Provider"""
    name: str = Field(min_length=1, max_length=200, description="Name of the provider")
    nit: str = Field(min_length=1, max_length=50, description="Provider's tax identification number")
    address: str = Field(min_length=1, max_length=500, description="Physical address of the provider")
    responsible_name: str = Field(min_length=1, max_length=200, description="Name of the primary contact person")
    email: EmailStr = Field(description="Contact email")
    phone_number: str = Field(min_length=1, max_length=50, description="Contact phone number")
    is_local_provider: bool = Field(default=True, description="Flag to indicate if the provider is local")


class ProviderUpdate(BaseModel):
    """Model for updating a Provider - nit is immutable"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200, description="Name of the provider")
    address: Optional[str] = Field(default=None, min_length=1, max_length=500, description="Physical address of the provider")
    responsible_name: Optional[str] = Field(default=None, min_length=1, max_length=200, description="Name of the primary contact person")
    email: Optional[EmailStr] = Field(default=None, description="Contact email")
    phone_number: Optional[str] = Field(default=None, min_length=1, max_length=50, description="Contact phone number")
    is_local_provider: Optional[bool] = Field(default=None, description="Flag to indicate if the provider is local")


class ProviderResponse(BaseModel):
    """Response model for Provider"""
    id: PydanticObjectId = Field(alias="_id")
    name: str
    nit: str
    address: str
    responsible_name: str
    email: EmailStr
    phone_number: str
    is_local_provider: bool
    created_at: datetime
    updated_at: Optional[datetime]
    deleted_at: Optional[datetime]

    class Config:
        populate_by_name = True


class ProviderListResponse(BaseModel):
    """Response model for provider list with pagination"""
    providers: list[ProviderResponse]
    total_count: int
    page_info: dict = Field(description="Pagination information")

    class Config:
        populate_by_name = True 