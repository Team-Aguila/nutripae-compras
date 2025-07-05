from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """Purchase Order Status"""
    PENDING = "pending"
    SHIPPED = "shipped"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class LineItem(BaseModel):
    """Line item within a Purchase Order (embedded document)"""
    product_id: PydanticObjectId = Field(description="REFERENCE -> products._id")
    quantity: int = Field(gt=0, description="Quantity of the product")
    price: Decimal = Field(description="Price per unit using Decimal for monetary values")


class PurchaseOrder(Document):
    """Purchase Order DB Model"""
    purchase_order_date: datetime = Field(description="When the order was placed")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Order status")
    provider_id: PydanticObjectId = Field(description="REFERENCE -> providers._id")
    line_items: List[LineItem] = Field(description="Array of embedded line item documents")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of document creation")
    updated_at: Optional[datetime] = Field(default=None, description="Timestamp of the last update")
    deleted_at: Optional[datetime] = Field(default=None, description="For soft deletes. Null if not deleted")

    class Settings:
        name = "purchase_orders"
        indexes = [
            "provider_id",
            "status",
            "purchase_order_date",
            "deleted_at"
        ] 