# apps/bitacora/utils.py
"""
Utilidades adicionales para la bitácora.
Funciones de conveniencia para casos específicos.
"""
import logging
from apps.bitacora.services.logger import AuditoriaLogger

logger = logging.getLogger(__name__)


def log_search_activity(query, ip=None, usuario=None):
    """
    Registra búsquedas realizadas por usuarios (registrados o anónimos).
    
    Args:
        query (str): Término de búsqueda
        ip (str): IP del usuario
        usuario (Usuario, optional): Usuario si está logueado
    """
    if usuario:
        accion = "SEARCH"
        descripcion = f"Búsqueda realizada: '{query}'"
    else:
        accion = "ANONYMOUS_SEARCH"
        descripcion = f"Búsqueda anónima: '{query}'"
    
    return AuditoriaLogger.registrar_evento(
        accion=accion,
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )


def log_product_interaction(producto_id, accion_tipo, ip=None, usuario=None):
    """
    Registra interacciones específicas con productos.
    
    Args:
        producto_id (int): ID del producto
        accion_tipo (str): 'view', 'add_to_cart', 'purchase', etc.
        ip (str): IP del usuario
        usuario (Usuario, optional): Usuario si está logueado
    """
    if usuario:
        accion = "PRODUCT_VIEW" if accion_tipo == 'view' else "PRODUCT_INTERACTION"
        descripcion = f"Usuario {usuario.nombre_usuario} - {accion_tipo} producto ID: {producto_id}"
    else:
        accion = "ANONYMOUS_PRODUCT_VIEW"
        descripcion = f"Usuario anónimo - {accion_tipo} producto ID: {producto_id}"
    
    return AuditoriaLogger.registrar_evento(
        accion=accion,
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )


def log_error_event(error_type, error_message, request=None, usuario=None):
    """
    Registra errores del sistema en la bitácora.
    
    Args:
        error_type (str): '404', '500', 'validation', etc.
        error_message (str): Mensaje del error
        request (HttpRequest, optional): Request para obtener IP y ruta
        usuario (Usuario, optional): Usuario si está disponible
    """
    ip = None
    ruta = ""
    
    if request:
        ip = _get_client_ip(request)
        ruta = request.path
    
    if error_type == '404':
        accion = "ERROR_404"
    elif error_type == '500':
        accion = "ERROR_500"
    else:
        accion = "SYSTEM_ERROR"
    
    descripcion = f"Error en {ruta or 'sistema'}: {error_message}"
    
    return AuditoriaLogger.registrar_evento(
        accion=accion,
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )


def log_dashboard_activity(seccion, ip=None, usuario=None):
    """
    Registra actividad específica del dashboard.
    
    Args:
        seccion (str): Sección del dashboard visitada
        ip (str): IP del usuario
        usuario (Usuario, optional): Usuario si está logueado
    """
    if usuario:
        accion = "DASHBOARD_ACCESS"
        descripcion = f"Usuario {usuario.nombre_usuario} accedió a dashboard: {seccion}"
    else:
        accion = "ANONYMOUS_VIEW"
        descripcion = f"Usuario anónimo accedió a dashboard: {seccion}"
    
    return AuditoriaLogger.registrar_evento(
        accion=accion,
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )


def _get_client_ip(request):
    """Obtiene la IP real del cliente considerando proxys."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip
