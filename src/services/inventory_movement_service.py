from datetime import datetime, time
from typing import List, Optional
from fastapi import HTTPException, status
from beanie import PydanticObjectId
import uuid

from models import (
    InventoryMovement,
    MovementType,
    InventoryMovementResponse,
    Inventory,
    Product,
    InventoryConsumptionRequest,
    InventoryConsumptionResponse,
    BatchConsumptionDetail,
    InventoryReceiptRequest,
    InventoryReceiptResponse,
    ManualInventoryAdjustmentRequest,
    ManualInventoryAdjustmentResponse,
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
        
        # Convert ObjectIds to strings for response model
        movement_dict = movement.model_dump()
        movement_dict["id"] = str(movement.id)
        movement_dict["product_id"] = str(movement.product_id)
        if movement_dict.get("reference_id"):
            movement_dict["reference_id"] = str(movement_dict["reference_id"])
        
        return InventoryMovementResponse(**movement_dict)

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
        
        # Convert ObjectIds to strings for response models
        result = []
        for movement in movements:
            movement_dict = movement.model_dump()
            movement_dict["id"] = str(movement.id)
            movement_dict["product_id"] = str(movement.product_id)
            if movement_dict.get("reference_id"):
                movement_dict["reference_id"] = str(movement_dict["reference_id"])
            result.append(InventoryMovementResponse(**movement_dict))
        
        return result

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
        
        # Convert string product_id to PydanticObjectId for database operations
        try:
            product_object_id = PydanticObjectId(consumption_request.product_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid product_id format: {consumption_request.product_id}"
            )
        
        # Validate product exists
        product = await Product.get(product_object_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {consumption_request.product_id} not found"
            )
        
        # Find available inventory batches with FIFO ordering
        available_batches = await InventoryMovementService._get_available_batches_fifo(
            product_id=product_object_id,
            institution_id=consumption_request.institution_id,
            storage_location=consumption_request.storage_location,
        )
        
        # Calculate total available stock
        total_available = sum(batch.remaining_weight for batch in available_batches)
        
        # Validate sufficient stock (User Story 2 requirement)
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
            
            # Update batch remaining weight (allow zero to handle complete consumption)
            new_remaining_weight = batch.remaining_weight - consume_from_batch
            batch.remaining_weight = max(0.0, new_remaining_weight)  # Ensure non-negative
            batch.updated_at = datetime.utcnow()
            
            # Save batch with proper error handling
            try:
                await batch.save()
            except Exception as e:
                # If save fails, this is a critical error that should stop the transaction
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Failed to update inventory batch {batch.id} remaining weight: {str(e)}"
                )
            
            # Create movement record for this batch consumption
            # Convert date to datetime if needed
            batch_expiration_datetime = None
            if batch.expiration_date:
                if isinstance(batch.expiration_date, datetime):
                    batch_expiration_datetime = batch.expiration_date
                else:
                    # Convert date to datetime at midnight
                    from datetime import date, time
                    if isinstance(batch.expiration_date, date):
                        batch_expiration_datetime = datetime.combine(batch.expiration_date, time.min)
            
            movement = await InventoryMovementService.create_movement(
                movement_type=MovementType.USAGE,
                product_id=product_object_id,
                institution_id=consumption_request.institution_id,
                quantity=-consume_from_batch,  # Negative for outgoing
                unit=consumption_request.unit,
                storage_location=consumption_request.storage_location,
                lot=batch.lot,
                expiration_date=batch_expiration_datetime,
                reference_id=None,  # Could be linked to a consumption order/recipe
                reference_type="inventory_consumption",
                notes=f"FIFO consumption - {consumption_request.reason}. Transaction ID: {transaction_id}. {consumption_request.notes or ''}",
                created_by=consumption_request.consumed_by,
                movement_date=consumption_date,
            )
            
            movement_ids.append(str(movement.id))
            
            # Record batch consumption details
            batch_detail = BatchConsumptionDetail(
                inventory_id=str(batch.id),
                lot=batch.lot,
                consumed_quantity=consume_from_batch,
                remaining_quantity=batch.remaining_weight,
                expiration_date=batch_expiration_datetime,
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
    async def receive_inventory(
        receipt_request: InventoryReceiptRequest
    ) -> InventoryReceiptResponse:
        """
        Receive inventory and create new batch (User Story 1).
        
        This method:
        1. Validates the product exists
        2. Creates a new inventory batch record
        3. Creates a credit (+) movement in the immutable ledger
        4. Returns detailed receipt information
        
        Args:
            receipt_request: Details of the inventory receipt
            
        Returns:
            InventoryReceiptResponse: Details of the receipt operation
            
        Raises:
            HTTPException: If validation errors or product not found
        """
        # Generate unique transaction ID
        transaction_id = str(uuid.uuid4())
        
        # Convert string product_id to PydanticObjectId for database operations
        try:
            product_object_id = PydanticObjectId(receipt_request.product_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid product_id format: {receipt_request.product_id}"
            )
        
        # Validate product exists
        product = await Product.get(product_object_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {receipt_request.product_id} not found"
            )
        
        # Validate storage location is provided
        if not receipt_request.storage_location or receipt_request.storage_location.strip() == "":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Storage location is required and cannot be empty"
            )
        
        # Validate batch number is unique within the same product and institution
        existing_batch = await Inventory.find_one({
            "product_id": product_object_id,
            "institution_id": receipt_request.institution_id,
            "batch_number": receipt_request.batch_number,
            "deleted_at": None
        })
        
        if existing_batch:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Batch number '{receipt_request.batch_number}' already exists for this product at this institution"
            )
        
        # Set reception date
        reception_date = receipt_request.reception_date or datetime.utcnow()
        
        # Create new inventory batch
        inventory_batch = Inventory(
            product_id=product_object_id,
            institution_id=receipt_request.institution_id,
            remaining_weight=receipt_request.quantity_received,
            initial_weight=receipt_request.quantity_received,
            unit=receipt_request.unit_of_measure,
            storage_location=receipt_request.storage_location,
            date_of_admission=reception_date,
            lot=receipt_request.batch_number,  # Use batch_number as lot for consistency
            batch_number=receipt_request.batch_number,
            expiration_date=receipt_request.expiration_date,
            minimum_threshold=0.0,  # Can be updated later via API
        )
        
        # Save the inventory batch
        await inventory_batch.insert()
        
        # Create receipt movement record (credit/positive movement)
        movement = await InventoryMovementService.create_movement(
            movement_type=MovementType.RECEIPT,
            product_id=product_object_id,
            institution_id=receipt_request.institution_id,
            quantity=receipt_request.quantity_received,  # Positive for incoming
            unit=receipt_request.unit_of_measure,
            storage_location=receipt_request.storage_location,
            lot=receipt_request.batch_number,
            expiration_date=datetime.combine(receipt_request.expiration_date, datetime.min.time()),
            reference_id=PydanticObjectId(receipt_request.purchase_order_id) if receipt_request.purchase_order_id else None,
            reference_type="purchase_order" if receipt_request.purchase_order_id else "manual_receipt",
            notes=f"Inventory receipt - Transaction ID: {transaction_id}. {receipt_request.notes or ''}",
            created_by=receipt_request.received_by,
            movement_date=reception_date,
        )
        
        # Create response
        response = InventoryReceiptResponse(
            transaction_id=transaction_id,
            inventory_id=str(inventory_batch.id),
            product_id=receipt_request.product_id,
            institution_id=receipt_request.institution_id,
            storage_location=receipt_request.storage_location,
            quantity_received=receipt_request.quantity_received,
            unit_of_measure=receipt_request.unit_of_measure,
            expiration_date=receipt_request.expiration_date,
            batch_number=receipt_request.batch_number,
            purchase_order_id=receipt_request.purchase_order_id,
            received_by=receipt_request.received_by,
            reception_date=reception_date,
            movement_id=str(movement.id),
            notes=receipt_request.notes,
            created_at=datetime.utcnow(),
        )
        
        return response

    @staticmethod
    async def create_manual_adjustment(
        adjustment_request: ManualInventoryAdjustmentRequest
    ) -> ManualInventoryAdjustmentResponse:
        """
        Create a manual inventory adjustment with comprehensive validation.
        
        This method implements critical business logic:
        - Validates that the inventory batch exists
        - Validates that the product exists
        - Prevents adjustments that would result in negative stock
        - Updates the actual inventory record
        - Creates an audit trail movement record
        
        Args:
            adjustment_request: The adjustment request data
            
        Returns:
            ManualInventoryAdjustmentResponse: Complete adjustment details
            
        Raises:
            HTTPException: For validation errors or business rule violations
        """
        # Convert string IDs to ObjectIds
        try:
            product_obj_id = PydanticObjectId(adjustment_request.product_id)
            inventory_obj_id = PydanticObjectId(adjustment_request.inventory_id)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid product_id or inventory_id format"
            )
        
        # Validate that the product exists
        product = await Product.get(product_obj_id)
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {adjustment_request.product_id} not found"
            )
        
        # Validate that the inventory batch exists and is not deleted
        inventory_batch = await Inventory.get(inventory_obj_id)
        if not inventory_batch or inventory_batch.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inventory batch with id {adjustment_request.inventory_id} not found"
            )
        
        # Validate that the inventory batch belongs to the specified product
        if inventory_batch.product_id != product_obj_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Inventory batch does not belong to the specified product"
            )
        
        # Validate that units match
        if adjustment_request.unit != inventory_batch.unit:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Unit mismatch. Inventory batch uses '{inventory_batch.unit}', adjustment requests '{adjustment_request.unit}'"
            )
        
        # Store original stock level
        previous_stock = inventory_batch.remaining_weight
        
        # Calculate new stock level after adjustment
        new_stock = previous_stock + adjustment_request.quantity
        
        # CRITICAL BUSINESS LOGIC: Prevent negative stock
        if new_stock < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Adjustment would result in negative stock. Current stock: {previous_stock}, "
                       f"adjustment: {adjustment_request.quantity}, resulting stock: {new_stock}"
            )
        
        # Generate transaction ID for traceability
        transaction_id = f"ADJ-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{str(uuid.uuid4())[:8]}"
        adjustment_date = datetime.utcnow()
        
        # Update the inventory batch
        inventory_batch.remaining_weight = new_stock
        inventory_batch.updated_at = adjustment_date
        await inventory_batch.save()
        
        # Create inventory movement record for audit trail
        movement = InventoryMovement(
            movement_type=MovementType.ADJUSTMENT,
            product_id=product_obj_id,
            institution_id=inventory_batch.institution_id,
            storage_location=inventory_batch.storage_location,
            quantity=adjustment_request.quantity,
            unit=adjustment_request.unit,
            lot=inventory_batch.lot,
            expiration_date=datetime.combine(inventory_batch.expiration_date, time.min),
            reference_id=inventory_obj_id,
            reference_type="manual_adjustment",
            movement_date=adjustment_date,
            notes=f"Manual adjustment: {adjustment_request.reason}. {adjustment_request.notes or ''}".strip(),
            created_by=adjustment_request.adjusted_by or "inventory_auditor",
        )
        
        await movement.insert()
        
        # Create response
        return ManualInventoryAdjustmentResponse(
            transaction_id=transaction_id,
            inventory_id=adjustment_request.inventory_id,
            product_id=adjustment_request.product_id,
            institution_id=inventory_batch.institution_id,
            storage_location=inventory_batch.storage_location,
            adjustment_quantity=adjustment_request.quantity,
            unit=adjustment_request.unit,
            reason=adjustment_request.reason,
            notes=adjustment_request.notes,
            adjusted_by=adjustment_request.adjusted_by or "inventory_auditor",
            previous_stock=previous_stock,
            new_stock=new_stock,
            movement_id=str(movement.id),
            adjustment_date=adjustment_date,
            created_at=adjustment_date,
        )

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
    ):
        """
        Get summary of available stock for a product.
        
        Args:
            product_id: ID of the product
            institution_id: ID of the institution
            storage_location: Optional storage location filter
            
        Returns:
            StockSummaryResponse compatible data
        """
        from ..models import StockSummaryResponse, BatchDetail
        
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
        
        # Convert batches to BatchDetail models
        batch_details = [
            BatchDetail(
                inventory_id=str(batch.id),
                lot=batch.lot,
                remaining_weight=batch.remaining_weight,
                date_of_admission=batch.date_of_admission,
                expiration_date=datetime.combine(batch.expiration_date, time.min),
            )
            for batch in batches
        ]
        
        return StockSummaryResponse(
            product_id=str(product_id),
            institution_id=institution_id,
            storage_location=storage_location,
            total_available_stock=total_stock,
            number_of_batches=batch_count,
            oldest_batch_date=oldest_batch.date_of_admission if oldest_batch else None,
            newest_batch_date=newest_batch.date_of_admission if newest_batch else None,
            batches=batch_details,
            unit="kg",
        )


# Create service instance
inventory_movement_service = InventoryMovementService() 