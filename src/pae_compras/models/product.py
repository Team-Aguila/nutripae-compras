from datetime import datetime
from typing import Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field
from enum import Enum


class WeeklyAvailability(str, Enum):
    """Weekly Availability Enum"""
    MONDAY = "MONDAY"
    TUESDAY = "TUESDAY"
    WEDNESDAY = "WEDNESDAY"
    THURSDAY = "THURSDAY"
    FRIDAY = "FRIDAY"
    SATURDAY = "SATURDAY"
    SUNDAY = "SUNDAY"


class LifeTime(BaseModel):
    """Life time object structure"""
    value: int = Field(gt=0, description="Life time value")
    unit: str = Field(description="Life time unit (e.g., 'days', 'weeks', 'months')")


class Product(Document):
    """Product DB Model"""
    provider_id: PydanticObjectId = Field(description="REFERENCE -> providers._id")
    name: str = Field(description="Name of the product")
    weight: float = Field(gt=0, description="Default or standard weight (e.g., in kg)")
    weekly_availability: WeeklyAvailability = Field(description="Weekly availability of the product")
    life_time: LifeTime = Field(description="Life time of the product with value and unit")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of document creation")
    updated_at: Optional[datetime] = Field(default=None, description="Timestamp of the last update")
    deleted_at: Optional[datetime] = Field(default=None, description="For soft deletes. Null if not deleted")

    class Settings:
        name = "products"
        indexes = [
            "provider_id",
            "name",
            "weekly_availability",
            "deleted_at"
        ] 