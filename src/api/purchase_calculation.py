import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from models.purchase_calculation import (
    PurchaseCalculationRequest,
    PurchaseCalculationResponse
)
from services.calculation_service import CalculationService
from services.external_services import ExternalServiceError
from core.dependencies import require_create, require_read, require_list

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/calculate",
    response_model=PurchaseCalculationResponse,
    summary="Calculate Purchase Needs",
    description="Calculate required ingredient quantities for a future period based on scheduled menus and beneficiary coverage"
)
async def calculate_purchase_needs(
    request: PurchaseCalculationRequest,
    current_user: dict = Depends(require_create()),
) -> PurchaseCalculationResponse:
    """
    Calculate the required quantities of ingredients for a future period.
    
    This endpoint performs the following steps:
    1. Retrieves campus coverage and beneficiary counts from the Coverage Service
    2. Gets scheduled menus and recipes from the Menu Service  
    3. Calculates daily ingredient needs based on portions and beneficiary counts
    4. Applies shrinkage factors to account for waste
    5. Sums gross quantities across all days and campuses
    6. Subtracts current inventory levels
    7. Returns a detailed purchase list with net quantities needed
    
    **Input Parameters:**
    - `start_date`: Beginning of the calculation period (YYYY-MM-DD)
    - `end_date`: End of the calculation period (YYYY-MM-DD)  
    - `coverage`: Specification of coverage area (municipalities or campuses)
    
    **Coverage Types:**
    - `municipality`: Provide list of municipality IDs to include all campuses in those municipalities
    - `campus`: Provide list of specific campus IDs to analyze
    
    **Response:**
    - Detailed purchase list with ingredient names, quantities, and net purchase needs
    - Calculation summary with metadata about the analysis
    - All quantities converted to grams for consistency
    """
    try:
        logger.info(f"Received purchase calculation request for period {request.start_date} to {request.end_date}")
        logger.info(f"Coverage: {request.coverage.type} with {len(request.coverage.ids)} locations")
        
        calculation_service = CalculationService()
        result = await calculation_service.calculate_purchase_needs(request)
        
        logger.info(f"Purchase calculation completed successfully. {result.total_ingredients} ingredients analyzed.")
        
        return result
        
    except ExternalServiceError as e:
        logger.error(f"External service error in purchase calculation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"External service error: {str(e)}"
        )
    except ValueError as e:
        logger.error(f"Validation error in purchase calculation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Validation error: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Unexpected error in purchase calculation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Internal server error: {str(e)}"
        )


@router.get(
    "/health",
    summary="Health Check",
    description="Check if the purchase calculation service is healthy"
)
async def health_check(
    current_user: dict = Depends(require_read()),
):
    """Health check endpoint for purchase calculation service"""
    return {
        "status": "healthy",
        "service": "Purchase Calculation Service",
        "version": "1.0.0"
    }


@router.get(
    "/coverage-info/{coverage_type}",
    summary="Get Coverage Information",
    description="Get information about available coverage areas (municipalities or campuses)"
)
async def get_coverage_info(
    coverage_type: str,
    current_user: dict = Depends(require_read()),
):
    """
    Get information about available coverage areas.
    
    Args:
        coverage_type: Either 'municipality' or 'campus'
    
    Returns:
        List of available locations with IDs and names
    """
    if coverage_type not in ["municipality", "campus"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Coverage type must be either 'municipality' or 'campus'"
        )
    
    try:
        from ..services.external_services import CoverageServiceClient
        import aiohttp
        
        coverage_client = CoverageServiceClient()
        
        async with aiohttp.ClientSession() as session:
            if coverage_type == "municipality":
                # Get towns/municipalities
                url = f"{coverage_client.base_url}{coverage_client.api_prefix}/towns/"
                async with session.get(url) as response:
                    if response.status == 200:
                        towns = await response.json()
                        return {
                            "coverage_type": "municipality",
                            "locations": [
                                {"id": town["id"], "name": town["name"]} 
                                for town in towns
                            ]
                        }
                    else:
                        response.raise_for_status()
            
            else:  # campus
                # Get campuses
                url = f"{coverage_client.base_url}{coverage_client.api_prefix}/campuses/"
                async with session.get(url) as response:
                    if response.status == 200:
                        campuses = await response.json()
                        return {
                            "coverage_type": "campus",
                            "locations": [
                                {"id": campus["id"], "name": campus["name"]} 
                                for campus in campuses
                            ]
                        }
                    else:
                        response.raise_for_status()
                        
    except Exception as e:
        logger.error(f"Error getting coverage info: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving coverage information: {str(e)}"
        ) 