import logging
from datetime import date
from typing import List, Dict, Any
from collections import defaultdict

from ..models.purchase_calculation import (
    PurchaseCalculationRequest,
    PurchaseCalculationResponse,
    CalculationPeriod,
    PurchaseListItem,
    Coverage,
    CoverageServiceResponse,
    MenuServiceResponse,
    DailyIngredientNeed,
    IngredientCalculation
)
from ..services.external_services import CoverageServiceClient, MenuServiceClient, ExternalServiceError
from ..services.inventory_service import InventoryService

logger = logging.getLogger(__name__)


class CalculationService:
    """Service for calculating purchase needs based on menus and beneficiary coverage"""
    
    def __init__(self):
        self.coverage_client = CoverageServiceClient()
        self.menu_client = MenuServiceClient()
        self.inventory_service = InventoryService()
    
    async def calculate_purchase_needs(self, request: PurchaseCalculationRequest) -> PurchaseCalculationResponse:
        """
        Main method to calculate purchase needs.
        
        Steps:
        1. Get campus coverage and beneficiary counts
        2. Get scheduled menus and recipes
        3. Calculate daily ingredient needs
        4. Sum gross quantities by ingredient
        5. Get current inventory levels
        6. Calculate net purchase needs
        """
        try:
            logger.info(f"Starting purchase calculation for period {request.start_date} to {request.end_date}")
            
            # Step 1: Get campus coverage
            coverage_response = await self.coverage_client.get_campus_coverage(
                request.start_date, request.end_date, request.coverage
            )
            
            if not coverage_response.campuses:
                logger.warning("No campuses found for the specified coverage")
                return self._create_empty_response(request)
            
            campus_ids = [campus.id for campus in coverage_response.campuses]
            logger.info(f"Found {len(campus_ids)} campuses: {campus_ids}")
            
            # Step 2: Get scheduled menus
            menu_response = await self.menu_client.get_scheduled_menus(
                request.start_date, request.end_date, campus_ids
            )
            
            if not menu_response.daily_menus:
                logger.warning("No menus found for the specified period and campuses")
                return self._create_empty_response(request)
            
            logger.info(f"Found {len(menu_response.daily_menus)} daily menus")
            
            # Step 3: Calculate daily ingredient needs
            daily_needs = self._calculate_daily_ingredient_needs(coverage_response, menu_response)
            logger.info(f"Calculated {len(daily_needs)} daily ingredient needs")
            
            # Step 4: Sum gross quantities by ingredient
            ingredient_calculations = self._sum_ingredient_quantities(daily_needs)
            logger.info(f"Aggregated needs for {len(ingredient_calculations)} unique ingredients")
            
            # Step 5: Get current inventory and calculate net needs
            purchase_list = await self._calculate_net_purchase_needs(ingredient_calculations)
            
            # Step 6: Create response
            calculation_summary = {
                "total_campuses": coverage_response.total_campuses,
                "total_days": menu_response.total_days,
                "total_daily_calculations": len(daily_needs),
                "campuses_analyzed": [campus.name for campus in coverage_response.campuses]
            }
            
            response = PurchaseCalculationResponse(
                calculation_period=CalculationPeriod(
                    start_date=request.start_date,
                    end_date=request.end_date
                ),
                purchase_list=purchase_list,
                total_ingredients=len(purchase_list),
                calculation_summary=calculation_summary
            )
            
            logger.info(f"Purchase calculation completed successfully. {len(purchase_list)} ingredients need purchase.")
            return response
            
        except ExternalServiceError as e:
            logger.error(f"External service error: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error in purchase calculation: {str(e)}")
            raise
    
    def _calculate_daily_ingredient_needs(
        self, 
        coverage_response: CoverageServiceResponse, 
        menu_response: MenuServiceResponse
    ) -> List[DailyIngredientNeed]:
        """Calculate daily ingredient needs for each campus, day, and meal type"""
        daily_needs = []
        
        # Create a mapping of campus_id to campus info for quick lookup
        campus_map = {campus.id: campus for campus in coverage_response.campuses}
        
        for daily_menu in menu_response.daily_menus:
            campus_info = campus_map.get(daily_menu.location_id)
            if not campus_info:
                logger.warning(f"Campus {daily_menu.location_id} not found in coverage data")
                continue
            
            # Process each meal type
            meal_types = [
                ("breakfast", daily_menu.breakfast, campus_info.beneficiary_counts.breakfast),
                ("lunch", daily_menu.lunch, campus_info.beneficiary_counts.lunch),
                ("snack", daily_menu.snack, campus_info.beneficiary_counts.snack)
            ]
            
            for meal_type, dishes, beneficiary_count in meal_types:
                if beneficiary_count == 0:
                    continue  # Skip if no beneficiaries for this meal type
                
                for dish in dishes:
                    for ingredient in dish.ingredients:
                        # Calculate daily ingredient need
                        daily_need = ingredient.quantity * beneficiary_count
                        shrinkage_factor = dish.shrinkage_factor or 1.1  # Default 10% shrinkage
                        gross_need = daily_need * shrinkage_factor
                        
                        daily_ingredient_need = DailyIngredientNeed(
                            ingredient_id=ingredient.ingredient_id,
                            ingredient_name=ingredient.ingredient_name,
                            campus_id=daily_menu.location_id,
                            campus_name=daily_menu.location_name,
                            meal_type=meal_type,
                            beneficiary_count=beneficiary_count,
                            portion_size=ingredient.quantity,
                            unit=ingredient.unit,
                            shrinkage_factor=shrinkage_factor,
                            daily_need=daily_need,
                            gross_need=gross_need,
                            date=daily_menu.menu_date
                        )
                        
                        daily_needs.append(daily_ingredient_need)
        
        return daily_needs
    
    def _sum_ingredient_quantities(self, daily_needs: List[DailyIngredientNeed]) -> Dict[str, IngredientCalculation]:
        """Sum gross quantities by ingredient across all days and campuses"""
        ingredient_calculations = {}
        
        for daily_need in daily_needs:
            ingredient_id = daily_need.ingredient_id
            
            if ingredient_id not in ingredient_calculations:
                ingredient_calculations[ingredient_id] = IngredientCalculation(
                    ingredient_id=ingredient_id,
                    ingredient_name=daily_need.ingredient_name,
                    unit=daily_need.unit,
                    total_gross_quantity=0.0,
                    daily_details=[]
                )
            
            # Convert units to standard base unit if needed
            converted_quantity = self._convert_to_base_unit(daily_need.gross_need, daily_need.unit)
            
            ingredient_calc = ingredient_calculations[ingredient_id]
            ingredient_calc.total_gross_quantity += converted_quantity
            
            # Store daily detail for audit
            detail = {
                "date": daily_need.date.isoformat(),
                "campus_name": daily_need.campus_name,
                "meal_type": daily_need.meal_type,
                "beneficiary_count": daily_need.beneficiary_count,
                "portion_size": daily_need.portion_size,
                "shrinkage_factor": daily_need.shrinkage_factor,
                "gross_need": daily_need.gross_need,
                "converted_quantity": converted_quantity
            }
            ingredient_calc.daily_details.append(detail)
        
        return ingredient_calculations
    
    def _convert_to_base_unit(self, quantity: float, unit: str) -> float:
        """Convert ingredient quantities to base unit (grams)"""
        # Conversion factors to grams
        conversion_factors = {
            "kg": 1000.0,
            "g": 1.0,
            "gram": 1.0,
            "grams": 1.0,
            "kilogram": 1000.0,
            "kilograms": 1000.0,
            "lb": 453.592,  # pounds to grams
            "lbs": 453.592,
            "oz": 28.3495,  # ounces to grams
            "l": 1000.0,    # liters to grams (assuming water density)
            "ml": 1.0,      # milliliters to grams (assuming water density)
            "liter": 1000.0,
            "liters": 1000.0,
            "milliliter": 1.0,
            "milliliters": 1.0
        }
        
        # Normalize unit name
        normalized_unit = unit.lower().strip()
        
        if normalized_unit in conversion_factors:
            return quantity * conversion_factors[normalized_unit]
        else:
            # If unit is unknown, assume it's already in base unit (grams)
            logger.warning(f"Unknown unit '{unit}', assuming base unit (grams)")
            return quantity
    
    async def _calculate_net_purchase_needs(
        self, 
        ingredient_calculations: Dict[str, IngredientCalculation]
    ) -> List[PurchaseListItem]:
        """Calculate net purchase needs by subtracting current inventory"""
        purchase_list = []
        
        for ingredient_calc in ingredient_calculations.values():
            try:
                # Get current inventory for this ingredient
                current_inventory = await self._get_total_available_inventory(
                    ingredient_calc.ingredient_id
                )
                
                # Calculate safety stock (10% of gross quantity or minimum 1000g)
                safety_stock = max(ingredient_calc.total_gross_quantity * 0.1, 1000.0)
                
                # Calculate net quantity needed
                net_quantity = ingredient_calc.total_gross_quantity + safety_stock - current_inventory
                net_quantity_to_purchase = max(net_quantity, 0.0)  # Can't purchase negative quantities
                
                purchase_item = PurchaseListItem(
                    ingredient_name=ingredient_calc.ingredient_name,
                    ingredient_id=ingredient_calc.ingredient_id,
                    unit="grams",  # All quantities converted to grams
                    total_gross_quantity=ingredient_calc.total_gross_quantity,
                    current_inventory=current_inventory,
                    safety_stock=safety_stock,
                    net_quantity_to_purchase=net_quantity_to_purchase
                )
                
                purchase_list.append(purchase_item)
                
            except Exception as e:
                logger.error(f"Error calculating net needs for ingredient {ingredient_calc.ingredient_id}: {str(e)}")
                # Continue with zero inventory assumption
                safety_stock = max(ingredient_calc.total_gross_quantity * 0.1, 1000.0)
                
                purchase_item = PurchaseListItem(
                    ingredient_name=ingredient_calc.ingredient_name,
                    ingredient_id=ingredient_calc.ingredient_id,
                    unit="grams",
                    total_gross_quantity=ingredient_calc.total_gross_quantity,
                    current_inventory=0.0,  # Assume zero if can't get inventory
                    safety_stock=safety_stock,
                    net_quantity_to_purchase=ingredient_calc.total_gross_quantity + safety_stock
                )
                
                purchase_list.append(purchase_item)
        
        # Sort by net quantity to purchase (descending) to prioritize high-need items
        purchase_list.sort(key=lambda x: x.net_quantity_to_purchase, reverse=True)
        
        return purchase_list
    
    async def _get_total_available_inventory(self, ingredient_id: str) -> float:
        """Get total available inventory for an ingredient across all institutions"""
        from ..models import Inventory
        from bson import ObjectId
        
        try:
            # Convert ingredient_id to ObjectId if needed
            if isinstance(ingredient_id, str):
                try:
                    product_object_id = ObjectId(ingredient_id)
                except:
                    logger.warning(f"Invalid ingredient_id format: {ingredient_id}")
                    return 0.0
            else:
                product_object_id = ingredient_id
            
            # Query inventory for this product
            inventory_items = await Inventory.find({
                "product_id": product_object_id,
                "deleted_at": None,
                "expiration_date": {"$gte": date.today()}  # Only non-expired items
            }).to_list()
            
            # Sum up remaining weights, converting to grams
            total_inventory = 0.0
            for item in inventory_items:
                if item.remaining_weight and item.remaining_weight > 0:
                    # Convert to grams based on unit
                    converted_weight = self._convert_to_base_unit(
                        item.remaining_weight, 
                        item.unit or "kg"
                    )
                    total_inventory += converted_weight
            
            return total_inventory
            
        except Exception as e:
            logger.error(f"Error getting inventory for ingredient {ingredient_id}: {str(e)}")
            return 0.0
    
    def _create_empty_response(self, request: PurchaseCalculationRequest) -> PurchaseCalculationResponse:
        """Create an empty response when no data is found"""
        return PurchaseCalculationResponse(
            calculation_period=CalculationPeriod(
                start_date=request.start_date,
                end_date=request.end_date
            ),
            purchase_list=[],
            total_ingredients=0,
            calculation_summary={
                "message": "No campuses or menus found for the specified criteria"
            }
        ) 