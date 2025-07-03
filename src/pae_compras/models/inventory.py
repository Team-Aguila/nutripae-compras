from datetime import datetime, date
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


class InventoryItem(Document):
    """Inventory Item DB Model"""
    product_id: PydanticObjectId = Field(description="The ID of the product")
    institution_id: str = Field(description="The ID of the institution")
    remaining_weight: float = Field(gt=0, description="Remaining weight of the product in inventory")
    date_of_admission: date = Field(description="Date of admission of the product")
    lot: str = Field(description="Lot number of the product")
    expiration_date: date = Field(description="Expiration date of the product")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = Field(default=None)
    deleted_at: Optional[datetime] = Field(default=None)

    class Settings:
        name = "inventory_items" 