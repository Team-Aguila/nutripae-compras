from datetime import datetime
from typing import List, Optional
from enum import Enum

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field, ConfigDict


class MovementType(str, Enum):
    """Types of inventory movements"""
    RECEIPT = "receipt"
    USAGE = "usage"
    ADJUSTMENT = "adjustment"
    EXPIRED = "expired"
    LOSS = "loss"


class InventoryMovement(Document):
    """Inventory Movement DB Model"""
    movement_type: MovementType = Field(description="Type of movement")
    product_id: PydanticObjectId = Field(description="REFERENCE -> products._id")
    institution_id: int = Field(description="REFERENCE -> institutions.id from coverage module")
    storage_location: Optional[str] = Field(default=None, description="Specific storage location within institution")
    quantity: float = Field(description="Quantity moved (positive for incoming, negative for outgoing)")
    unit: str = Field(default="kg", description="Unit of measurement")
    lot: Optional[str] = Field(default=None, description="Lot number")
    expiration_date: Optional[datetime] = Field(default=None, description="Expiration date for the item")
    reference_id: Optional[PydanticObjectId] = Field(default=None, description="Reference to related document")
    reference_type: Optional[str] = Field(default=None, description="Type of reference document")
    movement_date: datetime = Field(description="Date of the movement")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    created_by: str = Field(description="User who created the movement")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of document creation")
    deleted_at: Optional[datetime] = Field(default=None, description="For soft deletes. Null if not deleted")

    class Settings:
        name = "inventory_movements"
        indexes = [
            "product_id",
            "institution_id",
            "movement_type",
            "movement_date",
            "deleted_at"
        ]


class BatchConsumptionDetail(BaseModel):
    """Details of consumption from a specific batch"""
    inventory_id: str = Field(description="String representation of inventory batch ID")
    lot: str = Field(description="Lot number of the consumed batch")
    consumed_quantity: float = Field(description="Quantity consumed from this batch")
    remaining_quantity: float = Field(description="Remaining quantity in this batch after consumption")
    expiration_date: Optional[datetime] = Field(description="Expiration date of this batch")
    date_of_admission: datetime = Field(description="Date when this batch was added to inventory")


class InventoryMovementResponse(BaseModel):
    """Response model for inventory movement"""
    id: str = Field(alias="_id", description="String representation of movement ID")
    movement_type: MovementType
    product_id: str = Field(description="String representation of product ID")
    institution_id: int
    storage_location: Optional[str]
    quantity: float
    unit: str
    lot: Optional[str]
    expiration_date: Optional[datetime]
    reference_id: Optional[str] = Field(description="String representation of reference ID")
    reference_type: Optional[str]
    movement_date: datetime
    notes: Optional[str]
    created_by: str
    created_at: datetime

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            PydanticObjectId: str
        }
    )


class InventoryConsumptionRequest(BaseModel):
    """Request model for inventory consumption"""
    product_id: str = Field(description="String representation of product ID")
    institution_id: int = Field(description="ID of the institution/warehouse")
    storage_location: Optional[str] = Field(default=None, description="Storage location to consume from")
    quantity: float = Field(gt=0, description="Quantity to consume")
    unit: str = Field(default="kg", description="Unit of measurement")
    consumption_date: Optional[datetime] = Field(default=None, description="Date of consumption")
    reason: str = Field(description="Reason for consumption")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    consumed_by: str = Field(description="Person performing the consumption")


class InventoryConsumptionResponse(BaseModel):
    """Response model for inventory consumption operations"""
    transaction_id: str = Field(description="Unique identifier for this consumption transaction")
    product_id: str = Field(description="String representation of product ID")
    institution_id: int = Field(description="ID of the institution/warehouse")
    storage_location: Optional[str] = Field(description="Storage location where consumption occurred")
    total_quantity_consumed: float = Field(description="Total quantity consumed")
    unit: str = Field(description="Unit of measurement")
    consumption_date: datetime = Field(description="Date of consumption")
    reason: str = Field(description="Reason for consumption")
    notes: Optional[str] = Field(description="Additional notes")
    consumed_by: str = Field(description="Person who performed the consumption")
    batch_details: List[BatchConsumptionDetail] = Field(description="Details of consumption from each batch")
    movement_ids: List[str] = Field(description="String representations of created inventory movement record IDs")
    created_at: datetime = Field(description="Timestamp when consumption was recorded")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            PydanticObjectId: str
        }
    )


class BatchDetail(BaseModel):
    """Details of an individual inventory batch"""
    inventory_id: str = Field(description="String representation of inventory batch ID")
    lot: str = Field(description="Lot number")
    remaining_weight: float = Field(description="Remaining weight in this batch")
    date_of_admission: datetime = Field(description="Date when batch was added to inventory")
    expiration_date: Optional[datetime] = Field(description="Expiration date of this batch")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            PydanticObjectId: str
        }
    )


class StockSummaryResponse(BaseModel):
    """Response model for stock summary endpoint"""
    product_id: str = Field(description="String representation of product ID")
    institution_id: int = Field(description="Institution ID")
    storage_location: Optional[str] = Field(description="Storage location filter applied")
    total_available_stock: float = Field(description="Total available stock across all batches")
    number_of_batches: int = Field(description="Number of available batches")
    oldest_batch_date: Optional[datetime] = Field(description="Date of oldest batch")
    newest_batch_date: Optional[datetime] = Field(description="Date of newest batch")
    batches: List[BatchDetail] = Field(description="List of available batches with FIFO ordering")
    unit: str = Field(default="kg", description="Unit of measurement")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            PydanticObjectId: str
        }
    )


class ManualInventoryAdjustmentRequest(BaseModel):
    """Request model for manual inventory adjustments"""
    product_id: str = Field(description="String representation of product ID")
    inventory_id: str = Field(description="String representation of inventory batch ID")
    quantity: float = Field(description="Adjustment quantity (positive for additions, negative for subtractions)")
    unit: str = Field(default="kg", description="Unit of measurement")
    reason: str = Field(min_length=1, description="Mandatory reason for the adjustment")
    notes: Optional[str] = Field(default=None, description="Additional notes for the adjustment")
    adjusted_by: Optional[str] = Field(default="inventory_auditor", description="Person performing the adjustment")

    model_config = ConfigDict(
        str_strip_whitespace=True
    )


class ManualInventoryAdjustmentResponse(BaseModel):
    """Response model for manual inventory adjustments"""
    transaction_id: str = Field(description="Unique identifier for this adjustment transaction")
    inventory_id: str = Field(description="String representation of inventory batch ID")
    product_id: str = Field(description="String representation of product ID")
    institution_id: int = Field(description="Institution ID")
    storage_location: Optional[str] = Field(description="Storage location")
    adjustment_quantity: float = Field(description="Adjustment quantity applied")
    unit: str = Field(description="Unit of measurement")
    reason: str = Field(description="Reason for the adjustment")
    notes: Optional[str] = Field(description="Additional notes")
    adjusted_by: str = Field(description="Person who performed the adjustment")
    previous_stock: float = Field(description="Stock level before adjustment")
    new_stock: float = Field(description="Stock level after adjustment")
    movement_id: str = Field(description="String representation of created movement record ID")
    adjustment_date: datetime = Field(description="Date and time of adjustment")
    created_at: datetime = Field(description="Timestamp when adjustment was recorded")

    model_config = ConfigDict(
        populate_by_name=True,
        json_encoders={
            PydanticObjectId: str
        }
    ) 