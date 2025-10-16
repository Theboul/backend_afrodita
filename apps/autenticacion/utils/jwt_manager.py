from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class JWTManager:
    @staticmethod
    def generar_tokens(usuario):
        """
        Genera access y refresh tokens para un usuario.
        """
        refresh = RefreshToken.for_user(usuario)
        
        # Agregar claims personalizados si es necesario
        refresh['nombre'] = usuario.nombre_usuario
        refresh['rol'] = usuario.id_rol.nombre if hasattr(usuario, 'id_rol') else None
        
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }

    @staticmethod
    def set_tokens_in_cookies(response, tokens):
        """
        Almacena tokens en cookies HttpOnly seguras.
        """
        is_production = not settings.DEBUG
        
        # Access token - Corta duración, disponible para todas las rutas
        response.set_cookie(
            key="access_token",
            value=tokens["access"],
            httponly=True,  # Protección XSS
            secure=is_production,  # Solo HTTPS en producción
            samesite="Strict",  # Protección CSRF
            max_age=60 * 30,  # 30 minutos
            path="/",  # Disponible en todo el sitio
        )
        
        # Refresh token - Larga duración, scope limitado
        response.set_cookie(
            key="refresh_token",
            value=tokens["refresh"],
            httponly=True,
            secure=is_production,
            samesite="Strict",
            max_age=60 * 60 * 24 * 7,  # 7 días
            path="/api/auth/refresh/",  # Coincide con las URLs configuradas
        )
        
        return response

    @staticmethod
    def get_token_from_cookie(request, token_type="access"):
        """
        Extrae token desde cookies de forma segura.
        """
        cookie_name = f"{token_type}_token"
        return request.COOKIES.get(cookie_name)

    @staticmethod
    def clear_cookies(response):
        """
        Elimina las cookies de autenticación.
        """
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/api/auth/refresh/")
        return response

    @staticmethod
    def invalidar_refresh_token(refresh_token_str):
        """
        Invalida un refresh token agregándolo a la blacklist.
        Requiere djangorestframework-simplejwt[blacklist] instalado.
        """
        try:
            token = RefreshToken(refresh_token_str)
            token.blacklist()
            return True
        except TokenError:
            # Token ya inválido, expirado o blacklisted
            return False
        except Exception as e:
            # Loguear el error en producción
            logger.error(f"Error al invalidar token: {e}")
            return False

    @staticmethod
    def validar_y_refrescar_token(refresh_token_str):
        """
        Valida un refresh token y genera un nuevo access token.
        Opcionalmente puede generar un nuevo refresh token si ROTATE_REFRESH_TOKENS=True.
        """
        try:
            refresh = RefreshToken(refresh_token_str)
            
            # Generar nuevo access token
            new_access = str(refresh.access_token)
            
            # Verificar si se debe rotar el refresh token
            rotate_refresh = getattr(settings, 'ROTATE_REFRESH_TOKENS', False)
            
            if rotate_refresh:
                # Blacklist el token anterior
                refresh.blacklist()
                # Crear un nuevo refresh token
                usuario = refresh.payload.get('user_id')
                if usuario:
                    from apps.usuarios.models import Usuario
                    user_obj = Usuario.objects.get(id=usuario)
                    new_refresh = RefreshToken.for_user(user_obj)
                    new_refresh['nombre'] = user_obj.nombre_usuario
                    new_refresh['rol'] = user_obj.id_rol.nombre if hasattr(user_obj, 'id_rol') else None
                    refresh_token_str = str(new_refresh)
                else:
                    refresh_token_str = str(refresh)
            else:
                refresh_token_str = str(refresh)
            
            tokens = {
                "access": new_access,
                "refresh": refresh_token_str
            }
            
            logger.info("Token refrescado exitosamente")
            return tokens
            
        except TokenError as e:
            logger.warning(f"Token inválido al refrescar: {str(e)}")
            raise Exception(f"Token inválido: {str(e)}")
        except Exception as e:
            logger.error(f"Error inesperado al refrescar token: {str(e)}")
            raise Exception(f"Error al procesar token: {str(e)}")
