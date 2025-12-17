"""
Clase para estandarizar las respuestas HTTP de la API.
Centraliza la estructura de respuestas para mantener consistencia.
"""

from rest_framework.response import Response
from rest_framework import status
from .mensajes import Messages


class APIResponse:
    """Helpers estandarizados para las respuestas del API."""

    @staticmethod
    def success(message=None, data=None, status_code=200):
        """Respuesta exitosa con mensaje opcional."""
        if message is None:
            message = Messages.OPERATION_SUCCESS

        response_data = {
            'success': True,
            'message': message
        }
        if data is not None:
            response_data['data'] = data

        status_map = {
            200: status.HTTP_200_OK,
            201: status.HTTP_201_CREATED,
            204: status.HTTP_204_NO_CONTENT,
        }
        http_status = status_map.get(status_code, status_code)
        return Response(response_data, status=http_status)

    @staticmethod
    def error(message=None, errors=None, status_code=400, **kwargs):
        """Respuesta de error generica."""
        if message is None:
            message = Messages.OPERATION_FAILED

        response_data = {
            'success': False,
            'message': message
        }
        if errors is not None:
            response_data['errors'] = errors
        response_data.update(kwargs)

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
    def created(message=None, data=None):
        """Atajo para respuestas 201."""
        return APIResponse.success(message, data, status_code=201)

    @staticmethod
    def bad_request(message=None, errors=None):
        """Atajo para respuestas 400."""
        if message is None:
            message = Messages.INVALID_DATA
        return APIResponse.error(message, errors, status_code=400)

    @staticmethod
    def not_found(message=None):
        """Atajo para respuestas 404."""
        if message is None:
            message = Messages.NOT_FOUND
        return APIResponse.error(message, status_code=404)

    @staticmethod
    def server_error(message=None, detail=None):
        """Atajo para respuestas 500."""
        if message is None:
            message = Messages.SERVER_ERROR
        kwargs = {}
        if detail:
            kwargs['detail'] = str(detail)
        return APIResponse.error(message, status_code=500, **kwargs)

    @staticmethod
    def unauthorized(message=None):
        """Atajo para respuestas 401."""
        if message is None:
            message = Messages.UNAUTHORIZED
        return APIResponse.error(message, status_code=401)

    @staticmethod
    def forbidden(message=None):
        """Atajo para respuestas 403."""
        if message is None:
            message = Messages.FORBIDDEN
        return APIResponse.error(message, status_code=403)
