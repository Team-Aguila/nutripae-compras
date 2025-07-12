import httpx
from fastapi import Depends, HTTPException, status, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List
import logging

from core.config import settings

# Configurar logging para debugging
logger = logging.getLogger(__name__)

security = HTTPBearer()

def require_permission(permission: str):
    """
    Crea una dependencia que verifica si el usuario tiene un permiso específico.
    
    Este módulo NO conoce nada sobre JWT o estructura de tokens.
    Solo pasa el token al servicio de auth y recibe SÍ/NO.
    
    Args:
        permission: El permiso requerido (ej: "nutripae-rh:create")
    
    Returns:
        Una función async que valida el permiso
    """
    async def permission_checker(
        request: Request,
        credentials: HTTPAuthorizationCredentials = Security(security)
    ):
        try:
            token = credentials.credentials
            
            # Obtener información del endpoint actual
            endpoint_path = request.url.path
            if endpoint_path.startswith(settings.API_PREFIX_STR):
                endpoint_path = endpoint_path[len(settings.API_PREFIX_STR):]
            
            endpoint = f"{settings.MODULE_IDENTIFIER}{endpoint_path}"
            method = request.method
            
            # Preparar el payload para el servicio auth
            auth_payload = {
                "endpoint": endpoint,
                "method": method,
                "required_permissions": [permission]
            }
            
            logger.info(f"Checking authorization for user with permission '{permission}' on endpoint '{endpoint}'")
            logger.info(f"NUTRIPAE_AUTH_URL: {settings.NUTRIPAE_AUTH_URL}")
            
            # Hacer request al servicio de auth
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    f"{settings.NUTRIPAE_AUTH_URL}/authorization/check-authorization",
                    headers={"Authorization": f"Bearer {token}"},
                    json=auth_payload
                )
                
                # Manejar diferentes códigos de respuesta del servicio auth
                if response.status_code == 401:
                    # Token inválido, expirado, o usuario no encontrado
                    error_detail = "Invalid or expired token"
                    try:
                        error_info = response.json()
                        error_detail = error_info.get("detail", error_detail)
                    except:
                        pass
                    
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail=error_detail,
                        headers={"WWW-Authenticate": "Bearer"},
                    )
                
                elif response.status_code == 403:
                    # Usuario válido pero sin permisos suficientes
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Access forbidden - insufficient permissions",
                    )
                
                elif response.status_code == 500:
                    # Error interno del servicio auth
                    logger.error(f"Auth service internal error: {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Authentication service error",
                    )
                
                elif response.status_code != 200:
                    # Cualquier otro error
                    logger.error(f"Unexpected auth service response: {response.status_code} - {response.text}")
                    raise HTTPException(
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                        detail="Authentication service unavailable",
                    )
                
                # Procesar respuesta exitosa
                auth_result = response.json()
                
                if not auth_result.get("authorized", False):
                    missing_perms = auth_result.get("missing_permissions", [])
                    logger.warning(f"User lacks permissions. Missing: {missing_perms}")
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"You do not have enough permissions. Missing: {', '.join(missing_perms)}",
                    )
                
                logger.info(f"Authorization successful for user {auth_result.get('user_email')}")
                
                # Retornamos solo la información mínima necesaria
                return {
                    "user_id": auth_result.get("user_id"),
                    "user_email": auth_result.get("user_email")
                }
                
        except httpx.TimeoutException:
            logger.error("Timeout connecting to authentication service")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service timeout",
            )
        except httpx.RequestError as e:
            logger.error(f"Request error to authentication service: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable",
            )
        except HTTPException:
            # Re-lanzar HTTPExceptions sin modificar
            raise
        except Exception as e:
            logger.error(f"Unexpected error in authorization: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Internal authorization error",
            )
    
    return permission_checker

# Dependencias específicas para cada tipo de operación
# Cada endpoint especifica exactamente qué permiso necesita
def require_create():
    return require_permission("nutripae-compras:create")

def require_read():
    return require_permission("nutripae-compras:read")

def require_list():
    return require_permission("nutripae-compras:list")

def require_update():
    return require_permission("nutripae-compras:update")

def require_delete():
    return require_permission("nutripae-compras:delete") 