from fastapi import APIRouter, Depends, Query, status
from typing import Optional
from beanie import PydanticObjectId

from models import (
    InventoryConsultationQuery,
    InventoryConsultationResponse,
)
from services import inventory_service
from services.inventory_service import InventoryService
from core.dependencies import require_create, require_read, require_list

router = APIRouter()


@router.get(
    "/",
    response_model=InventoryConsultationResponse,
    status_code=status.HTTP_200_OK,
    summary="Consult Inventory Levels",
    description="Allows an Inventory Manager to consult inventory levels by ingredient and warehouse, with filtering capabilities.",
)
async def consult_inventory(
    institution_id: Optional[int] = Query(None, description="Filter by institution/warehouse ID"),
    product_id: Optional[str] = Query(None, description="Filter by specific product/ingredient ID"),
    category: Optional[str] = Query(None, description="Filter by product category"),
    provider_id: Optional[str] = Query(None, description="Filter by provider ID"),
    show_expired: Optional[bool] = Query(True, description="Whether to include expired items"),
    show_below_threshold: Optional[bool] = Query(None, description="Filter items below minimum threshold"),
    limit: Optional[int] = Query(100, le=1000, description="Maximum number of items to return"),
    offset: Optional[int] = Query(0, description="Number of items to skip"),
    service: InventoryService = Depends(lambda: inventory_service),
    current_user: dict = Depends(require_list()),
) -> InventoryConsultationResponse:
    """
    Consult inventory levels with comprehensive filtering options.

    **Features:**
    - **Filterable by warehouse**: Filter by institution_id to see inventory at specific locations
    - **Filterable by ingredient**: Filter by product_id to see specific ingredients
    - **Filterable by category**: Filter by category to group related products
    - **Filterable by provider**: Filter by provider_id to see products from specific suppliers
    - **Expiration control**: Choose whether to include expired items
    - **Threshold alerts**: Filter items below minimum stock thresholds
    - **Pagination**: Use limit and offset for pagination

    **Returns:**
    - **quantity**: Current available quantity
    - **base_unit**: Unit of measurement (e.g., kg, units)
    - **last_entry_date**: Date of the most recent inventory entry
    - **expiration_dates**: Product expiration dates
    - **is_below_threshold**: Flag indicating if item is below minimum threshold
    - **summary**: Statistical summary of the inventory consultation

    **Use Cases:**
    - Monitor stock levels across warehouses
    - Identify products needing restocking
    - Track expiration dates for food safety
    - Analyze inventory distribution by category
    """
    # Convert string IDs to PydanticObjectId where needed, keep institution_id as int
    product_obj_id = PydanticObjectId(product_id) if product_id else None
    provider_obj_id = PydanticObjectId(provider_id) if provider_id else None
    
    # Create query parameters object
    query_params = InventoryConsultationQuery(
        institution_id=institution_id,  # Keep as int
        product_id=product_obj_id,
        category=category,
        provider_id=provider_obj_id,
        show_expired=show_expired,
        show_below_threshold=show_below_threshold,
        limit=limit,
        offset=offset,
    )
    
    # Execute the consultation
    return await service.consult_inventory(query_params)


@router.put(
    "/{inventory_id}/threshold",
    status_code=status.HTTP_200_OK,
    summary="Update Minimum Threshold",
    description="Update the minimum stock threshold for a specific inventory item.",
)
async def update_minimum_threshold(
    inventory_id: str,
    new_threshold: float = Query(..., ge=0, description="New minimum threshold value"),
    service: InventoryService = Depends(lambda: inventory_service),
    current_user: dict = Depends(require_create()),
) -> dict:
    """
    Update the minimum stock threshold for a specific inventory item.
    
    This endpoint allows inventory managers to set or update minimum stock thresholds
    for individual inventory items. This is useful for:
    - Setting reorder points
    - Implementing automated stock alerts
    - Maintaining adequate safety stock levels
    
    Args:
        inventory_id: The ID of the inventory item to update
        new_threshold: The new minimum threshold value (must be >= 0)
    
    Returns:
        Success message with updated threshold information
    """
    inventory_obj_id = PydanticObjectId(inventory_id)
    
    success = await service.update_minimum_threshold(inventory_obj_id, new_threshold)
    
    if success:
        return {
            "message": "Minimum threshold updated successfully",
            "inventory_id": inventory_id,
            "new_threshold": new_threshold
        }
    else:
        return {"message": "Failed to update minimum threshold"} 