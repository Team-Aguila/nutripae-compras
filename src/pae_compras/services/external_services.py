import logging
from datetime import date
from typing import List, Dict, Any, Optional
import aiohttp
from pydantic import ValidationError

from ..core.config import settings
from ..models.purchase_calculation import (
    Coverage,
    CoverageServiceResponse,
    MenuServiceResponse,
    CampusInfo,
    BeneficiaryCount,
    DailyMenu,
    DishInfo,
    IngredientInfo
)

logger = logging.getLogger(__name__)


class ExternalServiceError(Exception):
    """Base exception for external service errors"""
    pass


class CoverageServiceClient:
    """Client for communicating with the Coverage Service"""
    
    def __init__(self):
        self.base_url = settings.coverage_service_url
        self.api_prefix = "/api/v1"
    
    async def get_campus_coverage(
        self, 
        start_date: date, 
        end_date: date, 
        coverage: Coverage
    ) -> CoverageServiceResponse:
        """
        Get campus coverage and beneficiary counts for the specified period and coverage area.
        
        This method will:
        1. Get campuses based on coverage type (municipality or direct campus IDs)
        2. For each campus, get active coverages (beneficiaries) by meal type
        3. Return aggregated beneficiary counts per campus
        """
        try:
            async with aiohttp.ClientSession() as session:
                campuses = await self._get_campuses_by_coverage(session, coverage)
                
                campus_infos = []
                for campus in campuses:
                    beneficiary_counts = await self._get_beneficiary_counts_for_campus(
                        session, campus["id"], start_date, end_date
                    )
                    
                    campus_info = CampusInfo(
                        id=str(campus["id"]),
                        name=campus["name"],
                        location_type="campus",
                        beneficiary_counts=beneficiary_counts
                    )
                    campus_infos.append(campus_info)
                
                return CoverageServiceResponse(
                    campuses=campus_infos,
                    total_campuses=len(campus_infos)
                )
                
        except Exception as e:
            logger.error(f"Error getting campus coverage: {str(e)}")
            raise ExternalServiceError(f"Failed to get coverage data: {str(e)}")
    
    async def _get_campuses_by_coverage(self, session: aiohttp.ClientSession, coverage: Coverage) -> List[Dict[str, Any]]:
        """Get campuses based on coverage specification"""
        if coverage.type == "campus":
            # Direct campus IDs
            campuses = []
            for campus_id in coverage.ids:
                campus = await self._get_campus_by_id(session, str(campus_id))
                if campus:
                    campuses.append(campus)
            return campuses
        
        elif coverage.type == "municipality":
            # Get campuses by municipality
            campuses = []
            for municipality_id in coverage.ids:
                municipality_campuses = await self._get_campuses_by_municipality(session, str(municipality_id))
                campuses.extend(municipality_campuses)
            return campuses
        
        else:
            raise ExternalServiceError(f"Unsupported coverage type: {coverage.type}")
    
    async def _get_campus_by_id(self, session: aiohttp.ClientSession, campus_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific campus by ID"""
        url = f"{self.base_url}{self.api_prefix}/campuses/{campus_id}"
        
        async with session.get(url) as response:
            if response.status == 200:
                return await response.json()
            elif response.status == 404:
                logger.warning(f"Campus {campus_id} not found")
                return None
            else:
                response.raise_for_status()
    
    async def _get_campuses_by_municipality(self, session: aiohttp.ClientSession, municipality_id: str) -> List[Dict[str, Any]]:
        """Get all campuses in a municipality"""
        # First get institutions in the town/municipality
        url = f"{self.base_url}{self.api_prefix}/institutions/"
        
        async with session.get(url) as response:
            if response.status != 200:
                response.raise_for_status()
            
            institutions = await response.json()
            # Filter institutions by town_id (municipality)
            municipality_institutions = [inst for inst in institutions if str(inst.get("town_id")) == str(municipality_id)]
        
        # Then get campuses for these institutions
        campuses = []
        url = f"{self.base_url}{self.api_prefix}/campuses/"
        
        async with session.get(url) as response:
            if response.status != 200:
                response.raise_for_status()
            
            all_campuses = await response.json()
            # Filter campuses by institution_id
            institution_ids = {inst["id"] for inst in municipality_institutions}
            campuses = [campus for campus in all_campuses if campus.get("institution_id") in institution_ids]
        
        return campuses
    
    async def _get_beneficiary_counts_for_campus(
        self, 
        session: aiohttp.ClientSession, 
        campus_id: str, 
        start_date: date, 
        end_date: date
    ) -> BeneficiaryCount:
        """Get beneficiary counts by meal type for a specific campus"""
        # Get all coverages for this campus
        url = f"{self.base_url}{self.api_prefix}/coverages/"
        
        async with session.get(url) as response:
            if response.status != 200:
                response.raise_for_status()
            
            all_coverages = await response.json()
        
        # Filter active coverages for this campus
        campus_coverages = [
            coverage for coverage in all_coverages 
            if str(coverage.get("campus_id")) == str(campus_id) and coverage.get("active", False)
        ]
        
        # Count by benefit_type_id (meal type)
        # Based on API docs: 1=desayuno, 2=almuerzo, 3=refrigerio
        breakfast_count = sum(1 for cov in campus_coverages if cov.get("benefit_type_id") == 1)
        lunch_count = sum(1 for cov in campus_coverages if cov.get("benefit_type_id") == 2)
        snack_count = sum(1 for cov in campus_coverages if cov.get("benefit_type_id") == 3)
        
        return BeneficiaryCount(
            breakfast=breakfast_count,
            lunch=lunch_count,
            snack=snack_count
        )


class MenuServiceClient:
    """Client for communicating with the Menu Service"""
    
    def __init__(self):
        self.base_url = settings.menu_service_url
        self.api_prefix = "/api/v1"
    
    async def get_scheduled_menus(
        self, 
        start_date: date, 
        end_date: date, 
        campus_ids: List[str]
    ) -> MenuServiceResponse:
        """
        Get scheduled menus for the specified period and campuses.
        
        This method will:
        1. Find active menu schedules that overlap with the date range
        2. For each schedule, get detailed menu information
        3. Extract recipes and ingredients for each dish
        4. Return structured daily menus with ingredient details
        """
        try:
            async with aiohttp.ClientSession() as session:
                # Get menu schedules that overlap with our date range
                schedules = await self._get_active_menu_schedules(session, start_date, end_date, campus_ids)
                
                daily_menus = []
                
                for schedule in schedules:
                    schedule_menus = await self._get_detailed_schedule_menus(session, schedule["_id"])
                    daily_menus.extend(schedule_menus)
                
                # Filter menus to only include our target campuses and date range
                filtered_menus = []
                for menu in daily_menus:
                    if (menu.location_id in campus_ids and 
                        start_date <= menu.menu_date <= end_date):
                        filtered_menus.append(menu)
                
                return MenuServiceResponse(
                    daily_menus=filtered_menus,
                    total_days=len(set(menu.menu_date for menu in filtered_menus))
                )
                
        except Exception as e:
            logger.error(f"Error getting scheduled menus: {str(e)}")
            raise ExternalServiceError(f"Failed to get menu data: {str(e)}")
    
    async def _get_active_menu_schedules(
        self, 
        session: aiohttp.ClientSession, 
        start_date: date, 
        end_date: date, 
        campus_ids: List[str]
    ) -> List[Dict[str, Any]]:
        """Get menu schedules that overlap with the date range"""
        url = f"{self.base_url}{self.api_prefix}/menu-schedules/"
        
        async with session.get(url) as response:
            if response.status != 200:
                response.raise_for_status()
            
            all_schedules = await response.json()
        
        # Filter schedules that overlap with our date range and cover our campuses
        relevant_schedules = []
        for schedule in all_schedules:
            schedule_start = date.fromisoformat(schedule["start_date"])
            schedule_end = date.fromisoformat(schedule["end_date"])
            
            # Check date overlap
            if (schedule_start <= end_date and schedule_end >= start_date):
                # Check if any of our target campuses are covered
                covered_campuses = {
                    loc["location_id"] for loc in schedule.get("coverage", [])
                    if loc.get("location_type") == "campus"
                }
                
                if any(campus_id in covered_campuses for campus_id in campus_ids):
                    relevant_schedules.append(schedule)
        
        return relevant_schedules
    
    async def _get_detailed_schedule_menus(
        self, 
        session: aiohttp.ClientSession, 
        schedule_id: str
    ) -> List[DailyMenu]:
        """Get detailed daily menus for a schedule"""
        url = f"{self.base_url}{self.api_prefix}/menu-schedules/{schedule_id}/detailed"
        
        async with session.get(url) as response:
            if response.status != 200:
                response.raise_for_status()
            
            schedule_data = await response.json()
        
        daily_menus = []
        
        for daily_menu_data in schedule_data.get("daily_menus", []):
            # Get dish details for each meal type
            breakfast_dishes = await self._get_dishes_with_recipes(session, daily_menu_data.get("breakfast", []))
            lunch_dishes = await self._get_dishes_with_recipes(session, daily_menu_data.get("lunch", []))
            snack_dishes = await self._get_dishes_with_recipes(session, daily_menu_data.get("snack", []))
            
            daily_menu = DailyMenu(
                location_id=daily_menu_data["location_id"],
                location_name=daily_menu_data["location_name"],
                location_type=daily_menu_data["location_type"],
                menu_date=date.fromisoformat(daily_menu_data["menu_date"]),
                breakfast=breakfast_dishes,
                lunch=lunch_dishes,
                snack=snack_dishes
            )
            daily_menus.append(daily_menu)
        
        return daily_menus
    
    async def _get_dishes_with_recipes(
        self, 
        session: aiohttp.ClientSession, 
        dish_list: List[Dict[str, Any]]
    ) -> List[DishInfo]:
        """Get detailed dish information including recipes"""
        dishes = []
        
        for dish_data in dish_list:
            dish_id = dish_data["id"]
            
            # Get full dish details including recipe
            url = f"{self.base_url}{self.api_prefix}/dishes/{dish_id}"
            
            async with session.get(url) as response:
                if response.status != 200:
                    logger.warning(f"Could not get dish {dish_id}: {response.status}")
                    continue
                
                full_dish_data = await response.json()
            
            # Extract ingredients from recipe
            ingredients = []
            recipe = full_dish_data.get("recipe", {})
            
            for ingredient_data in recipe.get("ingredients", []):
                # Get ingredient name
                ingredient_name = await self._get_ingredient_name(session, ingredient_data["ingredient_id"])
                
                ingredient = IngredientInfo(
                    ingredient_id=ingredient_data["ingredient_id"],
                    ingredient_name=ingredient_name,
                    quantity=ingredient_data["quantity"],
                    unit=ingredient_data["unit"]
                )
                ingredients.append(ingredient)
            
            # Create dish info with shrinkage factor (default 1.1 for 10% waste)
            dish_info = DishInfo(
                dish_id=dish_id,
                dish_name=full_dish_data["name"],
                ingredients=ingredients,
                shrinkage_factor=1.1  # Default 10% shrinkage factor
            )
            dishes.append(dish_info)
        
        return dishes
    
    async def _get_ingredient_name(self, session: aiohttp.ClientSession, ingredient_id: str) -> str:
        """Get ingredient name by ID"""
        url = f"{self.base_url}{self.api_prefix}/ingredients/{ingredient_id}"
        
        async with session.get(url) as response:
            if response.status == 200:
                ingredient_data = await response.json()
                return ingredient_data.get("name", f"Unknown Ingredient ({ingredient_id})")
            else:
                logger.warning(f"Could not get ingredient {ingredient_id}: {response.status}")
                return f"Unknown Ingredient ({ingredient_id})" 