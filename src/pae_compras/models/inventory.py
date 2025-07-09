from datetime import datetime, date
from typing import Optional, List
from enum import Enum

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, ConfigDict


class Inventory(Document):
    """Inventory DB Model - Represents individual batches of products"""
    product_id: PydanticObjectId = Field(description="REFERENCE -> products._id")
    institution_id: int = Field(description="REFERENCE -> institutions.id from coverage module")
    remaining_weight: float = Field(ge=0.0, description="Remaining weight in inventory (>= 0 to allow complete consumption)")
    unit: str = Field(default="kg", description="Unit of measurement (kg, units, liters, etc.)")
    storage_location: Optional[str] = Field(default=None, description="Specific storage location within institution")
    date_of_admission: datetime = Field(description="Date of admission to inventory")
    lot: str = Field(description="The lot number of the product")
    expiration_date: date = Field(description="The expiration date of the product")
    minimum_threshold: float = Field(default=0, description="Minimum stock threshold for this product")
    batch_number: str = Field(description="Unique batch identifier for FIFO tracking")
    initial_weight: float = Field(gt=0, description="Initial weight when batch was received")
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
            "storage_location",
            "batch_number",
            "deleted_at"
        ]


# Alias for backward compatibility
InventoryItem = Inventory


class InventoryReceiptRequest(BaseModel):
    """Request model for receiving inventory (User Story 1)"""
    product_id: str = Field(description="String representation of product ID")
    institution_id: int = Field(description="ID of the institution/warehouse")
    storage_location: str = Field(description="Specific storage location within institution")
    quantity_received: float = Field(gt=0, description="Quantity received")
    unit_of_measure: str = Field(default="kg", description="Unit of measurement")
    expiration_date: date = Field(description="Expiration date of the received batch")
    batch_number: str = Field(description="Unique batch number for tracking")
    purchase_order_id: Optional[str] = Field(default=None, description="Optional purchase order reference")
    received_by: str = Field(description="Person who received the inventory")
    reception_date: Optional[datetime] = Field(default=None, description="Date of reception")
    notes: Optional[str] = Field(default=None, description="Additional notes")


class InventoryReceiptResponse(BaseModel):
    """Response model for inventory receipt operations"""
    transaction_id: str = Field(description="Unique identifier for this receipt transaction")
    inventory_id: str = Field(description="String representation of created inventory batch ID")
    product_id: str = Field(description="String representation of product ID")
    institution_id: int = Field(description="ID of the institution/warehouse") 
    storage_location: str = Field(description="Storage location where inventory was placed")
    quantity_received: float = Field(description="Quantity received")
    unit_of_measure: str = Field(description="Unit of measurement")
    expiration_date: date = Field(description="Expiration date of the batch")
    batch_number: str = Field(description="Unique batch number")
    purchase_order_id: Optional[str] = Field(description="Purchase order reference if applicable")
    received_by: str = Field(description="Person who received the inventory")
    reception_date: datetime = Field(description="Date of reception")
    movement_id: str = Field(description="String representation of created inventory movement record ID")
    notes: Optional[str] = Field(description="Additional notes")
    created_at: datetime = Field(description="Timestamp when receipt was recorded")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            PydanticObjectId: str
        }
    )


class InventoryItemResponse(BaseModel):
    """Response model for inventory consultation"""
    id: str = Field(alias="_id", description="String representation of inventory ID")
    product_id: str = Field(description="String representation of product ID")
    product_name: str
    institution_id: int
    institution_name: str
    provider_name: str
    category: str  # This will be derived from provider or product classification
    quantity: float
    base_unit: str
    storage_location: Optional[str]
    lot: str
    batch_number: str
    last_entry_date: datetime
    expiration_date: date
    minimum_threshold: float
    is_below_threshold: bool
    initial_weight: float
    created_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            PydanticObjectId: str
        }
    )


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