from datetime import datetime
from typing import List, Optional
from fastapi import HTTPException, status
from beanie import PydanticObjectId
from pymongo.errors import DuplicateKeyError

from models import Provider


class ProviderService:
    """Service for managing provider CRUD operations"""

    @staticmethod
    async def create_provider(provider_data: dict, created_by: str = "system") -> Provider:
        """
        Create a new provider.
        
        Args:
            provider_data: Dictionary containing provider data
            created_by: User who created the provider
            
        Returns:
            Provider: Created provider
            
        Raises:
            HTTPException: If validation fails, NIT already exists, or creation fails
        """
        # Create the provider with current timestamp
        new_provider = Provider(
            **provider_data,
            created_at=datetime.utcnow(),
            updated_at=None,
            deleted_at=None,
        )
        
        try:
            await new_provider.insert()
            return new_provider
        except DuplicateKeyError:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Provider with NIT '{provider_data.get('nit')}' already exists"
            )
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create provider: {str(e)}"
            )

    @staticmethod
    async def get_provider_by_id(provider_id: PydanticObjectId) -> Provider:
        """
        Get a provider by its ID (only non-deleted providers).
        
        Args:
            provider_id: The ID of the provider
            
        Returns:
            Provider: The provider if found and not deleted
            
        Raises:
            HTTPException: If provider not found or deleted
        """
        provider = await Provider.get(provider_id)
        
        if not provider or provider.deleted_at is not None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Provider with id {provider_id} not found or has been deleted"
            )
        
        return provider

    @staticmethod
    async def get_providers(
        is_local_provider: Optional[bool] = None,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Provider]:
        """
        Get a list of providers (only non-deleted providers).
        
        Args:
            is_local_provider: Optional filter by local provider flag
            limit: Maximum number of providers to return
            offset: Number of providers to skip
            
        Returns:
            List[Provider]: List of providers
        """
        # Build query for non-deleted providers
        query = {"deleted_at": None}
        
        if is_local_provider is not None:
            query["is_local_provider"] = is_local_provider
        
        providers = await Provider.find(query).sort("-created_at").skip(offset).limit(limit).to_list()
        
        return providers

    @staticmethod
    async def update_provider(
        provider_id: PydanticObjectId,
        update_data: dict,
        updated_by: str = "system"
    ) -> Provider:
        """
        Update a provider (only non-deleted providers). NIT is immutable.
        
        Args:
            provider_id: The ID of the provider to update
            update_data: Dictionary containing fields to update
            updated_by: User who updated the provider
            
        Returns:
            Provider: Updated provider
            
        Raises:
            HTTPException: If provider not found, deleted, or update fails
        """
        # Get the provider first to ensure it exists and is not deleted
        provider = await ProviderService.get_provider_by_id(provider_id)
        
        # Update fields (excluding immutable fields like nit, created_at, etc.)
        allowed_fields = ["name", "address", "responsible_name", "email", "phone_number", "is_local_provider"]
        
        for field, value in update_data.items():
            if field in allowed_fields and value is not None:
                setattr(provider, field, value)
        
        # Set updated timestamp
        provider.updated_at = datetime.utcnow()
        
        try:
            await provider.save()
            return provider
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to update provider: {str(e)}"
            )

    @staticmethod
    async def delete_provider(provider_id: PydanticObjectId, deleted_by: str = "system") -> bool:
        """
        Soft delete a provider.
        
        Args:
            provider_id: The ID of the provider to delete
            deleted_by: User who deleted the provider
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            HTTPException: If provider not found or already deleted
        """
        # Get the provider first to ensure it exists and is not already deleted
        provider = await ProviderService.get_provider_by_id(provider_id)
        
        # Perform soft delete
        provider.deleted_at = datetime.utcnow()
        provider.updated_at = datetime.utcnow()
        
        try:
            await provider.save()
            return True
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to delete provider: {str(e)}"
            )

    @staticmethod
    async def count_providers(is_local_provider: Optional[bool] = None) -> int:
        """
        Count the total number of non-deleted providers.
        
        Args:
            is_local_provider: Optional filter by local provider flag
            
        Returns:
            int: Total count of providers
        """
        query = {"deleted_at": None}
        
        if is_local_provider is not None:
            query["is_local_provider"] = is_local_provider
        
        return await Provider.find(query).count()


# Create service instance
provider_service = ProviderService() 