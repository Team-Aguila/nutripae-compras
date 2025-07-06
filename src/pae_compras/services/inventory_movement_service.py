from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from beanie import PydanticObjectId
import uuid

from ..models import (
    InventoryMovement,
    MovementType,
    InventoryMovementResponse,
    Inventory,
    Product,
    InventoryConsumptionRequest,
    InventoryConsumptionResponse,
    BatchConsumptionDetail,
)


class InventoryMovementService:
    """Service for managing inventory movements"""

    @staticmethod
    async def create_movement(
        movement_type: MovementType,
        product_id: PydanticObjectId,
        institution_id: int,
        quantity: float,
        unit: str = "kg",
        storage_location: Optional[str] = None,
        lot: Optional[str] = None,
        expiration_date: Optional[datetime] = None,
        reference_id: Optional[PydanticObjectId] = None,
        reference_type: Optional[str] = None,
        notes: Optional[str] = None,
        created_by: str = "system",
        movement_date: Optional[datetime] = None,
    ) -> InventoryMovementResponse:
        """
        Create an inventory movement record.
        
        Args:
            movement_type: Type of movement (RECEIPT, USAGE, etc.)
            product_id: ID of the product
            institution_id: ID of the institution (integer from coverage module)
            quantity: Quantity moved (positive for incoming, negative for outgoing)
            unit: Unit of measurement
            storage_location: Specific storage location
            lot: Lot number
            expiration_date: Expiration date
            reference_id: Reference to related document
            reference_type: Type of reference document
            notes: Additional notes
            created_by: User who created the movement
            movement_date: Date of the movement
            
        Returns:
            InventoryMovementResponse: Created movement record
        """
        # Validate product exists
        product = await Product.get(product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found"
            )

        # Validate quantity based on movement type
        if movement_type in [MovementType.RECEIPT]:
            if quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quantity must be positive for incoming movements"
                )
        elif movement_type in [MovementType.USAGE, MovementType.EXPIRED, MovementType.LOSS]:
            if quantity >= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Quantity must be negative for outgoing movements"
                )

        # Create the movement record
        movement = InventoryMovement(
            movement_type=movement_type,
            product_id=product_id,
            institution_id=institution_id,
            storage_location=storage_location,
            quantity=quantity,
            unit=unit,
            lot=lot,
            expiration_date=expiration_date,
            reference_id=reference_id,
            reference_type=reference_type,
            movement_date=movement_date or datetime.utcnow(),
            notes=notes,
            created_by=created_by,
        )
        
        await movement.insert()
        
        return InventoryMovementResponse(**movement.model_dump())

    @staticmethod
    async def create_receipt_movement(
        product_id: PydanticObjectId,
        institution_id: int,
        quantity: float,
        unit: str = "kg",
        storage_location: Optional[str] = None,
        lot: Optional[str] = None,
        expiration_date: Optional[datetime] = None,
        reference_id: Optional[PydanticObjectId] = None,
        created_by: str = "system",
        notes: Optional[str] = None,
    ) -> InventoryMovementResponse:
        """
        Create a receipt movement (incoming stock).
        
        This is a convenience method for creating RECEIPT movements.
        """
        return await InventoryMovementService.create_movement(
            movement_type=MovementType.RECEIPT,
            product_id=product_id,
            institution_id=institution_id,
            quantity=abs(quantity),  # Ensure positive quantity
            unit=unit,
            storage_location=storage_location,
            lot=lot,
            expiration_date=expiration_date,
            reference_id=reference_id,
            reference_type="ingredient_receipt",
            created_by=created_by,
            notes=notes,
        )

    @staticmethod
    async def get_movements_by_product(
        product_id: PydanticObjectId,
        institution_id: Optional[int] = None,
        movement_type: Optional[MovementType] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[InventoryMovementResponse]:
        """
        Get inventory movements for a specific product.
        
        Args:
            product_id: ID of the product
            institution_id: Optional institution filter (integer)
            movement_type: Optional movement type filter
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of inventory movements
        """
        query = {"product_id": product_id, "deleted_at": None}
        
        if institution_id:
            query["institution_id"] = institution_id
            
        if movement_type:
            query["movement_type"] = movement_type
            
        movements = await InventoryMovement.find(query).sort("-movement_date").skip(offset).limit(limit).to_list()
        
        return [InventoryMovementResponse(**movement.model_dump()) for movement in movements]

    @staticmethod
    async def get_current_stock(
        product_id: PydanticObjectId,
        institution_id: int,
        storage_location: Optional[str] = None,
        lot: Optional[str] = None,
    ) -> float:
        """
        Calculate current stock level based on movements.
        
        Args:
            product_id: ID of the product
            institution_id: ID of the institution (integer)
            storage_location: Optional storage location filter
            lot: Optional lot filter
            
        Returns:
            Current stock level
        """
        query = {
            "product_id": product_id,
            "institution_id": institution_id,
            "deleted_at": None,
        }
        
        if storage_location:
            query["storage_location"] = storage_location
            
        if lot:
            query["lot"] = lot
            
        movements = await InventoryMovement.find(query).to_list()
        
        # Sum all movements (positive for incoming, negative for outgoing)
        total_quantity = sum(movement.quantity for movement in movements)
        
        return max(0, total_quantity)  # Ensure non-negative stock

    @staticmethod
    async def consume_inventory_fifo(
        consumption_request: InventoryConsumptionRequest
    ) -> InventoryConsumptionResponse:
        """
        Consume inventory using FIFO (First-In, First-Out) logic.
        
        This method:
        1. Finds all available batches for the product
        2. Sorts them by date of admission (oldest first)
        3. Consumes from oldest batches first
        4. Validates that total available stock is sufficient
        5. Creates inventory movement records for each batch consumed
        6. Updates the remaining weight in inventory batches
        
        Args:
            consumption_request: Details of the consumption request
            
        Returns:
            InventoryConsumptionResponse: Details of the consumption operation
            
        Raises:
            HTTPException: If insufficient stock or other validation errors
        """
        # Generate unique transaction ID
        transaction_id = str(uuid.uuid4())
        
        # Validate product exists
        product = await Product.get(consumption_request.product_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {consumption_request.product_id} not found"
            )
        
        # Find available inventory batches with FIFO ordering
        available_batches = await InventoryMovementService._get_available_batches_fifo(
            product_id=consumption_request.product_id,
            institution_id=consumption_request.institution_id,
            storage_location=consumption_request.storage_location,
        )
        
        # Calculate total available stock
        total_available = sum(batch.remaining_weight for batch in available_batches)
        
        # Validate sufficient stock
        if total_available < consumption_request.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock. Requested: {consumption_request.quantity} {consumption_request.unit}, Available: {total_available} {consumption_request.unit}"
            )
        
        # Perform FIFO consumption
        remaining_to_consume = consumption_request.quantity
        batch_details = []
        movement_ids = []
        consumption_date = consumption_request.consumption_date or datetime.utcnow()
        
        for batch in available_batches:
            if remaining_to_consume <= 0:
                break
                
            # Calculate how much to consume from this batch
            consume_from_batch = min(remaining_to_consume, batch.remaining_weight)
            
            # Update batch remaining weight
            batch.remaining_weight -= consume_from_batch
            batch.updated_at = datetime.utcnow()
            await batch.save()
            
            # Create movement record for this batch consumption
            movement = await InventoryMovementService.create_movement(
                movement_type=MovementType.USAGE,
                product_id=consumption_request.product_id,
                institution_id=consumption_request.institution_id,
                quantity=-consume_from_batch,  # Negative for outgoing
                unit=consumption_request.unit,
                storage_location=consumption_request.storage_location,
                lot=batch.lot,
                expiration_date=batch.expiration_date,
                reference_id=None,  # Could be linked to a consumption order/recipe
                reference_type="inventory_consumption",
                notes=f"FIFO consumption - {consumption_request.reason}. Transaction ID: {transaction_id}. {consumption_request.notes or ''}",
                created_by=consumption_request.consumed_by,
                movement_date=consumption_date,
            )
            
            movement_ids.append(movement.id)
            
            # Record batch consumption details
            batch_detail = BatchConsumptionDetail(
                inventory_id=batch.id,
                lot=batch.lot,
                consumed_quantity=consume_from_batch,
                remaining_quantity=batch.remaining_weight,
                expiration_date=batch.expiration_date,
                date_of_admission=batch.date_of_admission,
            )
            batch_details.append(batch_detail)
            
            # Update remaining quantity to consume
            remaining_to_consume -= consume_from_batch
        
        # Create response
        response = InventoryConsumptionResponse(
            transaction_id=transaction_id,
            product_id=consumption_request.product_id,
            institution_id=consumption_request.institution_id,
            storage_location=consumption_request.storage_location,
            total_quantity_consumed=consumption_request.quantity,
            unit=consumption_request.unit,
            consumption_date=consumption_date,
            reason=consumption_request.reason,
            notes=consumption_request.notes,
            consumed_by=consumption_request.consumed_by,
            batch_details=batch_details,
            movement_ids=movement_ids,
            created_at=datetime.utcnow(),
        )
        
        return response

    @staticmethod
    async def _get_available_batches_fifo(
        product_id: PydanticObjectId,
        institution_id: int,
        storage_location: Optional[str] = None,
    ) -> List[Inventory]:
        """
        Get available inventory batches ordered by FIFO (date of admission).
        
        Args:
            product_id: ID of the product
            institution_id: ID of the institution
            storage_location: Optional storage location filter
            
        Returns:
            List of inventory batches ordered by date of admission (oldest first)
        """
        query = {
            "product_id": product_id,
            "institution_id": institution_id,
            "remaining_weight": {"$gt": 0},  # Only batches with remaining stock
            "deleted_at": None,
        }
        
        if storage_location:
            query["storage_location"] = storage_location
        
        # Order by date of admission (FIFO - oldest first)
        batches = await Inventory.find(query).sort("date_of_admission").to_list()
        
        return batches

    @staticmethod
    async def get_available_stock_summary(
        product_id: PydanticObjectId,
        institution_id: int,
        storage_location: Optional[str] = None,
    ) -> dict:
        """
        Get summary of available stock for a product.
        
        Args:
            product_id: ID of the product
            institution_id: ID of the institution
            storage_location: Optional storage location filter
            
        Returns:
            Dictionary with stock summary information
        """
        batches = await InventoryMovementService._get_available_batches_fifo(
            product_id=product_id,
            institution_id=institution_id,
            storage_location=storage_location,
        )
        
        total_stock = sum(batch.remaining_weight for batch in batches)
        batch_count = len(batches)
        
        # Find oldest and newest batches
        oldest_batch = batches[0] if batches else None
        newest_batch = batches[-1] if batches else None
        
        return {
            "product_id": product_id,
            "institution_id": institution_id,
            "storage_location": storage_location,
            "total_available_stock": total_stock,
            "number_of_batches": batch_count,
            "oldest_batch_date": oldest_batch.date_of_admission if oldest_batch else None,
            "newest_batch_date": newest_batch.date_of_admission if newest_batch else None,
            "batches": [
                {
                    "inventory_id": batch.id,
                    "lot": batch.lot,
                    "remaining_weight": batch.remaining_weight,
                    "date_of_admission": batch.date_of_admission,
                    "expiration_date": batch.expiration_date,
                }
                for batch in batches
            ],
        }


# Create service instance
inventory_movement_service = InventoryMovementService() 