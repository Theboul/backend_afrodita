"""
Middlewares de seguridad para el sistema de autenticación.
"""
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed
import logging

logger = logging.getLogger(__name__)


class JWTCookieAuthenticationMiddleware(MiddlewareMixin):
    """
    Middleware para autenticar usuarios a través de JWT en cookies.
    Extrae el token, lo valida y asigna el usuario autenticado al request.
    """
    def process_request(self, request):
        # Si ya hay un header Authorization, no hacer nada
        if request.META.get('HTTP_AUTHORIZATION'):
            return None

        # Obtener token desde cookie
        access_token = request.COOKIES.get('access_token')
        
        if access_token:
            try:
                # 1. Agregar al header Authorization
                request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
                
                # 2. CRÍTICO: Validar y autenticar el usuario
                jwt_auth = JWTAuthentication()
                validated_token = jwt_auth.get_validated_token(access_token)
                user = jwt_auth.get_user(validated_token)
                
                # 3. Asignar usuario autenticado al request
                request.user = user
                
                logger.debug(f"Usuario autenticado desde cookie: {user.nombre_usuario}")
                
            except (InvalidToken, AuthenticationFailed) as e:
                # Token inválido o expirado - no hacer nada, usuario será AnonymousUser
                logger.debug(f"Token inválido en cookie: {str(e)}")
                pass
            except Exception as e:
                logger.error(f"Error al procesar JWT desde cookie: {str(e)}")
                pass
        
        return None


class IPBlacklistMiddleware(MiddlewareMixin):
    """
    Middleware para bloquear IPs en la lista negra.
    """
    def process_request(self, request):
        # Importar aquí para evitar circular imports
        from apps.autenticacion.models import IPBlacklist
        
        ip = self.get_client_ip(request)
        
        if IPBlacklist.esta_bloqueada(ip):
            logger.warning(f"Intento de acceso desde IP bloqueada: {ip}")
            return JsonResponse({
                'success': False,
                'error': 'Acceso denegado.',
                'detail': 'Tu dirección IP ha sido bloqueada.'
            }, status=403)
        
        return None

    @staticmethod
    def get_client_ip(request):
        """Obtiene la IP real del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class BruteForceProtectionMiddleware(MiddlewareMixin):
    """
    Middleware para protección contra ataques de fuerza bruta.
    Bloquea automáticamente IPs con demasiados intentos fallidos.
    """
    MAX_INTENTOS = 10  # Máximo de intentos fallidos
    VENTANA_TIEMPO = 30  # En minutos

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
        
        ip = self.get_client_ip(request)
        
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
                'error': 'Demasiados intentos fallidos.',
                'detail': f'Has excedido el límite de intentos. Tu IP ha sido bloqueada.'
            }, status=429)
        
        return None

    @staticmethod
    def get_client_ip(request):
        """Obtiene la IP real del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class SecurityHeadersMiddleware(MiddlewareMixin):
    """
    Middleware para agregar headers de seguridad adicionales.
    """
    def process_response(self, request, response):
        # Prevenir clickjacking
        response['X-Frame-Options'] = 'DENY'
        
        # Prevenir MIME type sniffing
        response['X-Content-Type-Options'] = 'nosniff'
        
        # XSS Protection (legacy browsers)
        response['X-XSS-Protection'] = '1; mode=block'
        
        # Referrer Policy
        response['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        # Permissions Policy (reemplaza Feature-Policy)
        response['Permissions-Policy'] = 'geolocation=(), microphone=(), camera=(), payment=(), usb=()'
        
        # Content Security Policy básico
        response['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'"
        
        # Controlar cache de páginas sensibles
        if 'auth' in request.path or 'admin' in request.path:
            response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
            response['Pragma'] = 'no-cache'
            response['Expires'] = '0'
        
        # Strict Transport Security (solo si usas HTTPS)
        if request.is_secure():
            response['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
        
        return response