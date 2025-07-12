from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from beanie import PydanticObjectId

from models import Product


class ProductService:
    """Service for managing product CRUD operations"""

    @staticmethod
    async def create_product(product_data: dict, created_by: str = "system") -> Product:
        """
        Create a new product.
        
        Args:
            product_data: Dictionary containing product data
            created_by: User who created the product
            
        Returns:
            Product: Created product
            
        Raises:
            HTTPException: If validation fails or creation fails
        """
        # Create the product with current timestamp
        new_product = Product(
            **product_data,
            created_at=datetime.utcnow(),
            updated_at=None,
            deleted_at=None,
        )
        
        try:
            await new_product.insert()
            return new_product
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create product: {str(e)}"
            )

    @staticmethod
    async def get_product_by_id(product_id: PydanticObjectId) -> Product:
        """
        Get a product by its ID (only non-deleted products).
        
        Args:
            product_id: The ID of the product
            
        Returns:
            Product: The product if found and not deleted
            
        Raises:
            HTTPException: If product not found or deleted
        """
        product = await Product.get(product_id)
        
        if not product or product.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product with id {product_id} not found or has been deleted"
            )
        
        return product

    @staticmethod
    async def get_products(
        provider_id: Optional[PydanticObjectId] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Product]:
        """
        Get a list of products (only non-deleted products).
        
        Args:
            provider_id: Optional filter by provider ID
            limit: Maximum number of products to return
            offset: Number of products to skip
            
        Returns:
            List[Product]: List of products
        """
        # Build query for non-deleted products
        query = {"deleted_at": None}
        
        if provider_id:
            query["provider_id"] = provider_id
        
        products = await Product.find(query).sort("-created_at").skip(offset).limit(limit).to_list()
        
        return products

    @staticmethod
    async def update_product(
        product_id: PydanticObjectId,
        update_data: dict,
        updated_by: str = "system"
    ) -> Product:
        """
        Update a product (only non-deleted products).
        
        Args:
            product_id: The ID of the product to update
            update_data: Dictionary containing fields to update
            updated_by: User who updated the product
            
        Returns:
            Product: Updated product
            
        Raises:
            HTTPException: If product not found, deleted, or update fails
        """
        # Get the product first to ensure it exists and is not deleted
        product = await ProductService.get_product_by_id(product_id)
        
        # Update fields (excluding immutable fields like provider_id, created_at, etc.)
        allowed_fields = ["name", "weight", "weekly_availability", "life_time", "shrinkage_factor"]
        
        for field, value in update_data.items():
            if field in allowed_fields and value is not None:
                setattr(product, field, value)
        
        # Set updated timestamp
        product.updated_at = datetime.utcnow()
        
        try:
            await product.save()
            return product
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update product: {str(e)}"
            )

    @staticmethod
    async def delete_product(product_id: PydanticObjectId, deleted_by: str = "system") -> bool:
        """
        Soft delete a product.
        
        Args:
            product_id: The ID of the product to delete
            deleted_by: User who deleted the product
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            HTTPException: If product not found or already deleted
        """
        # Get the product first to ensure it exists and is not already deleted
        product = await ProductService.get_product_by_id(product_id)
        
        # Perform soft delete
        product.deleted_at = datetime.utcnow()
        product.updated_at = datetime.utcnow()
        
        try:
            await product.save()
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete product: {str(e)}"
            )

    @staticmethod
    async def update_shrinkage_factor(
        product_id: PydanticObjectId,
        shrinkage_factor: float,
        updated_by: str = "system"
    ) -> Product:
        """
        Update the shrinkage factor for a specific product.
        
        Args:
            product_id: The ID of the product to update
            shrinkage_factor: New shrinkage factor value (0.0 to 1.0)
            updated_by: User who updated the product
            
        Returns:
            Product: Updated product
            
        Raises:
            HTTPException: If product not found, deleted, or update fails
        """
        # Validate shrinkage factor range
        if not (0.0 <= shrinkage_factor <= 1.0):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Shrinkage factor must be between 0.0 and 1.0"
            )
        
        # Get the product first to ensure it exists and is not deleted
        product = await ProductService.get_product_by_id(product_id)
        
        # Update shrinkage factor
        product.shrinkage_factor = shrinkage_factor
        product.updated_at = datetime.utcnow()
        
        try:
            await product.save()
            return product
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update product shrinkage factor: {str(e)}"
            )

    @staticmethod
    async def count_products(provider_id: Optional[PydanticObjectId] = None) -> int:
        """
        Count the total number of non-deleted products.
        
        Args:
            provider_id: Optional filter by provider ID
            
        Returns:
            int: Total count of products
        """
        query = {"deleted_at": None}
        
        if provider_id:
            query["provider_id"] = provider_id
        
        return await Product.find(query).count()


# Create service instance
product_service = ProductService() 