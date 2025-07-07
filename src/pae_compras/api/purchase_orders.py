from fastapi import APIRouter, Depends, status, Query
from beanie import PydanticObjectId
from typing import Optional
from datetime import date

from ..models import (
    PurchaseOrderCreate, 
    PurchaseOrderResponse, 
    MarkShippedResponse,
    CancelOrderRequest,
    CancelOrderResponse,
    PurchaseOrderFilters,
    PaginatedPurchaseOrderResponse,
    OrderStatus,
)
from ..services import purchase_order_service
from ..services.purchase_order_service import PurchaseOrderService

router = APIRouter()


@router.get(
    "/",
    response_model=PaginatedPurchaseOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="List and filter Purchase Orders",
    description="Retrieves a paginated list of purchase orders with optional filtering by order number, provider, status, and date ranges.",
)
async def list_purchase_orders(
    order_number: Optional[str] = Query(None, description="Filter by order number (partial match)"),
    provider_id: Optional[str] = Query(None, description="Filter by provider ID"),
    status: Optional[OrderStatus] = Query(None, description="Filter by order status"),
    created_from: Optional[date] = Query(None, description="Filter orders created from this date (YYYY-MM-DD)"),
    created_to: Optional[date] = Query(None, description="Filter orders created until this date (YYYY-MM-DD)"),
    delivery_from: Optional[date] = Query(None, description="Filter orders with delivery date from this date (YYYY-MM-DD)"),
    delivery_to: Optional[date] = Query(None, description="Filter orders with delivery date until this date (YYYY-MM-DD)"),
    page: int = Query(1, ge=1, description="Page number (starts from 1)"),
    limit: int = Query(10, ge=1, le=100, description="Number of items per page (max 100)"),
    service: PurchaseOrderService = Depends(lambda: purchase_order_service),
) -> PaginatedPurchaseOrderResponse:
    """
    Lists purchase orders with filtering and pagination.
    
    Supports filtering by:
    - **order_number**: Partial match on order number
    - **provider_id**: Exact match on provider ID
    - **status**: Filter by order status (pending, shipped, completed, cancelled)
    - **created_from/created_to**: Date range for order creation
    - **delivery_from/delivery_to**: Date range for required delivery date
    - **page/limit**: Pagination controls
    """
    # Convert provider_id string to PydanticObjectId if provided
    provider_obj_id = None
    if provider_id:
        try:
            provider_obj_id = PydanticObjectId(provider_id)
        except Exception:
            # If invalid ObjectId format, we'll let the service handle it
            pass
    
    filters = PurchaseOrderFilters(
        order_number=order_number,
        provider_id=provider_obj_id,
        status=status,
        created_from=created_from,
        created_to=created_to,
        delivery_from=delivery_from,
        delivery_to=delivery_to,
        page=page,
        limit=limit
    )
    
    return await service.list_purchase_orders(filters)


@router.get(
    "/{order_id}",
    response_model=PurchaseOrderResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Purchase Order by ID",
    description="Retrieves the complete details of a specific purchase order by its ID.",
)
async def get_purchase_order(
    order_id: PydanticObjectId,
    service: PurchaseOrderService = Depends(lambda: purchase_order_service),
) -> PurchaseOrderResponse:
    """
    Gets a purchase order by its ID.
    
    - **order_id**: The ID of the purchase order to retrieve
    
    Returns the complete purchase order details including all line items and status information.
    """
    return await service.get_purchase_order_by_id(order_id)


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