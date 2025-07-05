from datetime import datetime
from typing import Optional

from beanie import Document, Indexed
from pydantic import Field, EmailStr


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