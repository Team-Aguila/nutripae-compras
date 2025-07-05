from fastapi import HTTPException, status
from ..models import (
    IngredientReceipt,
    IngredientReceiptCreate,
    IngredientReceiptResponse,
    Inventory,
    Product,
    PurchaseOrder,
    OrderStatus,
)


class IngredientReceiptService:
    @staticmethod
    async def register_ingredient_receipt(
        receipt_data: IngredientReceiptCreate, created_by: str
    ) -> IngredientReceiptResponse:
        """
        Registers an ingredient receipt and updates inventory.
        - Validates input data.
        - Creates an IngredientReceipt document.
        - For each item in the receipt, creates an Inventory document.
        - Optionally updates the status of the related Purchase Order.
        """
        if not receipt_data.items:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ingredient receipt must have at least one item.",
            )

        # Validate that all products exist
        for item in receipt_data.items:
            product = await Product.get(item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with id {item.product_id} not found.",
                )

        # Create the ingredient receipt
        new_receipt = IngredientReceipt(
            **receipt_data.model_dump(),
            created_by=created_by,
        )
        await new_receipt.insert()

        # Create inventory items for each received item
        for item in receipt_data.items:
            inventory_item = Inventory(
                product_id=item.product_id,
                institution_id=receipt_data.institution_id,
                remaining_weight=item.quantity,  # Assuming quantity is in weight
                date_of_admission=receipt_data.receipt_date,
                lot=item.lot,
                expiration_date=item.expiration_date,
                minimum_threshold=0,  # Default threshold, can be updated later
            )
            await inventory_item.insert()

        # If linked to a purchase order, update its status
        if receipt_data.purchase_order_id:
            po = await PurchaseOrder.get(receipt_data.purchase_order_id)
            if po:
                # This is a simplified logic. A real-world scenario would
                # compare received quantities with ordered quantities
                # to set PARTIALLY_RECEIVED or COMPLETED.
                # For now, we'll just mark it as COMPLETED.
                po.status = OrderStatus.COMPLETED
                await po.save()

        return IngredientReceiptResponse(**new_receipt.model_dump())


ingredient_receipt_service = IngredientReceiptService() 