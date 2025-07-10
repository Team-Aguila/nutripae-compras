from datetime import date
from typing import List, Dict, Optional, Union, Any
from pydantic import BaseModel, Field


class Coverage(BaseModel):
    """Coverage specification for the calculation"""
    type: str = Field(..., description="Type of coverage: 'municipality' or 'campus'")
    ids: List[Union[int, str]] = Field(..., description="List of municipality or campus IDs")


class PurchaseCalculationRequest(BaseModel):
    """Request model for purchase calculation"""
    start_date: date = Field(..., description="Start date of the calculation period")
    end_date: date = Field(..., description="End date of the calculation period")
    coverage: Coverage = Field(..., description="Coverage specification")


class CalculationPeriod(BaseModel):
    """Period information for the calculation"""
    start_date: date
    end_date: date


class PurchaseListItem(BaseModel):
    """Individual item in the purchase list"""
    ingredient_name: str = Field(..., description="Name of the ingredient")
    ingredient_id: str = Field(..., description="ID of the ingredient")
    unit: str = Field(..., description="Unit of measurement")
    total_gross_quantity: float = Field(..., description="Total gross quantity needed")
    current_inventory: float = Field(default=0.0, description="Current inventory level")
    safety_stock: float = Field(default=0.0, description="Safety stock level")
    net_quantity_to_purchase: float = Field(..., description="Net quantity to purchase")


class PurchaseCalculationResponse(BaseModel):
    """Response model for purchase calculation"""
    calculation_period: CalculationPeriod
    purchase_list: List[PurchaseListItem]
    total_ingredients: int = Field(..., description="Total number of unique ingredients")
    calculation_summary: Dict[str, Any] = Field(default_factory=dict, description="Additional calculation metadata")


# External service models
class BeneficiaryCount(BaseModel):
    """Beneficiary count by meal type"""
    breakfast: int = Field(default=0)
    lunch: int = Field(default=0) 
    snack: int = Field(default=0)


class CampusInfo(BaseModel):
    """Campus information with beneficiary counts"""
    id: str
    name: str
    location_type: str = "campus"
    beneficiary_counts: BeneficiaryCount


class CoverageServiceResponse(BaseModel):
    """Response from coverage service"""
    campuses: List[CampusInfo]
    total_campuses: int


class IngredientInfo(BaseModel):
    """Ingredient information from menu service"""
    ingredient_id: str
    ingredient_name: str
    quantity: float
    unit: str


class DishInfo(BaseModel):
    """Dish information with recipe"""
    dish_id: str
    dish_name: str
    ingredients: List[IngredientInfo]
    shrinkage_factor: Optional[float] = Field(default=1.0, description="Shrinkage/waste factor")


class DailyMenu(BaseModel):
    """Daily menu information"""
    location_id: str
    location_name: str
    location_type: str
    menu_date: date
    breakfast: List[DishInfo] = Field(default_factory=list)
    lunch: List[DishInfo] = Field(default_factory=list)
    snack: List[DishInfo] = Field(default_factory=list)


class MenuServiceResponse(BaseModel):
    """Response from menu service"""
    daily_menus: List[DailyMenu]
    total_days: int


# Calculation intermediate models
class IngredientCalculation(BaseModel):
    """Intermediate calculation for an ingredient"""
    ingredient_id: str
    ingredient_name: str
    unit: str
    total_gross_quantity: float = 0.0
    daily_details: List[Dict[str, Any]] = Field(default_factory=list)


class DailyIngredientNeed(BaseModel):
    """Daily ingredient need calculation"""
    ingredient_id: str
    ingredient_name: str
    campus_id: str
    campus_name: str
    meal_type: str
    beneficiary_count: int
    portion_size: float
    unit: str
    shrinkage_factor: float
    daily_need: float
    gross_need: float
    date: date 