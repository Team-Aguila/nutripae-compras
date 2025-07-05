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
    OrderStatus,
    MarkShippedResponse,
    CancelOrderRequest,
    CancelOrderResponse,
)


class PurchaseOrderService:
    @staticmethod
    async def generate_order_number() -> str:
        """Generates a unique purchase order number."""
        now = datetime.datetime.now()
        # Simple example: PO-YYYYMMDD-HHMMSS
        return f"PO-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S%f')}"

    @staticmethod
    async def cancel_purchase_order(
        order_id: PydanticObjectId, 
        cancel_data: CancelOrderRequest, 
        cancelled_by: str
    ) -> CancelOrderResponse:
        """
        Cancels a purchase order.
        - Validates the order exists.
        - Validates no receipts have been registered (currently assumes no receipts if not completed).
        - Updates status to CANCELLED and records cancellation details.
        """
        # Find the order
        order = await PurchaseOrder.get(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase order with ID {order_id} not found."
            )

        # Validate current status - cannot cancel if already completed or cancelled
        if order.status == OrderStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order is already cancelled."
            )
        
        if order.status == OrderStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel order. Order has already been completed with receipts registered."
            )

        # Update the order
        now = datetime.datetime.utcnow()
        order.status = OrderStatus.CANCELLED
        order.cancelled_at = now
        order.cancelled_by = cancelled_by
        order.cancellation_reason = cancel_data.reason
        order.updated_at = now

        await order.save()

        return CancelOrderResponse(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            cancelled_at=order.cancelled_at,
            cancelled_by=order.cancelled_by,
            cancellation_reason=order.cancellation_reason,
            message="Order successfully cancelled"
        )

    @staticmethod
    async def mark_order_as_shipped(order_id: PydanticObjectId) -> MarkShippedResponse:
        """
        Marks a purchase order as shipped.
        - Validates the order exists.
        - Validates current status is PENDING.
        - Updates status to SHIPPED and records shipping timestamp.
        """
        # Find the order
        order = await PurchaseOrder.get(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase order with ID {order_id} not found."
            )

        # Validate current status
        if order.status != OrderStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot mark order as shipped. Current status is '{order.status}'. Only orders with status 'pending' can be marked as shipped."
            )

        # Update the order
        now = datetime.datetime.utcnow()
        order.status = OrderStatus.SHIPPED
        order.shipped_at = now
        order.updated_at = now

        await order.save()

        return MarkShippedResponse(
            id=order.id,
            order_number=order.order_number,
            status=order.status,
            shipped_at=order.shipped_at,
            message="Order successfully marked as shipped"
        )

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