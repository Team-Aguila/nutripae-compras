from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List
from beanie import PydanticObjectId

from ..models import (
    ProductCreate,
    ProductUpdate,
    ProductResponse,
    ProductListResponse,
    ShrinkageFactorUpdate,
)
from ..services import product_service
from ..services.product_service import ProductService

router = APIRouter()


@router.post(
    "/",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Product",
    description="Create a new product with validation against the Product model.",
)
async def create_product(
    product_data: ProductCreate,
    service: ProductService = Depends(lambda: product_service),
) -> ProductResponse:
    """
    Create a new product.

    **Request Body:**
    - **provider_id**: The ID of the provider for this product
    - **name**: Name of the product (1-200 characters)
    - **weight**: Default or standard weight (must be > 0, e.g., in kg)
    - **weekly_availability**: Day of the week when the product is available (MONDAY-SUNDAY)
    - **life_time**: Object containing:
      - **value**: Life time value (must be > 0)
      - **unit**: Life time unit (e.g., 'days', 'weeks', 'months')

    **Response:**
    Returns the newly created product object with a 201 Created status code.
    The created_at field is automatically set to the current UTC time.

    **Error Responses:**
    - **422 Unprocessable Entity**: Validation errors in the request body
    - **500 Internal Server Error**: Server error during creation
    """
    # In a real application, created_by would come from an authentication dependency
    created_by = "inventory_manager_test"
    
    # Convert to dict for service call
    product_dict = product_data.model_dump()
    
    created_product = await service.create_product(product_dict, created_by)
    return ProductResponse(**created_product.model_dump())


@router.get(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Get Product by ID",
    description="Retrieve a single, non-deleted product by its ID.",
)
async def get_product(
    product_id: PydanticObjectId,
    service: ProductService = Depends(lambda: product_service),
) -> ProductResponse:
    """
    Retrieve a single product by its ID.

    **Parameters:**
    - **product_id**: The unique ID of the product to retrieve

    **Response:**
    Returns the product object with a 200 OK status.

    **Error Responses:**
    - **404 Not Found**: Product not found or has been soft-deleted
    """
    product = await service.get_product_by_id(product_id)
    return ProductResponse(**product.model_dump())


@router.get(
    "/",
    response_model=ProductListResponse,
    summary="Get All Products",
    description="Retrieve a list of all products that have not been soft-deleted with filtering and pagination.",
)
async def get_products(
    provider_id: Optional[PydanticObjectId] = Query(
        default=None, description="Filter by provider ID"
    ),
    limit: int = Query(
        default=100, le=1000, description="Maximum number of products to return"
    ),
    offset: int = Query(
        default=0, ge=0, description="Number of products to skip for pagination"
    ),
    service: ProductService = Depends(lambda: product_service),
) -> ProductListResponse:
    """
    Retrieve a list of all non-deleted products.

    **Query Parameters:**
    - **provider_id**: (Optional) Filter products by specific provider
    - **limit**: Maximum number of products to return (default: 100, max: 1000)
    - **offset**: Number of products to skip for pagination (default: 0)

    **Features:**
    - **Filtering**: Filter by provider_id to see products from specific suppliers
    - **Pagination**: Use limit and offset for pagination
    - **Soft Delete Aware**: Only returns non-deleted products (deleted_at is null)

    **Response:**
    Returns a list of products with pagination information and a 200 OK status.

    **Use Cases:**
    - Browse product catalog
    - Filter products by provider
    - Paginate through large product lists
    """
    # Get products and total count
    products = await service.get_products(provider_id, limit, offset)
    total_count = await service.count_products(provider_id)
    
    # Convert products to response models
    product_responses = [ProductResponse(**product.model_dump()) for product in products]
    
    # Calculate pagination info
    page_info = {
        'current_page': (offset // limit) + 1,
        'page_size': limit,
        'total_pages': (total_count + limit - 1) // limit,
        'has_next': offset + limit < total_count,
        'has_previous': offset > 0
    }
    
    return ProductListResponse(
        products=product_responses,
        total_count=total_count,
        page_info=page_info
    )


@router.put(
    "/{product_id}",
    response_model=ProductResponse,
    summary="Update Product",
    description="Update a product. The provider_id is considered immutable and cannot be changed.",
)
async def update_product(
    product_id: PydanticObjectId,
    product_data: ProductUpdate,
    service: ProductService = Depends(lambda: product_service),
) -> ProductResponse:
    """
    Update a product by its ID.

    **Parameters:**
    - **product_id**: The unique ID of the product to update

    **Request Body (all fields are optional):**
    - **name**: New name of the product (1-200 characters)
    - **weight**: New default or standard weight (must be > 0)
    - **weekly_availability**: New day of availability (MONDAY-SUNDAY)
    - **life_time**: New life time object with value and unit

    **Important Notes:**
    - **provider_id is immutable**: Cannot be changed after product creation
    - Only provided fields will be updated
    - **updated_at** field is automatically set to current UTC timestamp

    **Response:**
    Returns the updated product object with a 200 OK status.

    **Error Responses:**
    - **404 Not Found**: Product not found or has been soft-deleted
    - **422 Unprocessable Entity**: Validation errors in the request body
    - **500 Internal Server Error**: Server error during update
    """
    # In a real application, updated_by would come from an authentication dependency
    updated_by = "inventory_manager_test"
    
    # Convert to dict and exclude None values
    update_dict = product_data.model_dump(exclude_none=True)
    
    updated_product = await service.update_product(product_id, update_dict, updated_by)
    return ProductResponse(**updated_product.model_dump())


@router.delete(
    "/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Product (Soft Delete)",
    description="Soft delete a product. The product is not removed from the database but marked as deleted.",
)
async def delete_product(
    product_id: PydanticObjectId,
    service: ProductService = Depends(lambda: product_service),
):
    """
    Soft delete a product by its ID.

    **Parameters:**
    - **product_id**: The unique ID of the product to delete

    **Soft Delete Behavior:**
    - The product document is **NOT removed** from the database
    - The **deleted_at** field is set to the current UTC timestamp
    - The **updated_at** field is also updated to current UTC timestamp
    - Deleted products will not appear in GET requests

    **Response:**
    Returns a 204 No Content status on successful deletion.

    **Error Responses:**
    - **404 Not Found**: Product not found or already deleted
    - **500 Internal Server Error**: Server error during deletion

    **Use Cases:**
    - Remove products from active catalog while preserving data
    - Maintain audit trail and referential integrity
    - Allow for potential product restoration in the future
    """
    # In a real application, deleted_by would come from an authentication dependency
    deleted_by = "inventory_manager_test"
    
    await service.delete_product(product_id, deleted_by)
    # FastAPI automatically returns 204 No Content for None return with the decorator 


@router.patch(
    "/{product_id}/shrinkage",
    response_model=ProductResponse,
    status_code=status.HTTP_200_OK,
    summary="Update Product Shrinkage Factor",
    description="Update the shrinkage factor for a specific product to account for processing losses.",
)
async def update_product_shrinkage_factor(
    product_id: PydanticObjectId,
    shrinkage_data: ShrinkageFactorUpdate,
    service: ProductService = Depends(lambda: product_service),
) -> ProductResponse:
    """
    Update the shrinkage factor for a specific product.

    **Parameters:**
    - **product_id**: The unique ID of the product to update

    **Request Body:**
    - **shrinkage_factor**: Loss factor between 0.0 and 1.0 (e.g., 0.15 for 15% loss)

    **Shrinkage Factor Explanation:**
    The shrinkage factor accounts for predictable processing losses such as:
    - Peeling vegetables (potato skins, onion layers)
    - Cooking losses (water evaporation, fat rendering)
    - Trimming waste (fat removal, damaged portions)
    - General handling losses

    **Calculation Formula:**
    ```
    gross_quantity_needed = net_quantity_needed * (1 + shrinkage_factor)
    ```

    **Examples:**
    - If 1kg of peeled potatoes is needed (net) and shrinkage factor is 0.20 (20%), 
      the system will calculate 1.2kg of raw potatoes needed (gross)
    - For 500g of trimmed meat with 0.15 (15%) shrinkage, 
      575g of raw meat should be ordered

    **Response:**
    Returns the updated product object with new shrinkage factor and 200 OK status.

    **Error Responses:**
    - **404 Not Found**: Product not found or has been soft-deleted
    - **422 Unprocessable Entity**: Invalid shrinkage factor (must be 0.0-1.0)
    - **500 Internal Server Error**: Server error during update

    **Use Cases:**
    - Set initial shrinkage factors for new products
    - Adjust factors based on historical loss data
    - Account for seasonal variations in product quality
    - Optimize purchasing to reduce waste
    """
    # In a real application, updated_by would come from an authentication dependency
    updated_by = "inventory_manager_test"
    
    updated_product = await service.update_shrinkage_factor(
        product_id, 
        shrinkage_data.shrinkage_factor, 
        updated_by
    )
    return ProductResponse(**updated_product.model_dump()) 