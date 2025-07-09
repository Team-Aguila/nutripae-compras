from fastapi import APIRouter, Depends, status, Query, Body
from typing import List, Optional
from beanie import PydanticObjectId

from ..models import (
    InventoryMovementResponse, 
    MovementType,
    InventoryConsumptionRequest,
    InventoryConsumptionResponse,
    StockSummaryResponse,
    InventoryReceiptRequest,
    InventoryReceiptResponse,
    ManualInventoryAdjustmentRequest,
    ManualInventoryAdjustmentResponse,
)
from ..services import inventory_movement_service
from ..services.inventory_movement_service import InventoryMovementService

router = APIRouter()


@router.post(
    "/receive-inventory",
    response_model=InventoryReceiptResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Receive Inventory (User Story 1)",
    description="Record the reception of ingredients (inputs), with or without a purchase order, automatically updating available inventory.",
)
async def receive_inventory(
    receipt_request: InventoryReceiptRequest = Body(...),
    service: InventoryMovementService = Depends(lambda: inventory_movement_service),
) -> InventoryReceiptResponse:
    """
    Record inventory reception (User Story 1).
    
    This endpoint implements the complete inventory receipt process:
    
    **Key Features:**
    - **Manual or Purchase Order**: Support reception with or without purchase order
    - **Batch Creation**: Creates new inventory batch with unique tracking
    - **Automatic Updates**: Updates available inventory automatically
    - **Audit Trail**: Creates detailed movement records for accountability
    - **Validation**: Ensures product exists and batch numbers are unique
    
    **Request Body:**
    ```json
    {
        "product_id": "648f8f8f8f8f8f8f8f8f8f8f",
        "institution_id": 1,
        "storage_location": "warehouse-01-A1",
        "quantity_received": 25.5,
        "unit_of_measure": "kg",
        "expiration_date": "2024-06-15",
        "batch_number": "BATCH-2024-001",
        "purchase_order_id": "PO-2024-123",
        "received_by": "warehouse_manager_juan",
        "reception_date": "2024-01-15T08:30:00Z",
        "notes": "Fresh vegetables delivery, good quality"
    }
    ```
    
    **Response:**
    - Complete receipt details including batch and movement IDs
    - Transaction ID for tracking
    - Created inventory batch information
    - Audit trail movement record
    
    **Error Conditions:**
    - 404: Product not found
    - 409: Batch number already exists
    - 400: Validation errors (invalid quantity, missing fields, etc.)
    
    **Acceptance Criteria Met:**
    - ✅ Allow manual entry (without purchase order)
    - ✅ Record: product_id, storage_location_id, quantity_received, unit_of_measure, expiration_date, batch_number
    - ✅ Create new inventory batch record in database
    - ✅ Log event as credit (+) movement in immutable ledger
    """
    return await service.receive_inventory(receipt_request)


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
        "product_id": str(product_id),
        "institution_id": institution_id,
        "storage_location": storage_location,
        "lot": lot,
        "current_stock": current_stock,
        "unit": "kg",  # This should come from product metadata in a real implementation
    }


@router.post(
    "/manual-adjustment",
    response_model=ManualInventoryAdjustmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Manual Inventory Adjustment",
    description="Create a manual inventory adjustment with comprehensive validation and stock protection.",
)
async def create_manual_adjustment(
    adjustment_request: ManualInventoryAdjustmentRequest = Body(...),
    service: InventoryMovementService = Depends(lambda: inventory_movement_service),
) -> ManualInventoryAdjustmentResponse:
    """
    Create a manual inventory adjustment for stock corrections.
    
    This endpoint implements critical business logic for inventory auditors:
    
    **Key Features:**
    - **Stock Protection**: Prevents adjustments that would result in negative stock
    - **Comprehensive Validation**: Validates product, inventory batch, and unit consistency
    - **Audit Trail**: Creates detailed movement records with reason and notes
    - **Real-time Updates**: Updates actual inventory levels immediately
    - **Transaction Tracking**: Provides unique transaction IDs for traceability
    
    **Request Body:**
    ```json
    {
        "product_id": "648f8f8f8f8f8f8f8f8f8f8f",
        "inventory_id": "648f8f8f8f8f8f8f8f8f8f8a",
        "quantity": -5.0,
        "unit": "kg",
        "reason": "Physical count discrepancy - found 5kg less than expected",
        "notes": "Verified during monthly inventory audit",
        "adjusted_by": "auditor_maria"
    }
    ```
    
    **Business Rules:**
    - **Negative Stock Prevention**: If current stock is 50kg and adjustment is -60kg, the transaction will be rejected
    - **Unit Consistency**: Adjustment unit must match the inventory batch unit
    - **Mandatory Reason**: Every adjustment must include a reason for audit purposes
    - **Product Validation**: Product and inventory batch must exist and be active
    
    **Response:**
    - Complete adjustment details including before/after stock levels
    - Transaction ID for tracking and audit purposes
    - Movement ID for the created audit trail record
    - Timestamp information for compliance
    
    **Error Conditions:**
    - 400: Adjustment would result in negative stock
    - 400: Unit mismatch between adjustment and inventory batch
    - 404: Product or inventory batch not found
    - 400: Invalid ID formats or missing required fields
    
    **Use Cases:**
    - Correct discrepancies found during physical counts
    - Record spoilage or damage losses
    - Adjust for measurement corrections
    - Document found/missing inventory
    """
    return await service.create_manual_adjustment(adjustment_request)


@router.post(
    "/consume-inventory",
    response_model=InventoryConsumptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Consume Inventory with FIFO Logic",
    description="Record inventory consumption using FIFO (First-In, First-Out) logic for batch management.",
)
async def consume_inventory_fifo(
    consumption_request: InventoryConsumptionRequest = Body(...),
    service: InventoryMovementService = Depends(lambda: inventory_movement_service),
) -> InventoryConsumptionResponse:
    """
    Consume inventory using FIFO (First-In, First-Out) logic.
    
    This endpoint implements the complete FIFO consumption process:
    
    **Key Features:**
    - **FIFO Logic**: Automatically selects oldest batches first
    - **Stock Validation**: Ensures sufficient stock before consumption
    - **Batch Tracking**: Records consumption from each batch
    - **Audit Trail**: Creates detailed movement records
    - **Transaction Integrity**: Groups all operations under a single transaction ID
    
    **Request Body:**
    ```json
    {
        "product_id": "648f8f8f8f8f8f8f8f8f8f8f",
        "institution_id": 1,
        "storage_location": "warehouse-01",
        "quantity": 5.5,
        "unit": "kg",
        "consumption_date": "2024-01-15T10:30:00Z",
        "reason": "menu preparation",
        "notes": "Used for lunch menu preparation",
        "consumed_by": "chef_maria"
    }
    ```
    
    **Response:**
    - Complete consumption details including batch breakdown
    - Transaction ID for tracking
    - List of created movement records
    - Remaining quantities in affected batches
    
    **Error Conditions:**
    - 404: Product not found
    - 400: Insufficient stock available
    - 400: Invalid quantity or other validation errors
    """
    return await service.consume_inventory_fifo(consumption_request)


@router.get(
    "/stock-summary/{product_id}/{institution_id}",
    response_model=StockSummaryResponse,
    summary="Get Available Stock Summary",
    description="Get detailed summary of available stock for a product with FIFO batch information.",
)
async def get_available_stock_summary(
    product_id: PydanticObjectId,
    institution_id: int,
    storage_location: Optional[str] = Query(
        default=None, description="Filter by storage location"
    ),
    service: InventoryMovementService = Depends(lambda: inventory_movement_service),
) -> StockSummaryResponse:
    """
    Get comprehensive summary of available stock for a product.
    
    **Parameters:**
    - **product_id**: The ID of the product
    - **institution_id**: The ID of the institution/warehouse
    - **storage_location**: (Optional) Filter by specific storage location
    
    **Returns:**
    Detailed stock summary including:
    - Total available stock across all batches
    - Number of available batches
    - Oldest and newest batch dates
    - Complete batch details with FIFO ordering
    - Individual batch information (lot, remaining weight, dates)
    
    **Use Cases:**
    - Check stock availability before consumption
    - Understand batch distribution and aging
    - Plan consumption strategies
    - Monitor inventory levels
    """
    return await service.get_available_stock_summary(
        product_id=product_id,
        institution_id=institution_id,
        storage_location=storage_location,
    )


@router.get(
    "/consumption-history/{product_id}",
    response_model=List[InventoryMovementResponse],
    summary="Get Consumption History",
    description="Get history of inventory consumption movements for a product.",
)
async def get_consumption_history(
    product_id: PydanticObjectId,
    institution_id: Optional[int] = Query(
        default=None, description="Filter by institution ID"
    ),
    storage_location: Optional[str] = Query(
        default=None, description="Filter by storage location"
    ),
    limit: int = Query(default=100, le=1000, description="Maximum number of records to return"),
    offset: int = Query(default=0, ge=0, description="Number of records to skip"),
    service: InventoryMovementService = Depends(lambda: inventory_movement_service),
) -> List[InventoryMovementResponse]:
    """
    Get history of consumption movements for a product.
    
    **Parameters:**
    - **product_id**: The ID of the product
    - **institution_id**: (Optional) Filter by institution ID
    - **storage_location**: (Optional) Filter by storage location
    - **limit**: Maximum number of records to return (default: 100, max: 1000)
    - **offset**: Number of records to skip for pagination (default: 0)
    
    **Returns:**
    List of consumption movements (USAGE type) showing:
    - Consumption details and quantities
    - Batch information (lot numbers, expiration dates)
    - Reasons and notes
    - Who performed the consumption
    - Transaction references
    
    **Use Cases:**
    - Audit consumption patterns
    - Track usage by person/reason
    - Analyze consumption trends
    - Verify FIFO compliance
    """
    return await service.get_movements_by_product(
        product_id=product_id,
        institution_id=institution_id,
        movement_type=MovementType.USAGE,
        limit=limit,
        offset=offset,
    ) 