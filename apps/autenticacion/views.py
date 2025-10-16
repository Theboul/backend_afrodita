#autenticacion/views.py
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from apps.autenticacion.models import LoginAttempt
from .serializers import LoginSerializer, RefreshTokenSerializer
from .utils.jwt_manager import JWTManager
from .utils.throttling import LoginRateThrottle
from apps.bitacora.signals import (
    login_exitoso, login_fallido, logout_realizado, logout_error
)
import logging

logger = logging.getLogger(__name__)

@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([LoginRateThrottle])
def login_usuario(request):
    """
    Endpoint para autenticación de usuarios.
    Protegido contra fuerza bruta con rate limiting.
    """
    serializer = LoginSerializer(data=request.data)

    if serializer.is_valid():
        usuario = serializer.validated_data["usuario"]
        ip_address = obtener_ip_cliente(request)

        # Generar tokens JWT
        tokens = JWTManager.generar_tokens(usuario)

        # Actualizar último acceso
        usuario.last_login = timezone.now()
        usuario.save(update_fields=["last_login"])

        # Registrar intento exitoso
        LoginAttempt.objects.create(usuario=usuario, ip=ip_address, exitoso=True)

        login_exitoso.send(sender=None, usuario=usuario, ip=ip_address)

        logger.info(f"Login exitoso - Usuario: {usuario.nombre_usuario}, IP: {ip_address}")

        # Preparar respuesta
        response = Response({
            "success": True,
            "message": f"Bienvenido {usuario.nombre_usuario}",
            "user": {
                "id": usuario.id_usuario,
                "username": usuario.nombre_usuario,
                "email": usuario.correo,
                "rol": usuario.id_rol.nombre if hasattr(usuario, 'id_rol') else None,
            }
        }, status=status.HTTP_200_OK)

        # Establecer tokens en cookies seguras
        return JWTManager.set_tokens_in_cookies(response, tokens)

    # Registrar intento fallido
    ip_address = obtener_ip_cliente(request)
    LoginAttempt.objects.create(usuario=None, ip=ip_address, exitoso=False)

    login_fallido.send(sender=None, ip=ip_address, credencial=request.data.get("credencial"))
    logger.warning(f"Login fallido - IP: {ip_address}")

    return Response({
        "success": False,
        "errors": serializer.errors
    }, status=status.HTTP_400_BAD_REQUEST)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout_usuario(request):
    """
    Endpoint para cerrar sesión.
    Invalida el refresh token y limpia las cookies.
    """
    usuario = request.user
    ip_address = obtener_ip_cliente(request)
    try:
        # Obtener el refresh token desde las cookies
        refresh_token = JWTManager.get_token_from_cookie(request, "refresh")
        
        # Intentar invalidar el token
        if refresh_token:
            JWTManager.invalidar_refresh_token(refresh_token)
        logout_realizado.send(sender=None, usuario=usuario, ip=ip_address)
        logger.info(f"Logout exitoso - Usuario: {usuario.nombre_usuario}, IP: {ip_address}")
        
        response = Response({
            "success": True,
            "message": "Sesión cerrada correctamente."
        }, status=status.HTTP_200_OK)
        
        return JWTManager.clear_cookies(response)
    
    except Exception as e:
        logout_error.send(sender=None, usuario=usuario, ip=ip_address, error=str(e))
        logger.error(f"Error en logout ({usuario.nombre_usuario}): {str(e)}")

        response = Response({
            "success": True,
            "message": "Sesión cerrada correctamente."
        }, status=status.HTTP_200_OK)
        return JWTManager.clear_cookies(response)


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Endpoint para refrescar el access token usando el refresh token.
    """
    try:
        # Obtener refresh token desde cookies
        refresh_token = JWTManager.get_token_from_cookie(request, "refresh")
        
        serializer = RefreshTokenSerializer(
            data=request.data,
            context={'refresh_token': refresh_token}
        )
        
        if not serializer.is_valid():
            return Response({
                "success": False,
                "error": "Refresh token no válido o expirado."
            }, status=status.HTTP_401_UNAUTHORIZED)

        # Generar nuevos tokens
        tokens = JWTManager.validar_y_refrescar_token(
            serializer.validated_data['refresh']
        )

        response = Response({
            "success": True,
            "message": "Token refrescado correctamente."
        }, status=status.HTTP_200_OK)

        # Actualizar cookies con nuevos tokens
        return JWTManager.set_tokens_in_cookies(response, tokens)

    except Exception as e:
        logger.error(f"Error al refrescar token: {str(e)}")
        return Response({
            "success": False,
            "error": "No se pudo refrescar el token."
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def verificar_sesion(request):
    """
    Endpoint para verificar si la sesión del usuario es válida.
    Útil para verificación en el frontend.
    """
    return Response({
        "success": True,
        "user": {
            "id": request.user.id,
            "username": request.user.nombre_usuario,
            "email": request.user.correo,
            "rol": request.user.id_rol.nombre if hasattr(request.user, 'id_rol') else None,
        }
    }, status=status.HTTP_200_OK)


def obtener_ip_cliente(request):
    """
    Obtiene la IP real del cliente considerando proxies y balanceadores.
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip