from fastapi import APIRouter, Depends, status

from ..models import PurchaseOrderCreate, PurchaseOrderResponse
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