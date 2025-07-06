from datetime import datetime, date
from typing import Optional, List
from enum import Enum

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class Inventory(Document):
    """Inventory DB Model"""
    product_id: PydanticObjectId = Field(description="REFERENCE -> products._id")
    institution_id: int = Field(description="REFERENCE -> institutions.id from coverage module")
    remaining_weight: float = Field(gt=0, description="Remaining weight in inventory")
    unit: str = Field(default="kg", description="Unit of measurement (kg, units, liters, etc.)")
    storage_location: Optional[str] = Field(default=None, description="Specific storage location within institution")
    date_of_admission: datetime = Field(description="Date of admission to inventory")
    lot: str = Field(description="The lot number of the product")
    expiration_date: date = Field(description="The expiration date of the product")
    minimum_threshold: float = Field(default=0, description="Minimum stock threshold for this product")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of document creation")
    updated_at: Optional[datetime] = Field(default=None, description="Timestamp of the last update")
    deleted_at: Optional[datetime] = Field(default=None, description="For soft deletes. Null if not deleted")

    class Settings:
        name = "inventory"
        indexes = [
            "product_id",
            "institution_id",
            "date_of_admission",
            "expiration_date",
            "deleted_at"
        ] 


# Alias for backward compatibility
InventoryItem = Inventory


class InventoryItemResponse(BaseModel):
    """Response model for inventory consultation"""
    id: PydanticObjectId = Field(alias="_id")
    product_id: PydanticObjectId
    product_name: str
    institution_id: int
    institution_name: str
    provider_name: str
    category: str  # This will be derived from provider or product classification
    quantity: float
    base_unit: str
    storage_location: Optional[str]
    lot: str
    last_entry_date: datetime
    expiration_date: date
    minimum_threshold: float
    is_below_threshold: bool
    created_at: datetime

    class Config:
        populate_by_name = True


class InventoryConsultationQuery(BaseModel):
    """Query parameters for inventory consultation"""
    institution_id: Optional[int] = Field(default=None, description="Filter by institution/warehouse")
    product_id: Optional[PydanticObjectId] = Field(default=None, description="Filter by specific product/ingredient")
    category: Optional[str] = Field(default=None, description="Filter by product category")
    provider_id: Optional[PydanticObjectId] = Field(default=None, description="Filter by provider")
    show_expired: Optional[bool] = Field(default=True, description="Whether to include expired items")
    show_below_threshold: Optional[bool] = Field(default=None, description="Filter items below minimum threshold")
    limit: Optional[int] = Field(default=100, le=1000, description="Maximum number of items to return")
    offset: Optional[int] = Field(default=0, description="Number of items to skip")


class InventoryConsultationResponse(BaseModel):
    """Response model for inventory consultation endpoint"""
    items: List[InventoryItemResponse]
    total_count: int
    page_info: dict = Field(description="Pagination information")
    summary: dict = Field(description="Summary statistics") 