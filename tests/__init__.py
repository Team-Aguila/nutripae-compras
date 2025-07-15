"""
PAE Compras Integration Tests
Portable test suite for PAE Compras API endpoints
"""

__version__ = "1.0.0"
__author__ = "PAE Development Team"
__description__ = "Integration tests for PAE Compras API"

# Import all test classes for easy access
from .test_products_api import TestProductsAPI
from .test_providers_api import TestProvidersAPI
from .test_inventory_api import TestInventoryAPI
from .test_inventory_movements_api import TestInventoryMovementsAPI
from .test_purchase_orders_api import TestPurchaseOrdersAPI

# Import configuration and utilities
from .config import TestConfig
from .conftest import assert_response_has_id, assert_pagination_response, assert_error_response

__all__ = [
    "TestProductsAPI",
    "TestProvidersAPI", 
    "TestInventoryAPI",
    "TestInventoryMovementsAPI",
    "TestPurchaseOrdersAPI",
    "TestConfig",
    "assert_response_has_id",
    "assert_pagination_response",
    "assert_error_response"
]
