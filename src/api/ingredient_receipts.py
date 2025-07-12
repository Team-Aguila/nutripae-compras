from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from beanie import PydanticObjectId

from models import IngredientReceiptCreate, IngredientReceiptResponse
from services import ingredient_receipt_service, inventory_movement_service
from services.ingredient_receipt_service import IngredientReceiptService
from core.dependencies import require_create, require_read, require_list

router = APIRouter()


@router.post(
    "/",
    response_model=IngredientReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register an Ingredient Receipt",
    description="Allows a Warehouse Manager to register the receipt of ingredients, updating the inventory with comprehensive tracking.",
)
async def register_ingredient_receipt(
    receipt_data: IngredientReceiptCreate,
    service: IngredientReceiptService = Depends(lambda: ingredient_receipt_service),
    current_user: dict = Depends(require_create()),
) -> IngredientReceiptResponse:
    """
    Registers the receipt of ingredients with comprehensive inventory management.

    **Features:**
    - Validates input data and product existence
    - Creates inventory items with proper unit and storage location handling
    - Creates inventory movement records for complete audit trail
    - Updates purchase order status based on actual receipt completion
    - Handles partial receipts properly
    - Supports manual mode (no purchase order) and purchase order linked mode

    **Parameters:**
    - **institution_id**: The ID of the institution where the ingredients are received (integer)
    - **purchase_order_id**: (Optional) The ID of the related purchase order. Leave null for manual mode
    - **receipt_date**: The date of the receipt
    - **delivery_person_name**: The name of the person delivering the items
    - **items**: A list of received items with detailed information:
      - **product_id**: The ID of the product/ingredient
      - **quantity**: The quantity received
      - **unit**: Unit of measurement (kg, units, liters, etc.)
      - **storage_location**: (Optional) Specific storage location within the institution
      - **lot**: Lot number of the product
      - **expiration_date**: Expiration date of the product
    """
    # In a real application, created_by would come from an authentication dependency
    created_by = "warehouse_manager_test"
    return await service.register_ingredient_receipt(receipt_data, created_by)


@router.get(
    "/{receipt_id}",
    response_model=IngredientReceiptResponse,
    summary="Get Ingredient Receipt by ID",
    description="Retrieve a specific ingredient receipt by its ID.",
)
async def get_ingredient_receipt(
    receipt_id: PydanticObjectId,
    service: IngredientReceiptService = Depends(lambda: ingredient_receipt_service),
    current_user: dict = Depends(require_read()),
) -> IngredientReceiptResponse:
    """
    Get an ingredient receipt by ID.
    
    **Parameters:**
    - **receipt_id**: The ID of the receipt to retrieve
    """
    return await service.get_receipt_by_id(receipt_id)


@router.get(
    "/institution/{institution_id}",
    response_model=List[IngredientReceiptResponse],
    summary="Get Ingredient Receipts by Institution",
    description="Retrieve ingredient receipts for a specific institution with pagination.",
)
async def get_ingredient_receipts_by_institution(
    institution_id: int,  # Changed to int to match coverage API
    limit: int = Query(default=100, le=1000, description="Maximum number of receipts to return"),
    offset: int = Query(default=0, ge=0, description="Number of receipts to skip"),
    service: IngredientReceiptService = Depends(lambda: ingredient_receipt_service),
    current_user: dict = Depends(require_list()),
) -> List[IngredientReceiptResponse]:
    """
    Get ingredient receipts for a specific institution.
    
    **Parameters:**
    - **institution_id**: The ID of the institution (integer from coverage module)
    - **limit**: Maximum number of receipts to return (default: 100, max: 1000)
    - **offset**: Number of receipts to skip for pagination (default: 0)
    """
    return await service.get_receipts_by_institution(institution_id, limit, offset) 