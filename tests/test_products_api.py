"""
Integration tests for Products API
Test cases: PRD-001 to PRD-026
"""
import pytest
import httpx
from typing import Dict, Any

from .conftest import assert_response_has_id, assert_pagination_response, assert_error_response


class TestProductsAPI:
    """Test suite for Products API endpoints"""
    
    # CREATE PRODUCT TESTS
    
    async def test_create_product_success(self, client: httpx.AsyncClient, api_prefix: str, test_provider):
        """PRD-001: Successfully create a new product"""
        provider_id = test_provider.get("_id") or test_provider.get("id")
        
        product_data = {
            "provider_id": provider_id,
            "name": "Test Product Success",
            "weight": 1.0,
            "weekly_availability": "MONDAY",
            "life_time": {"value": 30, "unit": "days"}
        }
        
        response = await client.post(f"{api_prefix}/products", json=product_data)
        
        assert response.status_code == 201
        data = response.json()
        product_id = assert_response_has_id(data)
        assert data["name"] == product_data["name"]
        assert data["weight"] == product_data["weight"]
        assert data["weekly_availability"] == product_data["weekly_availability"]
        assert data["life_time"] == product_data["life_time"]
        assert "created_at" in data
        assert "updated_at" in data
        assert data.get("deleted_at") is None
        
        # Cleanup
        await client.delete(f"{api_prefix}/products/{product_id}")

    async def test_create_product_missing_required_fields(self, client: httpx.AsyncClient, api_prefix: str, test_provider):
        """PRD-002: Fail to create product with missing required fields"""
        provider_id = test_provider.get("_id") or test_provider.get("id")
        
        invalid_data = {
            "provider_id": provider_id,
            "weight": 1.0
        }
        
        response = await client.post(f"{api_prefix}/products", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert_error_response(data)
        assert any(error["loc"] == ["body", "name"] for error in data["detail"])

    async def test_create_product_invalid_weight(self, client: httpx.AsyncClient, api_prefix: str, test_provider):
        """PRD-003: Fail to create product with invalid weight"""
        provider_id = test_provider.get("_id") or test_provider.get("id")
        
        invalid_data = {
            "provider_id": provider_id,
            "name": "Arroz Blanco",
            "weight": -1.0,
            "weekly_availability": "MONDAY",
            "life_time": {"value": 30, "unit": "days"}
        }
        
        response = await client.post(f"{api_prefix}/products", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert_error_response(data)
        assert any(error["loc"] == ["body", "weight"] for error in data["detail"])

    async def test_create_product_invalid_weekly_availability(self, client: httpx.AsyncClient, api_prefix: str, test_provider):
        """PRD-004: Fail to create product with invalid weekly_availability"""
        provider_id = test_provider.get("_id") or test_provider.get("id")
        
        invalid_data = {
            "provider_id": provider_id,
            "name": "Arroz Blanco",
            "weight": 1.0,
            "weekly_availability": "INVALID_DAY",
            "life_time": {"value": 30, "unit": "days"}
        }
        
        response = await client.post(f"{api_prefix}/products", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert_error_response(data)
        assert any(error["loc"] == ["body", "weekly_availability"] for error in data["detail"])

    async def test_create_product_invalid_provider_id(self, client: httpx.AsyncClient, api_prefix: str):
        """PRD-005: Fail to create product with invalid provider_id"""
        invalid_data = {
            "provider_id": "invalid_id",
            "name": "Arroz Blanco",
            "weight": 1.0,
            "weekly_availability": "MONDAY",
            "life_time": {"value": 30, "unit": "days"}
        }
        
        response = await client.post(f"{api_prefix}/products", json=invalid_data)
        
        assert response.status_code == 422
        data = response.json()
        assert_error_response(data)

    async def test_create_product_non_existent_provider(self, client: httpx.AsyncClient, api_prefix: str):
        """PRD-006: Fail to create product with non-existent provider"""
        invalid_data = {
            "provider_id": "648f8f8f8f8f8f8f8f8f8f8a",
            "name": "Arroz Blanco",
            "weight": 1.0,
            "weekly_availability": "MONDAY",
            "life_time": {"value": 30, "unit": "days"}
        }
        
        response = await client.post(f"{api_prefix}/products", json=invalid_data)
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data, "Provider not found")

    # READ PRODUCT TESTS
    
    async def test_get_product_by_id_success(self, client: httpx.AsyncClient, api_prefix: str, test_product):
        """PRD-007: Successfully retrieve an existing product"""
        product_id = test_product.get("_id") or test_product.get("id")
        
        response = await client.get(f"{api_prefix}/products/{product_id}")
        
        assert response.status_code == 200
        data = response.json()
        assert_response_has_id(data)
        assert "name" in data
        assert "weight" in data
        assert "weekly_availability" in data
        assert "life_time" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_get_product_by_id_invalid_format(self, client: httpx.AsyncClient, api_prefix: str):
        """PRD-008: Fail to retrieve product with invalid ID format"""
        response = await client.get(f"{api_prefix}/products/invalid_id")
        
        assert response.status_code == 422
        data = response.json()
        assert_error_response(data)

    async def test_get_product_by_id_not_found(self, client: httpx.AsyncClient, api_prefix: str):
        """PRD-009: Fail to retrieve non-existent product"""
        response = await client.get(f"{api_prefix}/products/648f8f8f8f8f8f8f8f8f8f8a")
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data, "not found or has been deleted")

    async def test_get_product_soft_deleted(self, client: httpx.AsyncClient, api_prefix: str, test_product):
        """PRD-010: Fail to retrieve soft-deleted product"""
        product_id = test_product.get("_id") or test_product.get("id")
        
        # First, soft delete the product
        await client.delete(f"{api_prefix}/products/{product_id}")
        
        # Then try to retrieve it
        response = await client.get(f"{api_prefix}/products/{product_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data, "not found or has been deleted")

    # LIST PRODUCTS TESTS
    
    async def test_get_products_list_default_pagination(self, client: httpx.AsyncClient, api_prefix: str):
        """PRD-011: Successfully retrieve products with default pagination"""
        response = await client.get(f"{api_prefix}/products")
        
        assert response.status_code == 200
        data = response.json()
        # Handle both response formats
        items_key = "products" if "products" in data else "items"
        assert_pagination_response(data, items_key)

    async def test_get_products_list_with_provider_filter(self, client: httpx.AsyncClient, api_prefix: str, test_provider):
        """PRD-012: Successfully retrieve products with provider filter"""
        provider_id = test_provider.get("_id") or test_provider.get("id")
        
        response = await client.get(f"{api_prefix}/products", params={"provider_id": provider_id})
        
        assert response.status_code == 200
        data = response.json()
        items_key = "products" if "products" in data else "items"
        assert_pagination_response(data, items_key)

    async def test_get_products_list_with_pagination(self, client: httpx.AsyncClient, api_prefix: str):
        """PRD-013: Successfully retrieve products with pagination"""
        response = await client.get(f"{api_prefix}/products", params={"limit": 10, "offset": 5})
        
        assert response.status_code == 200
        data = response.json()
        items_key = "products" if "products" in data else "items"
        assert_pagination_response(data, items_key)

    async def test_get_products_list_invalid_limit(self, client: httpx.AsyncClient, api_prefix: str):
        """PRD-014: Fail with invalid limit value"""
        response = await client.get(f"{api_prefix}/products", params={"limit": 1001})
        
        assert response.status_code == 422
        data = response.json()
        assert_error_response(data)

    async def test_get_products_list_invalid_offset(self, client: httpx.AsyncClient, api_prefix: str):
        """PRD-015: Fail with invalid offset value"""
        response = await client.get(f"{api_prefix}/products", params={"offset": -1})
        
        assert response.status_code == 422
        data = response.json()
        assert_error_response(data)

    # UPDATE PRODUCT TESTS
    
    async def test_update_product_name_success(self, client: httpx.AsyncClient, api_prefix: str, test_product):
        """PRD-016: Successfully update product name"""
        product_id = test_product.get("_id") or test_product.get("id")
        
        update_data = {"name": "Updated Product Name"}
        response = await client.put(f"{api_prefix}/products/{product_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert_response_has_id(data)
        assert data["name"] == "Updated Product Name"
        assert "updated_at" in data

    async def test_update_product_multiple_fields_success(self, client: httpx.AsyncClient, api_prefix: str, test_product):
        """PRD-017: Successfully update multiple fields"""
        product_id = test_product.get("_id") or test_product.get("id")
        
        update_data = {
            "name": "New Name",
            "weight": 2.0,
            "weekly_availability": "TUESDAY"
        }
        response = await client.put(f"{api_prefix}/products/{product_id}", json=update_data)
        
        assert response.status_code == 200
        data = response.json()
        assert_response_has_id(data)
        assert data["name"] == "New Name"
        assert data["weight"] == 2.0
        assert data["weekly_availability"] == "TUESDAY"
        assert "updated_at" in data

    async def test_update_product_not_found(self, client: httpx.AsyncClient, api_prefix: str):
        """PRD-018: Fail to update non-existent product"""
        update_data = {"name": "Updated Name"}
        response = await client.put(f"{api_prefix}/products/648f8f8f8f8f8f8f8f8f8f8a", json=update_data)
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data, "not found or has been deleted")

    async def test_update_product_invalid_weight(self, client: httpx.AsyncClient, api_prefix: str, test_product):
        """PRD-019: Fail to update with invalid weight"""
        product_id = test_product.get("_id") or test_product.get("id")
        
        update_data = {"weight": -1.0}
        response = await client.put(f"{api_prefix}/products/{product_id}", json=update_data)
        
        assert response.status_code == 422
        data = response.json()
        assert_error_response(data)

    async def test_update_product_soft_deleted(self, client: httpx.AsyncClient, api_prefix: str, test_product):
        """PRD-020: Fail to update soft-deleted product"""
        product_id = test_product.get("_id") or test_product.get("id")
        
        # First, soft delete the product
        await client.delete(f"{api_prefix}/products/{product_id}")
        
        # Then try to update it
        update_data = {"name": "Updated Name"}
        response = await client.put(f"{api_prefix}/products/{product_id}", json=update_data)
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data, "not found or has been deleted")

    # DELETE PRODUCT TESTS
    
    async def test_delete_product_success(self, client: httpx.AsyncClient, api_prefix: str, test_product):
        """PRD-021: Successfully soft delete a product"""
        product_id = test_product.get("_id") or test_product.get("id")
        
        response = await client.delete(f"{api_prefix}/products/{product_id}")
        
        assert response.status_code == 204

    async def test_delete_product_not_found(self, client: httpx.AsyncClient, api_prefix: str):
        """PRD-022: Fail to delete non-existent product"""
        response = await client.delete(f"{api_prefix}/products/648f8f8f8f8f8f8f8f8f8f8a")
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data, "not found or has been deleted")

    async def test_delete_product_already_deleted(self, client: httpx.AsyncClient, api_prefix: str, test_product):
        """PRD-023: Fail to delete already deleted product"""
        product_id = test_product.get("_id") or test_product.get("id")
        
        # First, delete the product
        await client.delete(f"{api_prefix}/products/{product_id}")
        
        # Then try to delete it again
        response = await client.delete(f"{api_prefix}/products/{product_id}")
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data, "not found or has been deleted")

    # SHRINKAGE TESTS
    
    async def test_update_product_shrinkage_success(self, client: httpx.AsyncClient, api_prefix: str, test_product):
        """PRD-024: Successfully update shrinkage factor"""
        product_id = test_product.get("_id") or test_product.get("id")
        
        shrinkage_data = {"shrinkage_factor": 0.15}
        response = await client.patch(f"{api_prefix}/products/{product_id}/shrinkage", json=shrinkage_data)
        
        assert response.status_code == 200
        data = response.json()
        assert_response_has_id(data)
        assert data["shrinkage_factor"] == 0.15
        assert "updated_at" in data

    async def test_update_product_shrinkage_invalid_factor(self, client: httpx.AsyncClient, api_prefix: str, test_product):
        """PRD-025: Fail to update with invalid shrinkage factor"""
        product_id = test_product.get("_id") or test_product.get("id")
        
        shrinkage_data = {"shrinkage_factor": -0.1}
        response = await client.patch(f"{api_prefix}/products/{product_id}/shrinkage", json=shrinkage_data)
        
        assert response.status_code == 422
        data = response.json()
        assert_error_response(data)

    async def test_update_product_shrinkage_not_found(self, client: httpx.AsyncClient, api_prefix: str):
        """PRD-026: Fail to update shrinkage for non-existent product"""
        shrinkage_data = {"shrinkage_factor": 0.15}
        response = await client.patch(f"{api_prefix}/products/648f8f8f8f8f8f8f8f8f8f8a/shrinkage", json=shrinkage_data)
        
        assert response.status_code == 404
        data = response.json()
        assert_error_response(data, "not found or has been deleted") 