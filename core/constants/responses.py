"""
Clase para estandarizar las respuestas HTTP de la API.
Centraliza la estructura de respuestas para mantener consistencia.
"""

from rest_framework.response import Response
from rest_framework import status


class APIResponse:
    """
    Generador de respuestas HTTP estandarizadas.
    Todas las respuestas siguen el formato:
    {
        "success": true/false,
        "message": "...",
        "data": {...} (opcional),
        "errors": {...} (opcional)
    }
    """
    
    @staticmethod
    def success(message, data=None, status_code=200):
        """
        Genera una respuesta exitosa estandarizada.
        
        Args:
            message (str): Mensaje descriptivo del éxito
            data (dict, optional): Datos adicionales a retornar
            status_code (int): Código HTTP (default: 200)
            
        Returns:
            Response: Objeto Response de DRF
            
        Example:
            return APIResponse.success(
                message="Usuario creado correctamente",
                data={"id": 1, "nombre": "Juan"},
                status_code=201
            )
        """
        response_data = {
            'success': True,
            'message': message
        }
        
        if data is not None:
            response_data.update(data)
        
        # Mapear códigos comunes
        status_map = {
            200: status.HTTP_200_OK,
            201: status.HTTP_201_CREATED,
            204: status.HTTP_204_NO_CONTENT,
        }
        
        http_status = status_map.get(status_code, status_code)
        return Response(response_data, status=http_status)
    
    @staticmethod
    def error(message, errors=None, status_code=400, **kwargs):
        """
        Genera una respuesta de error estandarizada.
        
        Args:
            message (str): Mensaje descriptivo del error
            errors (dict, optional): Detalles específicos de errores
            status_code (int): Código HTTP (default: 400)
            **kwargs: Campos adicionales (detail, code, etc.)
            
        Returns:
            Response: Objeto Response de DRF
            
        Example:
            return APIResponse.error(
                message="Error al crear usuario",
                errors={"email": "Ya existe"},
                status_code=400
            )
        """
        response_data = {
            'success': False,
            'message': message
        }
        
        if errors is not None:
            response_data['errors'] = errors
        
        # Agregar campos adicionales
        response_data.update(kwargs)
        
        # Mapear códigos comunes
        status_map = {
            400: status.HTTP_400_BAD_REQUEST,
            401: status.HTTP_401_UNAUTHORIZED,
            403: status.HTTP_403_FORBIDDEN,
            404: status.HTTP_404_NOT_FOUND,
            409: status.HTTP_409_CONFLICT,
            500: status.HTTP_500_INTERNAL_SERVER_ERROR,
        }
        
        http_status = status_map.get(status_code, status_code)
        return Response(response_data, status=http_status)
    
    @staticmethod
    def created(message, data=None):
        """Atajo para respuesta de creación exitosa (201)."""
        return APIResponse.success(message, data, status_code=201)
    
    @staticmethod
    def bad_request(message, errors=None):
        """Atajo para respuesta de petición inválida (400)."""
        return APIResponse.error(message, errors, status_code=400)
    
    @staticmethod
    def not_found(message):
        """Atajo para respuesta de recurso no encontrado (404)."""
        return APIResponse.error(message, status_code=404)
    
    @staticmethod
    def server_error(message, detail=None):
        """Atajo para error interno del servidor (500)."""
        kwargs = {}
        if detail:
            kwargs['detail'] = str(detail)
        return APIResponse.error(message, status_code=500, **kwargs)
    
    @staticmethod
    def unauthorized(message):
        """Atajo para respuesta no autorizada (401)."""
        return APIResponse.error(message, status_code=401)
    
    @staticmethod
    def forbidden(message):
        """Atajo para respuesta prohibida (403)."""
        return APIResponse.error(message, status_code=403)
