from datetime import datetime
from typing import Optional

from beanie import Document, PydanticObjectId
from pydantic import Field


class Inventory(Document):
    """Inventory DB Model"""
    product_id: PydanticObjectId = Field(description="REFERENCE -> products._id")
    institution_id: PydanticObjectId = Field(description="REFERENCE -> institutions._id")
    remaining_weight: float = Field(gt=0, description="Remaining weight in inventory")
    date_of_admission: datetime = Field(description="Date of admission to inventory")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Timestamp of document creation")
    updated_at: Optional[datetime] = Field(default=None, description="Timestamp of the last update")
    deleted_at: Optional[datetime] = Field(default=None, description="For soft deletes. Null if not deleted")

    class Settings:
        name = "inventory"
        indexes = [
            "product_id",
            "institution_id",
            "date_of_admission",
            "deleted_at"
        ] 