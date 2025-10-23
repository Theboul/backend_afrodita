import logging
import ipaddress
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings
from apps.bitacora.signals import vista_visitada

logger = logging.getLogger(__name__)

class AuditoriaMiddleware(MiddlewareMixin):
    """
    Middleware que registra automáticamente el acceso de usuarios autenticados
    a cualquier vista del sistema mediante la señal `vista_visitada`.
    
    IMPORTANTE: Debe estar DESPUÉS de JWTCookieAuthenticationMiddleware en settings.py
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        """
        Registra acceso tanto de usuarios autenticados como anónimos.
        Para anónimos, solo registra vistas importantes (productos, categorías, etc.)
        """
        path = request.path.lower()
        
        # Ignorar endpoints administrativos y estáticos siempre
        if any(excluido in path for excluido in [
            '/admin',
            '/static',
            '/media',
            '/favicon.ico'
        ]):
            return None

        try:
            ip = self.get_client_ip(request)
            
            # CRÍTICO: Verificar que el usuario esté autenticado correctamente
            # hasattr previene errores si request.user no existe
            if hasattr(request, 'user') and request.user.is_authenticated:
                # Usuario autenticado - registrar todas las vistas importantes
                if not any(excluido in path for excluido in [
                    '/api/auth/login',      # Ya se registra en views.py
                    '/api/auth/logout',     # Ya se registra en views.py
                    '/api/auth/refresh',    # Token refresh no es relevante
                    '/api/auth/verificar'   # Verificación de sesión no es relevante
                ]):
                    # DEBUG: Loguear para verificar que el usuario está autenticado
                    logger.debug(
                        f"Registrando vista para usuario autenticado: "
                        f"{request.user.nombre_usuario} -> {request.path}"
                    )
                    
                    vista_visitada.send(
                        sender=self.__class__,
                        usuario=request.user,
                        ip=ip,
                        ruta=request.path
                    )
            else:
                # Usuario anónimo - solo registrar vistas importantes para analytics
                if self._es_vista_importante_para_anonimos(path):
                    logger.debug(f"Registrando vista anónima: {request.path}")
                    
                    from apps.bitacora.signals import vista_anonima_visitada
                    vista_anonima_visitada.send(
                        sender=self.__class__,
                        ip=ip,
                        ruta=request.path,
                        user_agent=request.META.get('HTTP_USER_AGENT', '')
                    )
                    
        except Exception as e:
            # Nunca debe romper el flujo de la vista
            logger.error(f"Error en AuditoriaMiddleware: {str(e)}")
            logger.exception(e)  # Esto loguea el stacktrace completo

        return None

    def _es_vista_importante_para_anonimos(self, path):
        """
        Determina si una vista es importante para trackear en usuarios anónimos.
        Solo rastrea vistas que aporten valor al negocio.
        """
        rutas_importantes = [
            '/api/productos',           # Vista de productos
            '/api/categoria',           # Vista de categorías  
            '/dashboard',               # Dashboard
            '/preview',                 # Preview
            '/',                        # Página principal
        ]
        
        return any(ruta in path for ruta in rutas_importantes)

    def get_client_ip(self, request):
        """
        Obtiene la IP real del cliente de forma segura, considerando proxies confiables.
        
        ACTUALIZADO: Soporte para Cloudflare, Render y otros CDNs.
        
        Prioridad de headers:
        1. CF-Connecting-IP (Cloudflare) - Más confiable
        2. True-Client-IP (Algunos CDNs)
        3. X-Real-IP (Nginx)
        4. X-Forwarded-For (Estándar)
        5. REMOTE_ADDR (Fallback)
        
        Returns:
            str: IP del cliente o None si no se puede determinar
        """
        # Obtener configuración
        trusted_proxy_count = getattr(settings, 'TRUSTED_PROXY_COUNT', 0)
        trusted_proxy_ips = getattr(settings, 'TRUSTED_PROXY_IPS', [])
        log_suspicious = getattr(settings, 'LOG_SUSPICIOUS_IPS', True)
        
        # Obtener REMOTE_ADDR (siempre disponible)
        remote_addr = request.META.get('REMOTE_ADDR')
        
        # PRIORIDAD 1: Cloudflare envía la IP real en CF-Connecting-IP
        # Este header es MÁS CONFIABLE que X-Forwarded-For cuando usas Cloudflare
        cf_connecting_ip = request.META.get('HTTP_CF_CONNECTING_IP')
        if cf_connecting_ip and self._is_valid_ip(cf_connecting_ip):
            logger.debug(f"IP obtenida de CF-Connecting-IP (Cloudflare): {cf_connecting_ip}")
            return cf_connecting_ip
        
        # PRIORIDAD 2: True-Client-IP (usado por algunos CDNs)
        true_client_ip = request.META.get('HTTP_TRUE_CLIENT_IP')
        if true_client_ip and self._is_valid_ip(true_client_ip):
            logger.debug(f"IP obtenida de True-Client-IP: {true_client_ip}")
            return true_client_ip
        
        # PRIORIDAD 3: X-Real-IP (usado por Nginx)
        x_real_ip = request.META.get('HTTP_X_REAL_IP')
        if x_real_ip and self._is_valid_ip(x_real_ip):
            logger.debug(f"IP obtenida de X-Real-IP: {x_real_ip}")
            return x_real_ip
        
        # Si no hay proxies configurados, usar directamente REMOTE_ADDR
        if trusted_proxy_count == 0:
            logger.debug(f"Sin proxies configurados, usando REMOTE_ADDR: {remote_addr}")
            return remote_addr
        
        # PRIORIDAD 4: X-Forwarded-For (estándar pero menos confiable)
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        
        # Si no hay X-Forwarded-For pero esperamos proxies
        if not x_forwarded_for:
            if log_suspicious:
                logger.warning(
                    f"Se esperaban {trusted_proxy_count} proxies pero no hay "
                    f"X-Forwarded-For. Usando REMOTE_ADDR: {remote_addr}"
                )
            return remote_addr
        
        # Parsear la cadena de IPs
        ips = [ip.strip() for ip in x_forwarded_for.split(',')]
        
        # Validar que haya suficientes IPs en la cadena
        if len(ips) <= trusted_proxy_count:
            if log_suspicious:
                logger.warning(
                    f"X-Forwarded-For tiene menos IPs ({len(ips)}) de las esperadas "
                    f"({trusted_proxy_count + 1}): {x_forwarded_for}. "
                    f"Posible intento de spoofing. Usando REMOTE_ADDR: {remote_addr}"
                )
            return remote_addr
        
        # Extraer la IP del cliente
        client_ip_index = -(trusted_proxy_count + 1)
        client_ip = ips[client_ip_index]
        
        # Validar que sea una IP válida
        if not self._is_valid_ip(client_ip):
            if log_suspicious:
                logger.warning(
                    f"IP del cliente inválida en X-Forwarded-For: '{client_ip}'. "
                    f"Cadena completa: {x_forwarded_for}. "
                    f"Usando REMOTE_ADDR: {remote_addr}"
                )
            return remote_addr
        
        # Si hay lista de IPs de proxies confiables, validar REMOTE_ADDR
        if trusted_proxy_ips and remote_addr not in trusted_proxy_ips:
            if log_suspicious:
                logger.warning(
                    f"REMOTE_ADDR ({remote_addr}) no está en la lista de proxies "
                    f"confiables. Posible intento de bypass. "
                    f"X-Forwarded-For: {x_forwarded_for}"
                )
            return remote_addr
        
        # Todo validado, retornar la IP del cliente
        logger.debug(
            f"IP del cliente extraída de X-Forwarded-For: {client_ip} "
            f"(Cadena completa: {x_forwarded_for})"
        )
        return client_ip
    
    def _is_valid_ip(self, ip_string):
        """
        Valida que una cadena sea una dirección IP válida (IPv4 o IPv6).
        
        Args:
            ip_string (str): String a validar
            
        Returns:
            bool: True si es una IP válida, False en caso contrario
        """
        try:
            ipaddress.ip_address(ip_string)
            return True
        except ValueError:
            return False