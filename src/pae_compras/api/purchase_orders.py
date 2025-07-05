from fastapi import APIRouter, Depends, status
from beanie import PydanticObjectId

from ..models import (
    PurchaseOrderCreate, 
    PurchaseOrderResponse, 
    MarkShippedResponse,
    CancelOrderRequest,
    CancelOrderResponse
)
from ..services import purchase_order_service
from ..services.purchase_order_service import PurchaseOrderService

router = APIRouter()


@router.post(
    "/",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a manual Purchase Order",
    description="Allows for the manual creation of a purchase order by providing provider and item details.",
)
async def create_manual_purchase_order(
    order_data: PurchaseOrderCreate,
    service: PurchaseOrderService = Depends(lambda: purchase_order_service),
) -> PurchaseOrderResponse:
    """
    Manually creates a new purchase order.

    - **provider_id**: The ID of the provider for this order.
    - **items**: A list of items to be ordered, including ingredient ID, quantity, unit, and price.
    - **required_delivery_date**: The date when the order is required to be delivered.
    """
    # In a real application, created_by would come from an authentication dependency
    created_by = "test_user"
    return await service.create_manual_purchase_order(order_data, created_by)


@router.patch(
    "/{order_id}/mark-shipped",
    response_model=MarkShippedResponse,
    status_code=status.HTTP_200_OK,
    summary="Mark Purchase Order as Shipped",
    description="Changes the status of a purchase order from 'pending' to 'shipped' and records the shipping timestamp.",
)
async def mark_purchase_order_as_shipped(
    order_id: PydanticObjectId,
    service: PurchaseOrderService = Depends(lambda: purchase_order_service),
) -> MarkShippedResponse:
    """
    Marks a purchase order as shipped.

    - **order_id**: The ID of the purchase order to mark as shipped.
    
    Requirements:
    - Order must exist
    - Order status must be 'pending'
    """
    return await service.mark_order_as_shipped(order_id)


@router.patch(
    "/{order_id}/cancel",
    response_model=CancelOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Cancel Purchase Order",
    description="Cancels a purchase order and records the cancellation reason. Cannot cancel orders that have already been completed.",
)
async def cancel_purchase_order(
    order_id: PydanticObjectId,
    cancel_data: CancelOrderRequest,
    service: PurchaseOrderService = Depends(lambda: purchase_order_service),
) -> CancelOrderResponse:
    """
    Cancels a purchase order.

    - **order_id**: The ID of the purchase order to cancel.
    - **reason**: The reason for cancelling the order.
    
    Requirements:
    - Order must exist
    - Order cannot be already cancelled
    - Order cannot be completed (no receipts registered)
    """
    # In a real application, cancelled_by would come from an authentication dependency
    cancelled_by = "test_user"
    return await service.cancel_purchase_order(order_id, cancel_data, cancelled_by) 