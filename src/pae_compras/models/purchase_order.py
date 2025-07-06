from datetime import datetime, date
from decimal import Decimal
from enum import Enum
from typing import List, Optional, Any

from beanie import Document, PydanticObjectId, Indexed
from pydantic import BaseModel, Field, field_validator, field_serializer
from pymongo import ASCENDING
from bson import Decimal128


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

    @field_validator('price', mode='before')
    @classmethod
    def validate_price(cls, v):
        if isinstance(v, Decimal128):
            return Decimal(str(v))
        return v

    @field_serializer('price')
    def serialize_price(self, value: Decimal) -> str:
        return str(value)


class PurchaseOrderItem(BaseModel):
    """Item within a Purchase Order for create/update operations"""
    product_id: PydanticObjectId = Field(description="REFERENCE -> products._id")
    quantity: int = Field(gt=0, description="Quantity of the product")
    price: Decimal = Field(gt=0, description="Price per unit using Decimal for monetary values")

    @field_validator('price', mode='before')
    @classmethod
    def validate_price(cls, v):
        if isinstance(v, Decimal128):
            return Decimal(str(v))
        return v

    @field_serializer('price')
    def serialize_price(self, value: Decimal) -> str:
        return str(value)


class PurchaseOrder(Document):
    """Purchase Order DB Model"""
    purchase_order_date: datetime = Field(description="When the order was placed")
    status: OrderStatus = Field(default=OrderStatus.PENDING, description="Order status")
    provider_id: PydanticObjectId = Field(description="REFERENCE -> providers._id")
    line_items: List[LineItem] = Field(description="Array of embedded line item documents")
    order_number: Indexed(str, unique=True) = Field(default=None, description="Unique order number")
    subtotal: Optional[Decimal] = Field(default=None, description="Subtotal amount")
    taxes: Optional[Decimal] = Field(default=None, description="Tax amount")
    total: Optional[Decimal] = Field(default=None, description="Total amount")
    required_delivery_date: Optional[date] = Field(default=None, description="Required delivery date")
    shipped_at: Optional[datetime] = Field(default=None, description="Timestamp when order was marked as shipped")
    cancelled_at: Optional[datetime] = Field(default=None, description="Timestamp when order was cancelled")
    cancelled_by: Optional[str] = Field(default=None, description="User who cancelled the order")
    cancellation_reason: Optional[str] = Field(default=None, description="Reason for cancelling the order")
    created_by: Optional[str] = Field(default=None, description="User who created the order")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of document creation")
    updated_at: Optional[datetime] = Field(default=None, description="Timestamp of the last update")
    deleted_at: Optional[datetime] = Field(default=None, description="For soft deletes. Null if not deleted")

    @field_validator('subtotal', 'taxes', 'total', mode='before')
    @classmethod
    def validate_decimal_fields(cls, v):
        if v is None:
            return v
        if isinstance(v, Decimal128):
            return Decimal(str(v))
        return v

    @field_serializer('subtotal', 'taxes', 'total')
    def serialize_decimal_fields(self, value: Optional[Decimal]) -> Optional[str]:
        if value is None:
            return None
        return str(value)

    class Settings:
        name = "purchase_orders"
        indexes = [
            "provider_id",
            "status",
            "purchase_order_date",
            "deleted_at"
        ]


class PurchaseOrderCreate(BaseModel):
    """Model for creating a Purchase Order"""
    provider_id: PydanticObjectId = Field(description="REFERENCE -> providers._id")
    items: List[PurchaseOrderItem] = Field(description="List of items to be ordered")
    required_delivery_date: Optional[date] = Field(default=None, description="Required delivery date")
    purchase_order_date: Optional[datetime] = Field(default_factory=datetime.utcnow, description="When the order was placed")


class PurchaseOrderResponse(BaseModel):
    """Response model for Purchase Order"""
    id: PydanticObjectId = Field(alias="_id")
    purchase_order_date: datetime
    status: OrderStatus
    provider_id: PydanticObjectId
    line_items: List[LineItem]
    order_number: Optional[str]
    subtotal: Optional[Decimal]
    taxes: Optional[Decimal]
    total: Optional[Decimal]
    required_delivery_date: Optional[date]
    shipped_at: Optional[datetime]
    cancelled_at: Optional[datetime]
    cancelled_by: Optional[str]
    cancellation_reason: Optional[str]
    created_by: Optional[str]
    created_at: datetime
    updated_at: Optional[datetime]

    class Config:
        populate_by_name = True


class CancelOrderRequest(BaseModel):
    """Request model for cancelling a purchase order"""
    reason: str = Field(min_length=1, max_length=500, description="Reason for cancelling the order")


class CancelOrderResponse(BaseModel):
    """Response model for cancel order operation"""
    id: PydanticObjectId = Field(alias="_id")
    order_number: Optional[str]
    status: OrderStatus
    cancelled_at: datetime
    cancelled_by: str
    cancellation_reason: str
    message: str

    class Config:
        populate_by_name = True


class MarkShippedResponse(BaseModel):
    """Response model for mark shipped operation"""
    id: PydanticObjectId = Field(alias="_id")
    order_number: Optional[str]
    status: OrderStatus
    shipped_at: datetime
    message: str

    class Config:
        populate_by_name = True 