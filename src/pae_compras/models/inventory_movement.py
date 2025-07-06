from datetime import datetime
from typing import Optional, List
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


class InventoryConsumptionRequest(BaseModel):
    """Request model for inventory consumption with FIFO logic"""
    product_id: PydanticObjectId = Field(description="ID of the product to consume")
    institution_id: int = Field(description="ID of the institution/warehouse")
    storage_location: Optional[str] = Field(default=None, description="Specific storage location")
    quantity: float = Field(gt=0, description="Quantity to consume (must be positive)")
    unit: str = Field(default="kg", description="Unit of measurement")
    consumption_date: Optional[datetime] = Field(default=None, description="Date of consumption (defaults to now)")
    reason: str = Field(description="Reason for consumption (e.g., 'menu preparation', 'manual adjustment')")
    notes: Optional[str] = Field(default=None, description="Additional notes about the consumption")
    consumed_by: str = Field(description="Person or system that performed the consumption")


class BatchConsumptionDetail(BaseModel):
    """Details of consumption from a specific batch"""
    inventory_id: PydanticObjectId = Field(description="ID of the inventory batch")
    lot: str = Field(description="Lot number of the batch")
    consumed_quantity: float = Field(description="Quantity consumed from this batch")
    remaining_quantity: float = Field(description="Remaining quantity in this batch after consumption")
    expiration_date: datetime = Field(description="Expiration date of the batch")
    date_of_admission: datetime = Field(description="Date when batch was admitted to inventory")


class InventoryConsumptionResponse(BaseModel):
    """Response model for inventory consumption operations"""
    transaction_id: str = Field(description="Unique identifier for this consumption transaction")
    product_id: PydanticObjectId = Field(description="ID of the consumed product")
    institution_id: int = Field(description="ID of the institution/warehouse")
    storage_location: Optional[str] = Field(description="Storage location where consumption occurred")
    total_quantity_consumed: float = Field(description="Total quantity consumed")
    unit: str = Field(description="Unit of measurement")
    consumption_date: datetime = Field(description="Date of consumption")
    reason: str = Field(description="Reason for consumption")
    notes: Optional[str] = Field(description="Additional notes")
    consumed_by: str = Field(description="Person who performed the consumption")
    batch_details: List[BatchConsumptionDetail] = Field(description="Details of consumption from each batch")
    movement_ids: List[PydanticObjectId] = Field(description="IDs of created inventory movement records")
    created_at: datetime = Field(description="Timestamp when consumption was recorded") 