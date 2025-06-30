from datetime import datetime, date
from enum import Enum
from typing import List, Optional

from beanie import Document, Indexed, PydanticObjectId
from pydantic import BaseModel, Field


class OrderStatus(str, Enum):
    """Purchase Order Status"""
    GENERATED = "Generada"
    SENT = "Enviada"
    PARTIALLY_RECEIVED = "Parcialmente Recibida"
    RECEIVED = "Recibida"
    CANCELLED = "Cancelada"


class PurchaseOrderItem(BaseModel):
    """Item within a Purchase Order"""
    ingredient_id: PydanticObjectId = Field(description="The ID of the ingredient")
    quantity: float = Field(gt=0, description="The required quantity of the ingredient")
    unit: str = Field(min_length=1, description="The purchase unit of measure")
    price: float = Field(ge=0, description="The unit price")


class PurchaseOrderBase(BaseModel):
    """Base model for a Purchase Order"""
    provider_id: str = Field(description="The ID of the provider")
    items: List[PurchaseOrderItem] = Field(description="List of items in the order")
    subtotal: float = Field(ge=0, description="The subtotal of the order")
    taxes: float = Field(ge=0, description="Taxes for the order")
    total: float = Field(ge=0, description="The total amount of the order")
    required_delivery_date: date = Field(description="Required delivery date for the order")


class PurchaseOrder(Document, PurchaseOrderBase):
    """Purchase Order DB Model"""
    order_number: Indexed(str, unique=True) = Field(description="Unique purchase order number")
    status: OrderStatus = Field(default=OrderStatus.GENERATED, description="The status of the order")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(description="The user who created the order")

    class Settings:
        name = "purchase_orders"


class PurchaseOrderCreate(BaseModel):
    """Model for creating a manual Purchase Order"""
    provider_id: str = Field(description="The ID of the provider")
    items: List[PurchaseOrderItem] = Field(description="List of items to order")
    required_delivery_date: date = Field(description="Required delivery date")
    # created_by will be injected by the service/API from auth credentials
    # subtotal and total will be calculated by the service


class PurchaseOrderResponse(PurchaseOrderBase):
    """Response model for a Purchase Order"""
    id: PydanticObjectId = Field(alias="_id")
    order_number: str
    status: OrderStatus
    created_at: datetime
    created_by: str

    class Config:
        populate_by_name = True 