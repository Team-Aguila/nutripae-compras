from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from beanie import PydanticObjectId

from ..models import (
    InventoryMovement,
    MovementType,
    InventoryMovementResponse,
    Inventory,
    Product,
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


# Create service instance
inventory_movement_service = InventoryMovementService() 