"""
Utilidades compartidas para la app de autenticación.
Centraliza funciones reutilizables para evitar duplicación de código.
"""
import ipaddress
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def obtener_ip_cliente(request):
    """
    Obtiene la dirección IP real del cliente de forma segura, considerando proxies confiables.
    
    VERSIÓN COMPLETA con soporte para:
    - Cloudflare (CF-Connecting-IP)
    - CDNs (True-Client-IP)
    - Nginx (X-Real-IP)
    - Proxies estándar (X-Forwarded-For)
    - Validación de IPs confiables
    - Detección de spoofing
    
    Prioridad de headers:
    1. CF-Connecting-IP (Cloudflare) - Más confiable
    2. True-Client-IP (Algunos CDNs)
    3. X-Real-IP (Nginx)
    4. X-Forwarded-For (Estándar)
    5. REMOTE_ADDR (Fallback)
    
    Args:
        request: Objeto HttpRequest de Django
        
    Returns:
        str: Dirección IP del cliente o None si no se puede determinar
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
    if cf_connecting_ip and _is_valid_ip(cf_connecting_ip):
        logger.debug(f"IP obtenida de CF-Connecting-IP (Cloudflare): {cf_connecting_ip}")
        return cf_connecting_ip
    
    # PRIORIDAD 2: True-Client-IP (usado por algunos CDNs)
    true_client_ip = request.META.get('HTTP_TRUE_CLIENT_IP')
    if true_client_ip and _is_valid_ip(true_client_ip):
        logger.debug(f"IP obtenida de True-Client-IP: {true_client_ip}")
        return true_client_ip
    
    # PRIORIDAD 3: X-Real-IP (usado por Nginx)
    x_real_ip = request.META.get('HTTP_X_REAL_IP')
    if x_real_ip and _is_valid_ip(x_real_ip):
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
    if not _is_valid_ip(client_ip):
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


def _is_valid_ip(ip_string):
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


def es_usuario_anonimo(request):
    """
    Verifica si el usuario de la petición es anónimo o no está autenticado.
    
    Args:
        request: Objeto HttpRequest de Django
        
    Returns:
        bool: True si el usuario no está autenticado, False en caso contrario
    """
    return not request.user or request.user.is_anonymous
