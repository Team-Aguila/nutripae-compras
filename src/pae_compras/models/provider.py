from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field, EmailStr


class Provider(Document):
    """Provider DB Model"""
    name: Indexed(str) = Field(description="Name of the provider")
    nit: Indexed(str, unique=True) = Field(description="NIT of the provider")
    address: str = Field(description="Address of the provider")
    responsible_name: str = Field(description="Name of the responsible person")
    email: EmailStr = Field(description="Email of the provider")
    phone_number: str = Field(description="Phone number of the provider")
    is_local_provider: bool = Field(default=True, description="Indicates if the provider is local")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    deleted_at: Optional[datetime] = Field(default=None)

    class Settings:
        name = "providers" 