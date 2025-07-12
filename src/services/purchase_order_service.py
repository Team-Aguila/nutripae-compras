import datetime
from typing import List, Optional
from decimal import Decimal
from beanie import PydanticObjectId
from fastapi import HTTPException, status
import math

from models import (
    PurchaseOrder,
    PurchaseOrderCreate,
    PurchaseOrderItem,
    PurchaseOrderResponse,
    LineItem,
    OrderStatus,
    MarkShippedResponse,
    CancelOrderRequest,
    CancelOrderResponse,
    PurchaseOrderFilters,
    PaginatedPurchaseOrderResponse,
    PurchaseOrderSummary,
)


class PurchaseOrderService:
    @staticmethod
    async def generate_order_number() -> str:
        """Generates a unique purchase order number."""
        now = datetime.datetime.now()
        # Simple example: PO-YYYYMMDD-HHMMSS
        return f"PO-{now.strftime('%Y%m%d')}-{now.strftime('%H%M%S%f')}"

    @staticmethod
    async def list_purchase_orders(filters: PurchaseOrderFilters) -> PaginatedPurchaseOrderResponse:
        """
        Lists purchase orders with filtering and pagination.
        """
        # Build query conditions
        query_conditions = {}
        
        # Filter by order number (partial match)
        if filters.order_number:
            query_conditions["order_number"] = {"$regex": filters.order_number, "$options": "i"}
        
        # Filter by provider ID
        if filters.provider_id:
            query_conditions["provider_id"] = filters.provider_id
        
        # Filter by status
        if filters.status:
            query_conditions["status"] = filters.status
        
        # Filter by creation date range
        if filters.created_from or filters.created_to:
            date_filter = {}
            if filters.created_from:
                date_filter["$gte"] = datetime.datetime.combine(filters.created_from, datetime.time.min)
            if filters.created_to:
                date_filter["$lte"] = datetime.datetime.combine(filters.created_to, datetime.time.max)
            query_conditions["created_at"] = date_filter
        
        # Filter by delivery date range
        if filters.delivery_from or filters.delivery_to:
            delivery_filter = {}
            if filters.delivery_from:
                delivery_filter["$gte"] = filters.delivery_from
            if filters.delivery_to:
                delivery_filter["$lte"] = filters.delivery_to
            query_conditions["required_delivery_date"] = delivery_filter
        
        # Exclude soft-deleted orders
        query_conditions["deleted_at"] = None
        
        # Get total count for pagination
        total_count = await PurchaseOrder.find(query_conditions).count()
        
        # Calculate pagination
        skip = (filters.page - 1) * filters.limit
        total_pages = math.ceil(total_count / filters.limit) if total_count > 0 else 0
        
        # Get paginated results
        orders = await PurchaseOrder.find(query_conditions)\
            .sort([("created_at", -1)])\
            .skip(skip)\
            .limit(filters.limit)\
            .to_list()
        
        # Convert to summary format
        order_summaries = []
        for order in orders:
            order_dict = order.model_dump()
            # Ensure required fields have default values if missing
            if order_dict.get('purchase_order_date') is None:
                order_dict['purchase_order_date'] = order.created_at
            if order_dict.get('line_items') is None:
                order_dict['line_items'] = []
            
            order_summaries.append(PurchaseOrderSummary(**order_dict))
        
        return PaginatedPurchaseOrderResponse(
            items=order_summaries,
            total=total_count,
            page=filters.page,
            limit=filters.limit,
            total_pages=total_pages,
            has_next=filters.page < total_pages,
            has_previous=filters.page > 1
        )

    @staticmethod
    async def get_purchase_order_by_id(order_id: PydanticObjectId) -> PurchaseOrderResponse:
        """
        Gets a purchase order by its ID.
        """
        order = await PurchaseOrder.get(order_id)
        if not order:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase order with ID {order_id} not found."
            )
        
        if order.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Purchase order with ID {order_id} not found."
            )
        
        # Handle legacy data
        order_dict = order.model_dump()
        if order_dict.get('purchase_order_date') is None:
            order_dict['purchase_order_date'] = order.created_at
        if order_dict.get('line_items') is None:
            order_dict['line_items'] = []
        
        return PurchaseOrderResponse(**order_dict)

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

    @staticmethod
    async def calculate_gross_quantity_with_shrinkage(
        net_quantity_needed: float, 
        product_id: PydanticObjectId
    ) -> float:
        """
        Calculate gross quantity needed accounting for shrinkage factor.
        
        This method demonstrates how to apply the shrinkage factor to convert
        net quantity (what you need after processing) to gross quantity 
        (what you need to order to account for losses).
        
        Formula: gross_quantity_needed = net_quantity_needed * (1 + product.shrinkage_factor)
        
        Args:
            net_quantity_needed: The final quantity needed after processing
            product_id: ID of the product to get shrinkage factor from
            
        Returns:
            float: Gross quantity that should be ordered
            
        Example:
            - Net quantity needed: 1.0 kg of peeled potatoes
            - Product shrinkage factor: 0.20 (20% loss from peeling)
            - Gross quantity calculated: 1.0 * (1 + 0.20) = 1.2 kg raw potatoes
        """
        from ..models import Product
        
        # Get the product to access its shrinkage factor
        product = await Product.get(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found"
            )
        
        # Apply shrinkage factor formula
        gross_quantity = net_quantity_needed * (1 + product.shrinkage_factor)
        
        return gross_quantity

purchase_order_service = PurchaseOrderService() 