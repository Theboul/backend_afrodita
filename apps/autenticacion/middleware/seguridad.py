"""
Middlewares de seguridad para el sistema de autenticación.
"""
from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
from apps.autenticacion.utils.helpers import obtener_ip_cliente
from core.constants import Messages, SecurityConstants
import logging

logger = logging.getLogger(__name__)
SAFE_IPS = set(getattr(settings, 'IP_WHITELIST', []))


class JWTCookieAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware para autenticar usuarios a través de JWT en cookies.
    Extrae el token, lo valida y asigna el usuario autenticado al request.
    """
    def process_request(self, request):
        # No procesar si ya hay header Authorization
        if request.META.get("HTTP_AUTHORIZATION"):
            return None

        path = request.path or ""

        # Ignorar rutas que no son parte del API
        if not path.startswith("/api/"):
            # No intervenir en frontend, favicon, admin, etc.
            return None

        # Ignorar rutas públicas dentro del API (usar constantes)
        if any(path.startswith(r) for r in SecurityConstants.RUTAS_PUBLICAS_API):
            return None

        # Obtener token de cookie
        access_token = request.COOKIES.get("access_token")

        if access_token:
            try:
                request.META["HTTP_AUTHORIZATION"] = f"Bearer {access_token}"
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(access_token)
                user = jwt_auth.get_user(validated_token)
                request.user = user
                logger.debug(f"Usuario autenticado desde cookie: {user}")
            except (InvalidToken, AuthenticationFailed) as e:
                logger.warning(f"Token inválido en cookie: {e}")
                request.user = None
            except Exception as e:
                logger.error(f"Error al procesar JWT desde cookie: {e}")
                request.user = None
            return None

        # Si no hay token (en una ruta API protegida) → limpiar cookies
        response = JsonResponse(
            {"detail": Messages.UNAUTHORIZED},
            status=401,
        )
        response.delete_cookie("access_token", path="/")
        response.delete_cookie("refresh_token", path="/api/auth/refresh/")
        logger.info(f"Cookies limpiadas por token inválido en {path}")
        return response
    
    
class IPBlacklistMiddleware(MiddlewareMixin):
    """
    Middleware para bloquear IPs y ponerlas en la lista negra.
    """
    def process_request(self, request):
        # Importar aquí para evitar circular imports
        from apps.autenticacion.models import IPBlacklist
        
        ip = obtener_ip_cliente(request)
        
        if ip in SAFE_IPS:
            return None

        if IPBlacklist.esta_bloqueada(ip):
            logger.warning(f"Intento de acceso desde IP bloqueada: {ip}")
            return JsonResponse({
                'success': False,
                'error': Messages.IP_BLOCKED
            }, status=403)
        
        return None


class BruteForceProtectionMiddleware(MiddlewareMixin):
    """
    Middleware para protección contra ataques de fuerza bruta.
    Bloquea automáticamente IPs con demasiados intentos fallidos.
    
    NOTA: Los valores ahora se obtienen de SecurityConstants
    """
    # Usar valores desde SecurityConstants
    MAX_INTENTOS = SecurityConstants.MAX_INTENTOS_LOGIN
    VENTANA_TIEMPO = SecurityConstants.VENTANA_TIEMPO_MINUTOS

    def process_request(self, request):
        # Solo aplicar a endpoints de autenticación
        rutas_protegidas = [
            '/api/auth/login/', 
            '/api/usuarios/registro-cliente/',  # Registro desde usuarios
            '/api/usuarios/registro-roles/',    # Registro de roles
        ]
        
        if request.path not in rutas_protegidas:
            return None

        # Importar aquí para evitar circular imports
        from apps.autenticacion.models import LoginAttempt, IPBlacklist
        
        ip = obtener_ip_cliente(request)
        
        if not ip or ip in SAFE_IPS:
            return None

        # Verificar intentos fallidos recientes
        intentos_fallidos = LoginAttempt.obtener_intentos_fallidos_recientes(
            ip, 
            self.VENTANA_TIEMPO
        )

        if intentos_fallidos >= self.MAX_INTENTOS:
            logger.warning(
                f"IP bloqueada temporalmente por múltiples intentos fallidos: {ip} "
                f"({intentos_fallidos} intentos)"
            )
            
            # Agregar a blacklist automáticamente si no está
            if not IPBlacklist.esta_bloqueada(ip):
                IPBlacklist.objects.create(
                    ip=ip,
                    razon=f'Bloqueado automáticamente: {intentos_fallidos} intentos fallidos',
                    activa=True
                )
                logger.error(f"IP {ip} agregada a blacklist automáticamente")
            
            return JsonResponse({
                'success': False,
                'error': Messages.ACCOUNT_BLOCKED
            }, status=429)
        
        return None


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware para agregar headers de seguridad adicionales.
    NO sobrescribe headers de CORS que ya están configurados por django-cors-headers.
    """
    def process_response(self, request, response):
        # Solo agregar headers si no están ya presentes (no sobrescribir CORS)
        
        # Anti clickjacking (solo si no está configurado)
        if "X-Frame-Options" not in response:
            response["X-Frame-Options"] = "DENY"

        # Prevención de MIME sniffing
        if "X-Content-Type-Options" not in response:
            response["X-Content-Type-Options"] = "nosniff"

        # Protección básica XSS (para navegadores antiguos)
        if "X-XSS-Protection" not in response:
            response["X-XSS-Protection"] = "1; mode=block"

        # Política de referer
        if "Referrer-Policy" not in response:
            response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions Policy (reemplaza Feature-Policy)
        if "Permissions-Policy" not in response:
            response["Permissions-Policy"] = "geolocation=(), microphone=(), camera=(), payment=(), usb=()"

        # Política de contenido (CSP) - Relajada para permitir recursos externos
        # NO aplicar CSP restrictivo en API endpoints
        if not request.path.startswith('/api/') and "Content-Security-Policy" not in response:
            response["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "font-src 'self';"
            )

        # No cachear páginas sensibles (auth, admin)
        if any(seg in request.path for seg in ["auth", "admin"]):
            response["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response["Pragma"] = "no-cache"
            response["Expires"] = "0"

        # Forzar HTTPS si aplica
        if request.is_secure() and "Strict-Transport-Security" not in response:
            response["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains; preload"

        return response