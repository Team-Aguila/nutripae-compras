from datetime import datetime, date
from typing import List, Optional, Dict, Any
from beanie import PydanticObjectId
from fastapi import HTTPException, status

from models import (
    Inventory,
    InventoryItemResponse,
    InventoryConsultationQuery,
    InventoryConsultationResponse,
    Product,
    Provider,
)


class InventoryService:
    """Service for inventory consultation and management"""

    @staticmethod
    async def consult_inventory(
        query_params: InventoryConsultationQuery
    ) -> InventoryConsultationResponse:
        """
        Consult inventory levels with filtering capabilities.
        
        Args:
            query_params: Query parameters for filtering and pagination
            
        Returns:
            InventoryConsultationResponse with filtered inventory items
        """
        # Build the aggregation pipeline
        pipeline = InventoryService._build_inventory_pipeline(query_params)
        
        # Execute the aggregation
        results = await Inventory.aggregate(pipeline).to_list()
        
        # Process results
        inventory_items = []
        total_count = 0
        
        if results:
            # Get the actual data and count
            data_result = results[0] if results else {}
            inventory_items = data_result.get('data', [])
            
            # Handle empty total_count array safely
            total_count_list = data_result.get('total_count', [])
            if total_count_list:
                total_count = total_count_list[0].get('count', 0)
            else:
                total_count = 0
        
        # Convert to response models
        response_items = []
        for item in inventory_items:
            response_item = InventoryService._convert_to_response_model(item)
            response_items.append(response_item)
        
        # Calculate pagination info - handle Optional[int] safely
        limit = query_params.limit or 100
        offset = query_params.offset or 0
        
        page_info = {
            'current_page': (offset // limit) + 1,
            'page_size': limit,
            'total_pages': (total_count + limit - 1) // limit,
            'has_next': offset + limit < total_count,
            'has_previous': offset > 0
        }
        
        # Calculate summary statistics
        summary = await InventoryService._calculate_summary(response_items, query_params)
        
        return InventoryConsultationResponse(
            items=response_items,
            total_count=total_count,
            page_info=page_info,
            summary=summary
        )

    @staticmethod
    def _build_inventory_pipeline(query_params: InventoryConsultationQuery) -> List[Dict[str, Any]]:
        """Build MongoDB aggregation pipeline for inventory consultation"""
        pipeline = []
        
        # Match stage for filtering
        match_conditions: Dict[str, Any] = {"deleted_at": None}
        
        if query_params.institution_id:
            match_conditions["institution_id"] = query_params.institution_id
            
        if query_params.product_id:
            match_conditions["product_id"] = query_params.product_id
            
        if not query_params.show_expired:
            today_str = datetime.now().date().isoformat()
            match_conditions["expiration_date"] = {"$gte": today_str}
            
        pipeline.append({"$match": match_conditions})
        
        # Lookup product information
        pipeline.append({
            "$lookup": {
                "from": "products",
                "localField": "product_id",
                "foreignField": "_id",
                "as": "product_info"
            }
        })
        
        # Lookup provider information through product
        pipeline.append({
            "$lookup": {
                "from": "providers",
                "localField": "product_info.provider_id",
                "foreignField": "_id",
                "as": "provider_info"
            }
        })
        
        # Unwind the lookups (but make them optional to avoid empty results)
        pipeline.append({
            "$unwind": {
                "path": "$product_info",
                "preserveNullAndEmptyArrays": True
            }
        })
        pipeline.append({
            "$unwind": {
                "path": "$provider_info",
                "preserveNullAndEmptyArrays": True
            }
        })
        
        # Additional filtering after lookups
        additional_match = {}
        
        if query_params.provider_id:
            additional_match["provider_info._id"] = query_params.provider_id
            
        if query_params.category:
            # For this example, we'll use provider name as category
            # In a real application, you might have a category field in products
            additional_match["provider_info.name"] = {"$regex": query_params.category, "$options": "i"}
            
        if query_params.show_below_threshold is not None:
            if query_params.show_below_threshold:
                additional_match["$expr"] = {"$lt": ["$remaining_weight", "$minimum_threshold"]}
            else:
                additional_match["$expr"] = {"$gte": ["$remaining_weight", "$minimum_threshold"]}
        
        if additional_match:
            pipeline.append({"$match": additional_match})
        
        # Add computed fields - Including ALL required fields for InventoryItemResponse
        pipeline.append({
            "$addFields": {
                "is_below_threshold": {"$lt": ["$remaining_weight", "$minimum_threshold"]},
                "product_name": {"$ifNull": ["$product_info.name", "Unknown Product"]},
                "provider_name": {"$ifNull": ["$provider_info.name", "Unknown Provider"]},
                "institution_name": {"$concat": ["Institution ", {"$toString": "$institution_id"}]},  # In real app, lookup institution
                "category": {"$ifNull": ["$provider_info.name", "Unknown Category"]},  # Using provider as category for now
                "base_unit": {"$ifNull": ["$unit", "kg"]},  # Use the unit field from inventory, default to kg
                "quantity": "$remaining_weight",
                "last_entry_date": "$date_of_admission",
                # Ensure all fields required by InventoryItemResponse are present
                "storage_location": {"$ifNull": ["$storage_location", ""]},  # Handle null storage_location
                "batch_number": {"$ifNull": ["$batch_number", ""]},  # Handle null batch_number
                "initial_weight": {"$ifNull": ["$initial_weight", 0.0]}  # Handle null initial_weight
            }
        })
        
        # Sort by date of admission (most recent first)
        pipeline.append({"$sort": {"date_of_admission": -1}})
        
        # Create faceted pipeline for pagination and counting
        pipeline.append({
            "$facet": {
                "data": [
                    {"$skip": query_params.offset},
                    {"$limit": query_params.limit}
                ],
                "total_count": [
                    {"$count": "count"}
                ]
            }
        })
        
        return pipeline

    @staticmethod
    def _convert_to_response_model(item: Dict[str, Any]) -> InventoryItemResponse:
        """Convert aggregation result to response model"""
        return InventoryItemResponse(
            _id=str(item["_id"]),  # Convert ObjectId to string
            product_id=str(item["product_id"]),  # Convert ObjectId to string
            product_name=item["product_name"],
            institution_id=item["institution_id"],
            institution_name=item["institution_name"],
            provider_name=item["provider_name"],
            category=item["category"],
            quantity=item["quantity"],
            base_unit=item["base_unit"],
            storage_location=item["storage_location"],  # Now included in pipeline
            lot=item["lot"],
            batch_number=item["batch_number"],  # Now included in pipeline
            last_entry_date=item["last_entry_date"],
            expiration_date=item["expiration_date"],
            minimum_threshold=item["minimum_threshold"],
            is_below_threshold=item["is_below_threshold"],
            initial_weight=item["initial_weight"],  # Now included in pipeline
            created_at=item["created_at"]
        )

    @staticmethod
    async def _calculate_summary(
        items: List[InventoryItemResponse],
        query_params: InventoryConsultationQuery
    ) -> Dict[str, Any]:
        """Calculate summary statistics for the inventory consultation"""
        if not items:
            return {
                "total_items": 0,
                "below_threshold_count": 0,
                "expired_count": 0,
                "categories": 0,
                "total_quantity": 0
            }
        
        today = date.today()
        items_below_threshold = sum(1 for item in items if item.is_below_threshold)
        expired_items = sum(1 for item in items if item.expiration_date < today)
        unique_categories = len(set(item.category for item in items))
        total_quantity = sum(item.quantity for item in items)
        
        return {
            "total_items": len(items),
            "below_threshold_count": items_below_threshold,
            "expired_count": expired_items,
            "categories": unique_categories,
            "total_quantity": round(total_quantity, 2)
        }

    @staticmethod
    async def update_minimum_threshold(
        inventory_id: PydanticObjectId,
        new_threshold: float
    ) -> bool:
        """Update minimum threshold for a specific inventory item"""
        inventory_item = await Inventory.get(inventory_id)
        if not inventory_item:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventory item not found"
            )
        
        inventory_item.minimum_threshold = new_threshold
        inventory_item.updated_at = datetime.utcnow()
        await inventory_item.save()
        
        return True


# Service instance
inventory_service = InventoryService() 