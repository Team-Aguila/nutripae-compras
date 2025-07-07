from fastapi import APIRouter, Depends, status, Query
from typing import List, Optional
from beanie import PydanticObjectId

from ..models import InventoryMovementResponse, MovementType
from ..services import inventory_movement_service
from ..services.inventory_movement_service import InventoryMovementService

router = APIRouter()


@router.get(
    "/product/{product_id}",
    response_model=List[InventoryMovementResponse],
    summary="Get Inventory Movements by Product",
    description="Retrieve inventory movements for a specific product with filtering and pagination.",
)
async def get_inventory_movements_by_product(
    product_id: PydanticObjectId,
    institution_id: Optional[int] = Query(
        default=None, description="Filter by institution ID"
    ),
    movement_type: Optional[MovementType] = Query(
        default=None, description="Filter by movement type"
    ),
    limit: int = Query(default=100, le=1000, description="Maximum number of movements to return"),
    offset: int = Query(default=0, ge=0, description="Number of movements to skip"),
    service: InventoryMovementService = Depends(lambda: inventory_movement_service),
) -> List[InventoryMovementResponse]:
    """
    Get inventory movements for a specific product.
    
    **Parameters:**
    - **product_id**: The ID of the product to get movements for
    - **institution_id**: (Optional) Filter by institution ID
    - **movement_type**: (Optional) Filter by movement type (receipt, usage, adjustment, etc.)
    - **limit**: Maximum number of movements to return (default: 100, max: 1000)
    - **offset**: Number of movements to skip for pagination (default: 0)
    
    **Returns:**
    List of inventory movements showing the complete audit trail for the product.
    """
    return await service.get_movements_by_product(
        product_id=product_id,
        institution_id=institution_id,
        movement_type=movement_type,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/stock/{product_id}/{institution_id}",
    response_model=dict,
    summary="Get Current Stock Level",
    description="Get the current stock level for a specific product at an institution.",
)
async def get_current_stock(
    product_id: PydanticObjectId,
    institution_id: int,
    storage_location: Optional[str] = Query(
        default=None, description="Filter by storage location"
    ),
    lot: Optional[str] = Query(
        default=None, description="Filter by lot number"
    ),
    service: InventoryMovementService = Depends(lambda: inventory_movement_service),
) -> dict:
    """
    Get current stock level for a specific product at an institution.
    
    **Parameters:**
    - **product_id**: The ID of the product
    - **institution_id**: The ID of the institution
    - **storage_location**: (Optional) Filter by specific storage location
    - **lot**: (Optional) Filter by lot number
    
    **Returns:**
    Current stock level calculated from all movements.
    """
    current_stock = await service.get_current_stock(
        product_id=product_id,
        institution_id=institution_id,
        storage_location=storage_location,
        lot=lot,
    )
    
    return {
        "product_id": product_id,
        "institution_id": institution_id,
        "storage_location": storage_location,
        "lot": lot,
        "current_stock": current_stock,
        "unit": "kg",  # This should come from product metadata in a real implementation
    }


@router.post(
    "/manual-adjustment",
    response_model=InventoryMovementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Manual Inventory Adjustment",
    description="Create a manual inventory adjustment movement for stock corrections.",
)
async def create_manual_adjustment(
    product_id: PydanticObjectId,
    institution_id: int,
    quantity: float,
    unit: str = "kg",
    storage_location: Optional[str] = Query(default=None, description="Storage location"),
    lot: Optional[str] = Query(default=None, description="Lot number"),
    notes: Optional[str] = Query(default=None, description="Adjustment notes"),
    service: InventoryMovementService = Depends(lambda: inventory_movement_service),
) -> InventoryMovementResponse:
    """
    Create a manual inventory adjustment movement.
    
    **Parameters:**
    - **product_id**: The ID of the product
    - **institution_id**: The ID of the institution
    - **quantity**: The adjustment quantity (positive for increase, negative for decrease)
    - **unit**: Unit of measurement (default: kg)
    - **storage_location**: (Optional) Storage location
    - **lot**: (Optional) Lot number
    - **notes**: (Optional) Notes explaining the adjustment
    
    **Returns:**
    Created inventory movement record.
    """
    # In a real application, created_by would come from an authentication dependency
    created_by = "warehouse_manager_test"
    
    return await service.create_movement(
        movement_type=MovementType.ADJUSTMENT,
        product_id=product_id,
        institution_id=institution_id,
        quantity=quantity,
        unit=unit,
        storage_location=storage_location,
        lot=lot,
        notes=notes,
        created_by=created_by,
    ) 