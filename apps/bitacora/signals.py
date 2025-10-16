import logging
from django.dispatch import receiver, Signal
from apps.bitacora.services.logger import AuditoriaLogger

logger = logging.getLogger(__name__)

# =====================================================
# Definición de señales del sistema
# =====================================================
login_exitoso = Signal()        # args: usuario, ip
login_fallido = Signal()        # args: ip, credencial
logout_realizado = Signal()     # args: usuario, ip
logout_error = Signal()         # args: usuario, ip, error
vista_visitada = Signal()       # args: usuario, ip, ruta
vista_anonima_visitada = Signal()  # args: ip, ruta, user_agent
token_invalidado = Signal()     # args: token, usuario(optional)


# =====================================================
# Manejadores (receivers)
# =====================================================

@receiver(login_exitoso)
def registrar_login_exitoso(sender, usuario, ip, **kwargs):
    AuditoriaLogger.registrar_evento(
        accion="LOGIN",
        descripcion=f"Inicio de sesión exitoso del usuario {usuario.nombre_usuario}",
        ip=ip,
        usuario=usuario
    )


@receiver(login_fallido)
def registrar_login_fallido(sender, ip, credencial=None, **kwargs):
    AuditoriaLogger.registrar_evento(
        accion="FAILED_LOGIN",
        descripcion=f"Intento fallido de inicio de sesión. Credencial usada: {credencial or 'desconocida'}",
        ip=ip
    )


@receiver(logout_realizado)
def registrar_logout(sender, usuario, ip, **kwargs):
    AuditoriaLogger.registrar_evento(
        accion="LOGOUT",
        descripcion=f"Sesión cerrada por {usuario.nombre_usuario}",
        ip=ip,
        usuario=usuario
    )


@receiver(logout_error)
def registrar_logout_error(sender, usuario, ip, error, **kwargs):
    AuditoriaLogger.registrar_evento(
        accion="LOGOUT_ERROR",
        descripcion=f"Error al cerrar sesión ({usuario.nombre_usuario}): {error}",
        ip=ip,
        usuario=usuario
    )


@receiver(vista_visitada)
def registrar_vista_visitada(sender, usuario, ip, ruta, **kwargs):
    AuditoriaLogger.registrar_evento(
        accion="VIEW_ACCESS",
        descripcion=f"El usuario {usuario.nombre_usuario} accedió a la ruta: {ruta}",
        ip=ip,
        usuario=usuario
    )


@receiver(vista_anonima_visitada)
def registrar_vista_anonima(sender, ip, ruta, user_agent="", **kwargs):
    """
    Registra vistas de usuarios anónimos para analytics del dashboard.
    """
    # Determinar el tipo de acción según la ruta
    if '/productos' in ruta:
        accion = "ANONYMOUS_PRODUCT_VIEW"
        descripcion = f"Usuario anónimo vio productos en: {ruta}"
    elif '/categoria' in ruta:
        accion = "ANONYMOUS_VIEW"
        descripcion = f"Usuario anónimo vio categorías en: {ruta}"
    else:
        accion = "ANONYMOUS_VIEW"
        descripcion = f"Usuario anónimo accedió a: {ruta}"
    
    # Agregar información del user agent si está disponible
    if user_agent:
        descripcion += f" | User-Agent: {user_agent[:100]}..."
    
    AuditoriaLogger.registrar_evento_anonimo(
        accion=accion,
        descripcion=descripcion,
        ip=ip
    )


@receiver(token_invalidado)
def registrar_token_invalidado(sender, token, usuario=None, **kwargs):
    AuditoriaLogger.registrar_evento(
        accion="TOKEN_INVALIDATION",
        descripcion=f"Refresh token invalidado: {token[:12]}...",
        ip=None,
        usuario=usuario
    )
