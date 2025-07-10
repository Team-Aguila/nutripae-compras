from fastapi import APIRouter, Depends, Query, status
from typing import Optional, List
from beanie import PydanticObjectId

from ..models import (
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse,
    ProviderListResponse,
)
from ..services import provider_service
from ..services.provider_service import ProviderService

router = APIRouter()


@router.post(
    "/",
    response_model=ProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Provider",
    description="Create a new provider with validation. NIT must be unique.",
)
async def create_provider(
    provider_data: ProviderCreate,
    service: ProviderService = Depends(lambda: provider_service),
) -> ProviderResponse:
    """
    Create a new provider.

    **Request Body:**
    - **name**: Name of the provider (1-200 characters)
    - **nit**: Provider's tax identification number (unique, 1-50 characters)
    - **address**: Physical address of the provider (1-500 characters)
    - **responsible_name**: Name of the primary contact person (1-200 characters)
    - **email**: Contact email (valid email format)
    - **phone_number**: Contact phone number (1-50 characters)
    - **is_local_provider**: Flag to indicate if the provider is local (optional, defaults to true)

    **Response:**
    Returns the newly created provider object with a 201 Created status code.
    The created_at field is automatically set to the current UTC time.

    **Error Responses:**
    - **409 Conflict**: Provider with the given NIT already exists
    - **422 Unprocessable Entity**: Validation errors in the request body
    - **500 Internal Server Error**: Server error during creation
    """
    # In a real application, created_by would come from an authentication dependency
    created_by = "procurement_manager_test"
    
    # Convert to dict for service call
    provider_dict = provider_data.model_dump()
    
    created_provider = await service.create_provider(provider_dict, created_by)
    return ProviderResponse(**created_provider.model_dump())


@router.get(
    "/{provider_id}",
    response_model=ProviderResponse,
    summary="Get Provider by ID",
    description="Retrieve a single, non-deleted provider by its ID.",
)
async def get_provider(
    provider_id: PydanticObjectId,
    service: ProviderService = Depends(lambda: provider_service),
) -> ProviderResponse:
    """
    Retrieve a single provider by its ID.

    **Parameters:**
    - **provider_id**: The unique ID of the provider to retrieve

    **Response:**
    Returns the provider object with a 200 OK status.

    **Error Responses:**
    - **404 Not Found**: Provider not found or has been soft-deleted
    """
    provider = await service.get_provider_by_id(provider_id)
    return ProviderResponse(**provider.model_dump())


@router.get(
    "/",
    response_model=ProviderListResponse,
    summary="Get All Providers",
    description="Retrieve a list of all providers that have not been soft-deleted with filtering and pagination.",
)
async def get_providers(
    is_local_provider: Optional[bool] = Query(
        default=None, description="Filter by local provider flag (true for local, false for non-local)"
    ),
    skip: int = Query(
        default=0, ge=0, description="Number of providers to skip for pagination"
    ),
    limit: int = Query(
        default=100, le=1000, description="Maximum number of providers to return"
    ),
    service: ProviderService = Depends(lambda: provider_service),
) -> ProviderListResponse:
    """
    Retrieve a list of all non-deleted providers.

    **Query Parameters:**
    - **is_local_provider**: (Optional) Filter providers by local flag (true/false)
    - **skip**: Number of providers to skip for pagination (default: 0)
    - **limit**: Maximum number of providers to return (default: 100, max: 1000)

    **Features:**
    - **Filtering**: Filter by is_local_provider to see local or non-local providers
    - **Pagination**: Use skip and limit for pagination
    - **Soft Delete Aware**: Only returns non-deleted providers (deleted_at is null)

    **Response:**
    Returns a list of providers with pagination information and a 200 OK status.

    **Use Cases:**
    - Browse provider catalog
    - Filter providers by local/non-local classification
    - Paginate through large provider lists
    """
    # Get providers and total count
    providers = await service.get_providers(is_local_provider, limit, skip)
    total_count = await service.count_providers(is_local_provider)
    
    # Convert providers to response models
    provider_responses = [ProviderResponse(**provider.model_dump()) for provider in providers]
    
    # Calculate pagination info
    page_info = {
        'current_page': (skip // limit) + 1,
        'page_size': limit,
        'total_pages': (total_count + limit - 1) // limit,
        'has_next': skip + limit < total_count,
        'has_previous': skip > 0
    }
    
    return ProviderListResponse(
        providers=provider_responses,
        total_count=total_count,
        page_info=page_info
    )


@router.put(
    "/{provider_id}",
    response_model=ProviderResponse,
    summary="Update Provider",
    description="Update a provider. The NIT is considered immutable and cannot be changed.",
)
async def update_provider(
    provider_id: PydanticObjectId,
    provider_data: ProviderUpdate,
    service: ProviderService = Depends(lambda: provider_service),
) -> ProviderResponse:
    """
    Update a provider by its ID.

    **Parameters:**
    - **provider_id**: The unique ID of the provider to update

    **Request Body (all fields are optional):**
    - **name**: New name of the provider (1-200 characters)
    - **address**: New physical address (1-500 characters)
    - **responsible_name**: New name of the primary contact person (1-200 characters)
    - **email**: New contact email (valid email format)
    - **phone_number**: New contact phone number (1-50 characters)
    - **is_local_provider**: New local provider flag (true/false)

    **Important Notes:**
    - **NIT is immutable**: Cannot be changed after provider creation
    - Only provided fields will be updated
    - **updated_at** field is automatically set to current UTC timestamp

    **Response:**
    Returns the updated provider object with a 200 OK status.

    **Error Responses:**
    - **404 Not Found**: Provider not found or has been soft-deleted
    - **422 Unprocessable Entity**: Validation errors in the request body
    - **500 Internal Server Error**: Server error during update
    """
    # In a real application, updated_by would come from an authentication dependency
    updated_by = "procurement_manager_test"
    
    # Convert to dict and exclude None values
    update_dict = provider_data.model_dump(exclude_none=True)
    
    updated_provider = await service.update_provider(provider_id, update_dict, updated_by)
    return ProviderResponse(**updated_provider.model_dump())


@router.delete(
    "/{provider_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete Provider (Soft Delete)",
    description="Soft delete a provider. The provider is not removed from the database but marked as deleted.",
)
async def delete_provider(
    provider_id: PydanticObjectId,
    service: ProviderService = Depends(lambda: provider_service),
):
    """
    Soft delete a provider by its ID.

    **Parameters:**
    - **provider_id**: The unique ID of the provider to delete

    **Soft Delete Behavior:**
    - The provider document is **NOT removed** from the database
    - The **deleted_at** field is set to the current UTC timestamp
    - The **updated_at** field is also updated to current UTC timestamp
    - Deleted providers will not appear in GET requests

    **Response:**
    Returns a 204 No Content status on successful deletion.

    **Error Responses:**
    - **404 Not Found**: Provider not found or already deleted
    - **500 Internal Server Error**: Server error during deletion

    **Use Cases:**
    - Remove providers from active catalog while preserving data
    - Maintain audit trail and referential integrity
    - Allow for potential provider restoration in the future
    """
    # In a real application, deleted_by would come from an authentication dependency
    deleted_by = "procurement_manager_test"
    
    await service.delete_provider(provider_id, deleted_by)
    # FastAPI automatically returns 204 No Content for None return with the decorator 