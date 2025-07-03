from fastapi import APIRouter, Depends, status

from ..models import IngredientReceiptCreate, IngredientReceiptResponse
from ..services import ingredient_receipt_service
from ..services.ingredient_receipt_service import IngredientReceiptService

router = APIRouter()


@router.post(
    "/",
    response_model=IngredientReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an Ingredient Receipt",
    description="Allows a Warehouse Manager to register the receipt of ingredients, updating the inventory.",
)
async def register_ingredient_receipt(
    receipt_data: IngredientReceiptCreate,
    service: IngredientReceiptService = Depends(lambda: ingredient_receipt_service),
) -> IngredientReceiptResponse:
    """
    Registers the receipt of ingredients.

    - **institution_id**: The ID of the institution where the ingredients are received.
    - **purchase_order_id**: (Optional) The ID of the related purchase order.
    - **receipt_date**: The date of the receipt.
    - **delivery_person_name**: The name of the person delivering the items.
    - **items**: A list of received items, including product ID, quantity, lot, and expiration date.
    """
    # In a real application, created_by would come from an authentication dependency
    created_by = "warehouse_manager_test"
    return await service.register_ingredient_receipt(receipt_data, created_by) 