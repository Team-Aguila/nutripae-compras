from datetime import datetime
from typing import Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field, validator
from enum import Enum


class WeeklyAvailability(str, Enum):
    """Weekly Availability Enum"""
    MONDAY = "Lunes"
    TUESDAY = "Martes"
    WEDNESDAY = "Miércoles"
    THURSDAY = "Jueves"
    FRIDAY = "Viernes"
    SATURDAY = "Sábado"
    SUNDAY = "Domingo"


class Product(Document):
    """Product DB Model"""
    name: Indexed(str) = Field(description="Name of the product")
    weight: float = Field(gt=0, description="Weight of the product")
    weekly_availability: WeeklyAvailability = Field(description="Weekly availability of the product")
    provider_id: PydanticObjectId = Field(description="The ID of the provider")
    life_time_interval: int = Field(gt=0, description="Life time of the product in days")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    deleted_at: Optional[datetime] = Field(default=None)

    class Settings:
        name = "products" 