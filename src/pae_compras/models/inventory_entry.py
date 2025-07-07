from datetime import datetime, date
from typing import List, Optional, Dict, Any
from enum import Enum

from beanie import PydanticObjectId
from pydantic import BaseModel, Field


class EntryMode(str, Enum):
    """Inventory entry modes"""
    MANUAL = "manual"  # Manual entry without purchase order
    PURCHASE_ORDER = "purchase_order"  # Entry linked to purchase order


class InventoryEntryItem(BaseModel):
    """Individual item in an inventory entry"""
    product_id: PydanticObjectId = Field(description="The ID of the product/ingredient")
    product_name: Optional[str] = Field(default=None, description="Name of the product (filled by service)")
    quantity: float = Field(gt=0, description="Quantity received")
    unit: str = Field(default="kg", description="Unit of measurement (kg, units, liters, etc.)")
    storage_location: Optional[str] = Field(default=None, description="Specific storage location within institution")
    lot: str = Field(description="Lot number of the product")
    expiration_date: date = Field(description="Expiration date of the product")
    unit_cost: Optional[float] = Field(default=None, description="Cost per unit (for cost tracking)")
    notes: Optional[str] = Field(default=None, description="Additional notes for this item")


class InventoryEntryRequest(BaseModel):
    """Request model for creating an inventory entry"""
    # Entry mode and basic info
    entry_mode: EntryMode = Field(description="Entry mode (manual or purchase_order)")
    institution_id: int = Field(description="The ID of the institution/warehouse from coverage module")
    
    # Purchase order info (optional for manual mode)
    purchase_order_id: Optional[PydanticObjectId] = Field(
        default=None, 
        description="The ID of the related purchase order (required for purchase_order mode)"
    )
    
    # Receipt details
    receipt_date: date = Field(description="The date the ingredients were received")
    delivery_person_name: str = Field(description="Name of the person who delivered the ingredients")
    delivery_company: Optional[str] = Field(default=None, description="Delivery company name")
    delivery_notes: Optional[str] = Field(default=None, description="Additional delivery notes")
    
    # Items
    items: List[InventoryEntryItem] = Field(
        min_items=1, 
        description="List of items being received"
    )
    
    # Quality control
    quality_check_passed: bool = Field(default=True, description="Whether quality check passed")
    quality_notes: Optional[str] = Field(default=None, description="Quality control notes")
    
    # Additional metadata
    receiving_temperature: Optional[float] = Field(default=None, description="Temperature at which items were received")
    truck_license_plate: Optional[str] = Field(default=None, description="Delivery truck license plate")


class InventoryEntryResponse(BaseModel):
    """Response model for inventory entry"""
    # Entry information
    id: PydanticObjectId = Field(alias="_id")
    entry_mode: EntryMode
    institution_id: int
    institution_name: Optional[str] = Field(default=None, description="Institution name (filled by service)")
    
    # Purchase order info
    purchase_order_id: Optional[PydanticObjectId]
    purchase_order_number: Optional[str] = Field(default=None, description="Purchase order number")
    
    # Receipt details
    receipt_date: date
    delivery_person_name: str
    delivery_company: Optional[str]
    delivery_notes: Optional[str]
    
    # Items with enriched data
    items: List[InventoryEntryItem]
    
    # Quality control
    quality_check_passed: bool
    quality_notes: Optional[str]
    
    # Additional metadata
    receiving_temperature: Optional[float]
    truck_license_plate: Optional[str]
    
    # Summary information
    total_items: int = Field(description="Total number of different items received")
    total_quantity: float = Field(description="Total quantity received (sum of all items)")
    
    # Audit information
    created_by: str
    created_at: datetime
    
    # Processing status
    inventory_updated: bool = Field(description="Whether inventory was successfully updated")
    movements_created: int = Field(description="Number of inventory movements created")
    
    class Config:
        populate_by_name = True


class InventoryEntryValidationError(BaseModel):
    """Model for validation errors in inventory entry"""
    field: str = Field(description="Field that has the error")
    error_code: str = Field(description="Error code")
    error_message: str = Field(description="Human-readable error message")
    suggested_value: Optional[str] = Field(default=None, description="Suggested correction")


class InventoryEntryValidationResponse(BaseModel):
    """Response model for inventory entry validation"""
    is_valid: bool = Field(description="Whether the entry is valid")
    errors: List[InventoryEntryValidationError] = Field(description="List of validation errors")
    warnings: List[InventoryEntryValidationError] = Field(description="List of validation warnings")
    
    # Purchase order validation (if applicable)
    purchase_order_valid: Optional[bool] = Field(default=None, description="Whether purchase order is valid")
    purchase_order_items_match: Optional[bool] = Field(default=None, description="Whether items match purchase order")
    
    # Product validation
    products_exist: bool = Field(description="Whether all products exist in the system")
    products_active: bool = Field(description="Whether all products are active")
    
    # Inventory validation
    storage_locations_valid: bool = Field(description="Whether storage locations are valid")
    expiration_dates_valid: bool = Field(description="Whether expiration dates are reasonable")


class InventoryEntrySearchQuery(BaseModel):
    """Query parameters for searching inventory entries"""
    institution_id: Optional[int] = Field(default=None, description="Filter by institution")
    entry_mode: Optional[EntryMode] = Field(default=None, description="Filter by entry mode")
    purchase_order_id: Optional[PydanticObjectId] = Field(default=None, description="Filter by purchase order")
    product_id: Optional[PydanticObjectId] = Field(default=None, description="Filter by product")
    delivery_person_name: Optional[str] = Field(default=None, description="Filter by delivery person")
    
    # Date filters
    receipt_date_from: Optional[date] = Field(default=None, description="Filter entries from this date")
    receipt_date_to: Optional[date] = Field(default=None, description="Filter entries to this date")
    
    # Quality control
    quality_check_passed: Optional[bool] = Field(default=None, description="Filter by quality check status")
    
    # Pagination
    limit: int = Field(default=100, le=1000, description="Maximum number of entries to return")
    offset: int = Field(default=0, ge=0, description="Number of entries to skip")
    
    # Sorting
    sort_by: str = Field(default="created_at", description="Field to sort by")
    sort_order: str = Field(default="desc", description="Sort order (asc/desc)")


class InventoryEntrySearchResponse(BaseModel):
    """Response model for inventory entry search"""
    entries: List[InventoryEntryResponse]
    total_count: int
    page_info: Dict[str, Any] = Field(description="Pagination information")
    filters_applied: Dict[str, Any] = Field(description="Applied filters")
    
    # Summary statistics
    summary: Dict[str, Any] = Field(description="Summary statistics")


class InventoryEntryStats(BaseModel):
    """Statistics for inventory entries"""
    total_entries: int
    manual_entries: int
    purchase_order_entries: int
    
    # Quality statistics
    quality_check_passed_count: int
    quality_check_failed_count: int
    quality_check_pass_rate: float
    
    # Date range statistics
    date_range: Dict[str, date]
    entries_per_day: Dict[str, int]
    
    # Top statistics
    top_institutions: List[Dict[str, Any]]
    top_products: List[Dict[str, Any]]
    top_delivery_persons: List[Dict[str, Any]] 