from fastapi import HTTPException, status
from datetime import datetime
from typing import List, Dict, Any
from beanie import PydanticObjectId

from models import (
    IngredientReceipt,
    IngredientReceiptCreate,
    IngredientReceiptResponse,
    Inventory,
    Product,
    PurchaseOrder,
    OrderStatus,
    InventoryMovement,
    MovementType,
)
from .inventory_movement_service import inventory_movement_service


class IngredientReceiptService:
    @staticmethod
    async def register_ingredient_receipt(
        receipt_data: IngredientReceiptCreate, created_by: str
    ) -> IngredientReceiptResponse:
        """
        Registers an ingredient receipt with comprehensive inventory and movement tracking.
        
        Features:
        - Validates input data and product existence
        - Creates an IngredientReceipt document
        - Creates inventory items with proper unit and storage location handling
        - Creates inventory movement records for audit trail
        - Updates purchase order status based on actual receipt completion
        - Handles partial receipts properly
        
        Args:
            receipt_data: The ingredient receipt data
            created_by: User who created the receipt
            
        Returns:
            IngredientReceiptResponse: The created receipt
        """
        if not receipt_data.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ingredient receipt must have at least one item.",
            )

        # Validate that all products exist
        product_info = {}
        for item in receipt_data.items:
            product = await Product.get(item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {item.product_id} not found.",
                )
            product_info[item.product_id] = product

        # If linked to a purchase order, validate it exists
        purchase_order = None
        if receipt_data.purchase_order_id:
            purchase_order = await PurchaseOrder.get(receipt_data.purchase_order_id)
            if not purchase_order:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Purchase order with id {receipt_data.purchase_order_id} not found.",
                )

        # Create the ingredient receipt
        new_receipt = IngredientReceipt(
            **receipt_data.model_dump(),
            created_by=created_by,
        )
        await new_receipt.insert()

        # Process each received item
        for item in receipt_data.items:
            # Create inventory item
            inventory_item = Inventory(
                product_id=item.product_id,
                institution_id=receipt_data.institution_id,  # Now uses int
                remaining_weight=item.quantity,
                unit=item.unit,
                storage_location=item.storage_location,
                date_of_admission=datetime.combine(receipt_data.receipt_date, datetime.min.time()),
                lot=item.lot,
                expiration_date=item.expiration_date,
                batch_number=item.lot,  # Use lot as batch number for FIFO tracking
                initial_weight=item.quantity,  # Set initial weight to received quantity
                minimum_threshold=0,  # Default threshold, can be updated later
            )
            await inventory_item.insert()

            # Create inventory movement record for audit trail
            await inventory_movement_service.create_receipt_movement(
                product_id=item.product_id,
                institution_id=receipt_data.institution_id,  # Now uses int
                quantity=item.quantity,
                unit=item.unit,
                storage_location=item.storage_location,
                lot=item.lot,
                expiration_date=datetime.combine(item.expiration_date, datetime.min.time()),
                reference_id=new_receipt.id,
                created_by=created_by,
                notes=f"Receipt from {receipt_data.delivery_person_name}",
            )

        # Update purchase order status if applicable
        if purchase_order:
            await IngredientReceiptService._update_purchase_order_status(
                purchase_order, receipt_data.items
            )

        # Convert ObjectIds to strings for response model
        receipt_dict = new_receipt.model_dump()
        receipt_dict["id"] = str(new_receipt.id)
        if receipt_dict.get("purchase_order_id"):
            receipt_dict["purchase_order_id"] = str(receipt_dict["purchase_order_id"])
        
        # Convert product_ids in items to strings
        for item in receipt_dict.get("items", []):
            if item.get("product_id"):
                item["product_id"] = str(item["product_id"])
        
        return IngredientReceiptResponse(**receipt_dict)

    @staticmethod
    async def _update_purchase_order_status(
        purchase_order: PurchaseOrder, received_items: List[Any]
    ) -> None:
        """
        Update purchase order status based on received items.
        
        This method compares received quantities with ordered quantities
        to determine if the order is partially received or completed.
        
        Args:
            purchase_order: The purchase order to update
            received_items: List of received items
        """
        # Create a map of received quantities by product
        received_quantities = {}
        for item in received_items:
            product_id = item.product_id
            if product_id in received_quantities:
                received_quantities[product_id] += item.quantity
            else:
                received_quantities[product_id] = item.quantity

        # Check if all items have been fully received
        all_received = True
        any_received = False
        
        for line_item in purchase_order.line_items:
            product_id = line_item.product_id
            ordered_quantity = line_item.quantity
            received_quantity = received_quantities.get(product_id, 0)
            
            if received_quantity > 0:
                any_received = True
                
            if received_quantity < ordered_quantity:
                all_received = False

        # Update status based on receipt completion
        if all_received:
            purchase_order.status = OrderStatus.COMPLETED
        elif any_received:
            purchase_order.status = OrderStatus.SHIPPED  # Partially received
        
        purchase_order.updated_at = datetime.utcnow()
        await purchase_order.save()

    @staticmethod
    async def get_receipt_by_id(receipt_id: PydanticObjectId) -> IngredientReceiptResponse:
        """
        Get an ingredient receipt by ID.
        
        Args:
            receipt_id: The ID of the receipt
            
        Returns:
            IngredientReceiptResponse: The receipt data
        """
        receipt = await IngredientReceipt.get(receipt_id)
        if not receipt:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Receipt with id {receipt_id} not found.",
            )
        
        # Convert ObjectIds to strings for response model
        receipt_dict = receipt.model_dump()
        receipt_dict["id"] = str(receipt.id)
        if receipt_dict.get("purchase_order_id"):
            receipt_dict["purchase_order_id"] = str(receipt_dict["purchase_order_id"])
        
        # Convert product_ids in items to strings
        for item in receipt_dict.get("items", []):
            if item.get("product_id"):
                item["product_id"] = str(item["product_id"])
        
        return IngredientReceiptResponse(**receipt_dict)

    @staticmethod
    async def get_receipts_by_institution(
        institution_id: int,  # Now uses int
        limit: int = 100,
        offset: int = 0,
    ) -> List[IngredientReceiptResponse]:
        """
        Get ingredient receipts for a specific institution.
        
        Args:
            institution_id: The institution ID (integer)
            limit: Maximum number of receipts to return
            offset: Number of receipts to skip
            
        Returns:
            List of ingredient receipts
        """
        receipts = await IngredientReceipt.find(
            {"institution_id": institution_id}
        ).sort("-created_at").skip(offset).limit(limit).to_list()
        
        # Convert ObjectIds to strings for response models
        result = []
        for receipt in receipts:
            receipt_dict = receipt.model_dump()
            receipt_dict["id"] = str(receipt.id)
            if receipt_dict.get("purchase_order_id"):
                receipt_dict["purchase_order_id"] = str(receipt_dict["purchase_order_id"])
            
            # Convert product_ids in items to strings
            for item in receipt_dict.get("items", []):
                if item.get("product_id"):
                    item["product_id"] = str(item["product_id"])
            
            result.append(IngredientReceiptResponse(**receipt_dict))
        
        return result


ingredient_receipt_service = IngredientReceiptService() 