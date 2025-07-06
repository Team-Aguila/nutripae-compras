from datetime import datetime
from typing import Optional
from enum import Enum

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class MovementType(str, Enum):
    """Types of inventory movements"""
    RECEIPT = "receipt"  # Incoming stock from suppliers
    USAGE = "usage"  # Outgoing stock for consumption
    ADJUSTMENT = "adjustment"  # Manual adjustments
    TRANSFER = "transfer"  # Transfer between locations
    EXPIRED = "expired"  # Stock marked as expired
    LOSS = "loss"  # Stock loss/waste


class InventoryMovement(Document):
    """Inventory Movement DB Model - Tracks all inventory movements for audit trail"""
    
    # Core movement information
    movement_type: MovementType = Field(description="Type of inventory movement")
    product_id: PydanticObjectId = Field(description="Reference to the product")
    institution_id: int = Field(description="Reference to the institution from coverage module")
    storage_location: Optional[str] = Field(default=None, description="Specific storage location within institution")
    
    # Quantity and unit information
    quantity: float = Field(description="Quantity moved (positive for incoming, negative for outgoing)")
    unit: str = Field(default="kg", description="Unit of measurement (kg, units, liters, etc.)")
    
    # Product details at time of movement
    lot: Optional[str] = Field(default=None, description="Lot number of the product")
    expiration_date: Optional[datetime] = Field(default=None, description="Expiration date of the product")
    
    # Reference information
    reference_id: Optional[PydanticObjectId] = Field(default=None, description="Reference to related document (receipt, order, etc.)")
    reference_type: Optional[str] = Field(default=None, description="Type of reference document")
    
    # Movement details
    movement_date: datetime = Field(default_factory=datetime.utcnow, description="Date of the movement")
    notes: Optional[str] = Field(default=None, description="Additional notes about the movement")
    
    # User tracking
    created_by: str = Field(description="User who created this movement")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of document creation")
    
    # Soft delete
    deleted_at: Optional[datetime] = Field(default=None, description="For soft deletes. Null if not deleted")

    class Settings:
        name = "inventory_movements"
        indexes = [
            "movement_type",
            "product_id",
            "institution_id",
            "movement_date",
            "reference_id",
            "reference_type",
            "deleted_at"
        ]


class InventoryMovementResponse(BaseModel):
    """Response model for inventory movement"""
    id: PydanticObjectId = Field(alias="_id")
    movement_type: MovementType
    product_id: PydanticObjectId
    institution_id: int
    storage_location: Optional[str]
    quantity: float
    unit: str
    lot: Optional[str]
    expiration_date: Optional[datetime]
    reference_id: Optional[PydanticObjectId]
    reference_type: Optional[str]
    movement_date: datetime
    notes: Optional[str]
    created_by: str
    created_at: datetime

    class Config:
        populate_by_name = True 