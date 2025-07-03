from datetime import datetime, date
from typing import List, Optional

from beanie import Document, PydanticObjectId
from pydantic import BaseModel, Field


class ReceivedItem(BaseModel):
    """Item received as part of an ingredient receipt"""
    product_id: PydanticObjectId = Field(description="The ID of the product received")
    quantity: float = Field(gt=0, description="The quantity of the product received")
    lot: str = Field(description="The lot number of the product")
    expiration_date: date = Field(description="The expiration date of the product")


class IngredientReceiptBase(BaseModel):
    """Base model for an Ingredient Receipt"""
    institution_id: str = Field(description="The ID of the institution where the ingredients were received")
    purchase_order_id: Optional[PydanticObjectId] = Field(default=None, description="The ID of the related purchase order")
    receipt_date: date = Field(description="The date the ingredients were received")
    delivery_person_name: str = Field(description="Name of the person who delivered the ingredients")
    items: List[ReceivedItem] = Field(description="List of received items")


class IngredientReceipt(Document, IngredientReceiptBase):
    """Ingredient Receipt DB Model"""
    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(description="The user who registered the receipt")

    class Settings:
        name = "ingredient_receipts"


class IngredientReceiptCreate(BaseModel):
    """Model for creating an Ingredient Receipt"""
    institution_id: str = Field(description="The ID of the institution where the ingredients were received")
    purchase_order_id: Optional[PydanticObjectId] = Field(default=None, description="The ID of the related purchase order")
    receipt_date: date = Field(description="The date the ingredients were received")
    delivery_person_name: str = Field(description="Name of the person who delivered the ingredients")
    items: List[ReceivedItem] = Field(description="List of received items")


class IngredientReceiptResponse(IngredientReceiptBase):
    """Response model for an Ingredient Receipt"""
    id: PydanticObjectId = Field(alias="_id")
    created_at: datetime
    created_by: str

    class Config:
        populate_by_name = True 