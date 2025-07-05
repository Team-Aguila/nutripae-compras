import datetime
from typing import List
from decimal import Decimal
from beanie import PydanticObjectId
from fastapi import HTTPException, status

from ..models import (
    PurchaseOrder,
    PurchaseOrderCreate,
    PurchaseOrderItem,
    PurchaseOrderResponse,
    LineItem,
)


class PurchaseOrderService:
    @staticmethod
    async def generate_order_number() -> str:
        """Generates a unique purchase order number."""
        now = datetime.datetime.now()
        # Simple example: PO-YYYYMMDD-HHMMSS
        return f"PO-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S%f')}"

    @staticmethod
    async def create_manual_purchase_order(
        order_data: PurchaseOrderCreate, created_by: str
    ) -> PurchaseOrderResponse:
        """
        Creates a manual purchase order.
        - Validates input data.
        - Calculates subtotal and total.
        - Generates a unique order number.
        - Saves the order to the database.
        """
        if not order_data.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Purchase order must have at least one item.",
            )

        # Calculate subtotal and total
        subtotal = sum(item.quantity * item.price for item in order_data.items)
        # Assuming taxes are 0 for now
        taxes = Decimal("0.0")
        total = subtotal + taxes

        order_number = await PurchaseOrderService.generate_order_number()

        # Convert PurchaseOrderItem to LineItem
        line_items = [
            LineItem(
                product_id=item.product_id,
                quantity=item.quantity,
                price=item.price
            )
            for item in order_data.items
        ]

        new_order = PurchaseOrder(
            purchase_order_date=order_data.purchase_order_date,
            provider_id=order_data.provider_id,
            line_items=line_items,
            required_delivery_date=order_data.required_delivery_date,
            order_number=order_number,
            subtotal=subtotal,
            taxes=taxes,
            total=total,
            created_by=created_by,
        )

        await new_order.insert()

        return PurchaseOrderResponse(**new_order.model_dump())

purchase_order_service = PurchaseOrderService() 