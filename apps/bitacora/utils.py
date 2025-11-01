"""
Utilidades para la bitácora.
Funciones de sanitización, validación y helpers para receivers.
"""
import re
import html
import logging

from apps.bitacora.services.logger import AuditoriaLogger
from apps.autenticacion.utils import obtener_ip_cliente
from core.constants import SecurityConstants

logger = logging.getLogger(__name__)


# =====================================================
# FUNCIONES DE SANITIZACIÓN 
# =====================================================

def sanitizar_user_agent(user_agent, max_length=200):
    """
    Sanitiza el User-Agent para prevenir inyección de código.
    
    Proceso:
    1. Limita la longitud
    2. Escapa caracteres HTML
    3. Remueve caracteres de control y no imprimibles
    4. Remueve saltos de línea y caracteres peligrosos
    
    Args:
        user_agent (str): User-Agent original del request
        max_length (int): Longitud máxima permitida (default: 200)
    
    Returns:
        str: User-Agent sanitizado y seguro para almacenar
    """
    if not user_agent:
        return ""
    
    # 1. Limitar longitud
    user_agent = str(user_agent)[:max_length]
    
    # 2. Escapar caracteres HTML (previene XSS)
    user_agent = html.escape(user_agent)
    
    # 3. Remover caracteres de control (ASCII 0-31 excepto espacio)
    user_agent = re.sub(r'[\x00-\x1F\x7F-\x9F]', '', user_agent)
    
    # 4. Remover saltos de línea y retornos de carro
    user_agent = user_agent.replace('\n', '').replace('\r', '')
    
    # 5. Normalizar espacios múltiples
    user_agent = re.sub(r'\s+', ' ', user_agent).strip()
    
    return user_agent


def sanitizar_texto_generico(texto, max_length=500):
    """
    Sanitiza texto genérico para descripciones de bitácora.
    
    Similar a sanitizar_user_agent pero más permisivo con caracteres especiales
    que pueden ser legítimos en descripciones.
    """
    if not texto:
        return ""
    
    # 1. Limitar longitud
    texto = str(texto)[:max_length]
    
    # 2. Escapar HTML
    texto = html.escape(texto)
    
    # 3. Remover solo caracteres de control peligrosos (mantener saltos de línea)
    texto = re.sub(r'[\x00-\x08\x0B-\x0C\x0E-\x1F\x7F-\x9F]', '', texto)
    
    # 4. Normalizar saltos de línea múltiples
    texto = re.sub(r'\n{3,}', '\n\n', texto)
    
    return texto


def es_user_agent_sospechoso(user_agent):
    """
    Detecta User-Agents potencialmente maliciosos o sospechosos.
    
    Args:
        user_agent (str): User-Agent a analizar
    
    Returns:
        tuple: (bool, str) - (es_sospechoso, razon)
    """
    if not user_agent:
        return False, ""
    
    user_agent_lower = user_agent.lower()
    
    # Usar patrones desde SecurityConstants
    for patron, razon in SecurityConstants.PATRONES_USER_AGENT_SOSPECHOSOS:
        if re.search(patron, user_agent_lower):
            logger.warning(
                f"User-Agent sospechoso detectado: {razon} | "
                f"User-Agent: {user_agent[:100]}"
            )
            return True, razon
    
    return False, ""


# =====================================================
# HELPERS PARA RECEIVERS
# =====================================================

def obtener_atributo_seguro(obj, atributo, default="N/A"):
    """
    Obtiene un atributo de un objeto de forma segura, manejando None.
    
    Args:
        obj: Objeto del cual obtener el atributo
        atributo (str): Nombre del atributo (puede usar dot notation: 'categoria.nombre')
        default: Valor por defecto si obj es None o no tiene el atributo
    
    Returns:
        Valor del atributo o el default
        
    Examples:
        >>> producto = Producto(nombre="Test", id_categoria=None)
        >>> obtener_atributo_seguro(producto, "nombre")
        "Test"
        >>> obtener_atributo_seguro(producto, "id_categoria.nombre", "Sin categoría")
        "Sin categoría"
        >>> obtener_atributo_seguro(None, "nombre", "Sin objeto")
        "Sin objeto"
    """
    if obj is None:
        return default
    
    try:
        # Soportar dot notation (ej: "id_categoria.nombre")
        for attr in atributo.split('.'):
            obj = getattr(obj, attr, None)
            if obj is None:
                return default
        return obj
    except (AttributeError, TypeError):
        return default


def formatear_cambios(cambios_dict):
    """
    Formatea un diccionario de cambios para descripción de bitácora.
    
    Args:
        cambios_dict (dict): Dict con estructura {campo: {'anterior': x, 'nuevo': y}}
                             O lista de dicts con estructura [{'campo': ..., 'antes': ..., 'despues': ...}]
    
    Returns:
        str: String formateado "campo1: x → y, campo2: a → b"
    """
    if not cambios_dict:
        return "Sin cambios detectados"
    
    cambios_formateados = []
    
    # Soportar dos formatos:
    # 1. Dict: {campo: {'anterior': x, 'nuevo': y}}
    # 2. Lista: [{'campo': 'x', 'antes': 'y', 'despues': 'z'}]
    
    if isinstance(cambios_dict, dict):
        for campo, datos in cambios_dict.items():
            anterior = datos.get('anterior', datos.get('antes', 'N/A'))
            nuevo = datos.get('nuevo', datos.get('despues', 'N/A'))
            cambios_formateados.append(f"{campo}: {anterior} → {nuevo}")
    
    elif isinstance(cambios_dict, list):
        for cambio in cambios_dict:
            campo = cambio.get('campo', 'desconocido')
            anterior = cambio.get('antes', cambio.get('anterior', 'N/A'))
            nuevo = cambio.get('despues', cambio.get('nuevo', 'N/A'))
            cambios_formateados.append(f"{campo}: {anterior} → {nuevo}")
    
    return ", ".join(cambios_formateados) if cambios_formateados else "Sin cambios detectados"


# =====================================================
# VALIDACIONES DE IP Y REQUEST
# =====================================================

def validar_ip_formato(ip_string):
    """
    Valida que una cadena tenga formato de IP válido sin importarla.
    
    Más rápido que usar ipaddress cuando solo necesitas validar el formato.
    """
    if not ip_string:
        return False
    
    # Patrón para IPv4
    ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'
    
    # Patrón simplificado para IPv6
    ipv6_pattern = r'^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$'
    
    return bool(
        re.match(ipv4_pattern, ip_string) or 
        re.match(ipv6_pattern, ip_string)
    )


def extraer_info_segura_request(request):
    """
    Extrae información segura y sanitizada de un request para logging.
    """
    return {
        'method': request.method,
        'path': request.path[:200],
        'user_agent': sanitizar_user_agent(
            request.META.get('HTTP_USER_AGENT', ''),
            max_length=200
        ),
        'referer': sanitizar_texto_generico(
            request.META.get('HTTP_REFERER', ''),
            max_length=300
        ),
        'content_type': request.META.get('CONTENT_TYPE', ''),
    }


def truncar_descripcion(descripcion, max_length=1000):
    """
    Trunca descripción de manera inteligente para bitácora.
    """
    if not descripcion:
        return ""
    
    descripcion = str(descripcion)
    
    if len(descripcion) <= max_length:
        return descripcion
    
    return descripcion[:max_length - 3] + "..."


# =====================================================
# FUNCIONES DE CONVENIENCIA PARA LOGGING
# =====================================================

# NOTA: Para obtener IP del cliente, usar directamente:
# from apps.autenticacion.utils import obtener_ip_cliente
# ip = obtener_ip_cliente(request)


def log_search_activity(query, ip=None, usuario=None):
    """Registra búsquedas realizadas por usuarios."""
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
    """Registra interacciones específicas con productos."""
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
    """Registra errores del sistema en la bitácora."""
    ip = None
    ruta = ""
    
    if request:
        ip = obtener_ip_cliente(request)
        ruta = request.path
    
    if error_type == '404':
        accion = "ERROR_404"
    elif error_type == '500':
        accion = "ERROR_500"
    else:
        accion = "SUSPICIOUS_ACTIVITY"
    
    descripcion = f"Error en {ruta or 'sistema'}: {error_message}"
    
    return AuditoriaLogger.registrar_evento(
        accion=accion,
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )


def log_dashboard_activity(seccion, ip=None, usuario=None):
    """Registra actividad específica del dashboard."""
    if usuario:
        accion = "VIEW_ACCESS"
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


def ofuscar_credencial(credencial, modo='parcial'):
    """
    Ofusca una credencial (username/email) para prevenir enumeración de usuarios.
    
    Args:
        credencial (str): Username o email a ofuscar
        modo (str): 'parcial', 'total', o 'hash'
            - 'parcial': Muestra primeros caracteres (ej: "adm***")
            - 'total': Oculta todo (ej: "***")
            - 'hash': Genera hash para tracking sin exponer datos
    
    Returns:
        str: Credencial ofuscada
        
    Examples:
        >>> ofuscar_credencial("admin@example.com", modo='parcial')
        "adm***@***"
        >>> ofuscar_credencial("usuario123", modo='total')
        "***"
        >>> ofuscar_credencial("test@mail.com", modo='hash')
        "hash_a3c5f8..."
    """
    if not credencial:
        return "***"
    
    credencial = str(credencial)
    
    if modo == 'total':
        return "***"
    
    elif modo == 'hash':
        # Generar hash SHA256 truncado para tracking sin exponer datos
        import hashlib
        hash_obj = hashlib.sha256(credencial.encode('utf-8'))
        return f"hash_{hash_obj.hexdigest()[:8]}"
    
    else:  # modo == 'parcial'
        # Si es email, ofuscar parte local y dominio
        if '@' in credencial:
            partes = credencial.split('@')
            local = partes[0]
            dominio = partes[1] if len(partes) > 1 else ''
            
            # Mostrar solo primeros 3 caracteres de local
            local_ofuscado = local[:3] + '***' if len(local) > 3 else '***'
            
            # Ofuscar dominio pero mantener extensión
            if '.' in dominio:
                dominio_partes = dominio.split('.')
                dominio_ofuscado = '***.' + dominio_partes[-1]
            else:
                dominio_ofuscado = '***'
            
            return f"{local_ofuscado}@{dominio_ofuscado}"
        
        else:
            # Si es username, mostrar solo primeros 3 caracteres
            return credencial[:3] + '***' if len(credencial) > 3 else '***'


def detectar_intento_fuerza_bruta(
    ip, 
    ventana_minutos=None, 
    max_intentos=None
):
    """
    Detecta si una IP está realizando intentos de fuerza bruta.
    
    Args:
        ip (str): Dirección IP a verificar
        ventana_minutos (int, optional): Ventana de tiempo en minutos
        max_intentos (int, optional): Máximo de intentos permitidos
    
    Returns:
        tuple: (es_fuerza_bruta: bool, cantidad_intentos: int)
        
    Note:
        Si no se proporcionan ventana_minutos o max_intentos, se usan
        los valores de SecurityConstants.
    """
    from django.utils import timezone
    from datetime import timedelta
    from apps.bitacora.models import Bitacora
    
    if not ip:
        return False, 0
    
    # Usar valores de SecurityConstants si no se proporcionan
    if ventana_minutos is None:
        ventana_minutos = SecurityConstants.DETECCION_FUERZA_BRUTA_VENTANA
    if max_intentos is None:
        max_intentos = SecurityConstants.DETECCION_FUERZA_BRUTA_MAX
    
    fecha_limite = timezone.now() - timedelta(minutes=ventana_minutos)
    
    # Contar intentos fallidos desde esta IP en la ventana de tiempo
    intentos_fallidos = Bitacora.objects.filter(
        ip=ip,
        accion='FAILED_LOGIN',
        fecha_hora__gte=fecha_limite
    ).count()
    
    es_fuerza_bruta = intentos_fallidos >= max_intentos
    
    if es_fuerza_bruta:
        logger.warning(
            f"Posible ataque de fuerza bruta detectado desde IP {ip}: "
            f"{intentos_fallidos} intentos en {ventana_minutos} minutos"
        )
    
    return es_fuerza_bruta, intentos_fallidos


def generar_fingerprint_intento_login(credencial, user_agent, ip):
    """
    Genera un fingerprint único para rastrear patrones de ataque sin exponer datos.
    
    Args:
        credencial (str): Username/email del intento
        user_agent (str): User-Agent del request
        ip (str): IP del intento
    
    Returns:
        str: Fingerprint único (hash)
    """
    import hashlib
    
    datos = f"{credencial}|{user_agent}|{ip}"
    hash_obj = hashlib.sha256(datos.encode('utf-8'))
    
    return hash_obj.hexdigest()[:16]