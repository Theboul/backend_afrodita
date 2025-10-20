import logging
from django.dispatch import receiver, Signal
from apps.bitacora.services.logger import AuditoriaLogger

logger = logging.getLogger(__name__)

# =====================================================
# DEFINICIÓN DE SEÑALES DEL SISTEMA
# =====================================================

# --- AUTENTICACIÓN Y SESIONES ---
login_exitoso = Signal()           # args: usuario, ip
login_fallido = Signal()           # args: ip, credencial
logout_realizado = Signal()        # args: usuario, ip
logout_error = Signal()            # args: usuario, ip, error
token_invalidado = Signal()        # args: token, usuario(optional)

# --- MONITOREO DE VISTAS / VISITAS ---
vista_visitada = Signal()          # args: usuario, ip, ruta
vista_anonima_visitada = Signal()  # args: ip, ruta, user_agent

# --- GESTIÓN ADMINISTRATIVA (USUARIOS) ---
usuario_creado = Signal()             # args: usuario_creado, usuario_ejecutor, ip, datos_adicionales
usuario_actualizado = Signal()        # args: usuario_afectado, usuario_ejecutor, ip, datos_anteriores, datos_nuevos
usuario_eliminado = Signal()          # args: usuario_afectado, usuario_ejecutor, ip, motivo, tokens_invalidados
usuario_estado_cambiado = Signal()    # args: usuario_afectado, usuario_ejecutor, ip, estado_anterior, estado_nuevo, motivo
usuario_password_cambiado = Signal()  # args: usuario_afectado, usuario_ejecutor, ip
logout_forzado = Signal()             # args: usuario_afectado, usuario_ejecutor, ip, motivo, tokens_invalidados

# --- GESTIÓN DE CATEGORÍAS (CU10) ---
categoria_creada = Signal()        # args: categoria, usuario, ip
categoria_actualizada = Signal()   # args: categoria, usuario, ip, cambios
categoria_movida = Signal()        # args: categoria, usuario, ip, origen, destino, motivo
categoria_eliminada = Signal()     # args: categoria, usuario, ip, motivo
categoria_restaurada = Signal()    # args: categoria, usuario, ip


# =====================================================
# RECEIVERS: AUTENTICACIÓN Y SESIONES
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


@receiver(token_invalidado)
def registrar_token_invalidado(sender, token, usuario=None, **kwargs):
    AuditoriaLogger.registrar_evento(
        accion="TOKEN_INVALIDATION",
        descripcion=f"Refresh token invalidado: {token[:12]}...",
        ip=None,
        usuario=usuario
    )


# =====================================================
# RECEIVERS: MONITOREO DE VISITAS
# =====================================================

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
    if '/productos' in ruta:
        accion = "ANONYMOUS_PRODUCT_VIEW"
        descripcion = f"Usuario anónimo vio productos en: {ruta}"
    elif '/categoria' in ruta:
        accion = "ANONYMOUS_VIEW"
        descripcion = f"Usuario anónimo vio categorías en: {ruta}"
    else:
        accion = "ANONYMOUS_VIEW"
        descripcion = f"Usuario anónimo accedió a: {ruta}"

    if user_agent:
        descripcion += f" | User-Agent: {user_agent[:100]}..."

    AuditoriaLogger.registrar_evento_anonimo(
        accion=accion,
        descripcion=descripcion,
        ip=ip
    )


# =====================================================
# RECEIVERS: GESTIÓN DE USUARIOS / ADMINISTRACIÓN
# =====================================================

@receiver(usuario_creado)
def registrar_usuario_creado(sender, usuario_creado, usuario_ejecutor, ip, datos_adicionales=None, **kwargs):
    descripcion = f"Creación de usuario {usuario_creado.nombre_usuario} por {usuario_ejecutor.nombre_usuario}"
    if datos_adicionales:
        descripcion += f" | Rol: {datos_adicionales.get('rol', 'Sin rol')}"
    AuditoriaLogger.registrar_evento(
        accion="REGISTER",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario_ejecutor
    )


@receiver(usuario_actualizado)
def registrar_usuario_actualizado(sender, usuario_afectado, usuario_ejecutor, ip, datos_anteriores, datos_nuevos, **kwargs):
    cambios = []
    for campo, valor_anterior in datos_anteriores.items():
        valor_nuevo = datos_nuevos.get(campo)
        if valor_anterior != valor_nuevo:
            cambios.append(f"{campo}: {valor_anterior} → {valor_nuevo}")

    descripcion = f"Actualización de usuario {usuario_afectado.nombre_usuario} por {usuario_ejecutor.nombre_usuario}"
    if cambios:
        descripcion += f" | Cambios: {', '.join(cambios)}"

    AuditoriaLogger.registrar_evento(
        accion="PROFILE_UPDATE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario_ejecutor
    )


@receiver(usuario_eliminado)
def registrar_usuario_eliminado(sender, usuario_afectado, usuario_ejecutor, ip, motivo, tokens_invalidados, **kwargs):
    descripcion = f"Eliminación lógica de usuario {usuario_afectado.nombre_usuario} por {usuario_ejecutor.nombre_usuario}"
    descripcion += f" | Tokens invalidados: {tokens_invalidados}"
    if motivo:
        descripcion += f" | Motivo: {motivo}"
    AuditoriaLogger.registrar_evento(
        accion="DELETE_ACCOUNT",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario_ejecutor
    )


@receiver(usuario_estado_cambiado)
def registrar_usuario_estado_cambiado(sender, usuario_afectado, usuario_ejecutor, ip, estado_anterior, estado_nuevo, motivo, **kwargs):
    accion = "PERMISSION_CHANGE" if estado_nuevo == "ACTIVO" else "TOKEN_INVALIDATION"
    descripcion = f"Cambio de estado de {usuario_afectado.nombre_usuario}: {estado_anterior} → {estado_nuevo} por {usuario_ejecutor.nombre_usuario}"
    if motivo:
        descripcion += f" | Motivo: {motivo}"
    AuditoriaLogger.registrar_evento(
        accion=accion,
        descripcion=descripcion,
        ip=ip,
        usuario=usuario_ejecutor
    )


@receiver(usuario_password_cambiado)
def registrar_usuario_password_cambiado(sender, usuario_afectado, usuario_ejecutor, ip, **kwargs):
    AuditoriaLogger.registrar_evento(
        accion="PASSWORD_CHANGE",
        descripcion=f"Contraseña cambiada forzadamente a {usuario_afectado.nombre_usuario} por {usuario_ejecutor.nombre_usuario}",
        ip=ip,
        usuario=usuario_ejecutor
    )


@receiver(logout_forzado)
def registrar_logout_forzado(sender, usuario_afectado, usuario_ejecutor, ip, motivo, tokens_invalidados, **kwargs):
    descripcion = f"Logout forzado a {usuario_afectado.nombre_usuario} por {usuario_ejecutor.nombre_usuario}"
    descripcion += f" | Tokens invalidados: {tokens_invalidados}"
    if motivo:
        descripcion += f" | Motivo: {motivo}"
    AuditoriaLogger.registrar_evento(
        accion="TOKEN_INVALIDATION",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario_ejecutor
    )


# =====================================================
# RECEIVERS: GESTIÓN DE CATEGORÍAS
# =====================================================

@receiver(categoria_creada)
def registrar_categoria_creada(sender, categoria, usuario, ip, **kwargs):
    descripcion = f"Categoría '{categoria.nombre}' creada por {usuario.nombre_usuario}"
    if categoria.id_catpadre:
        descripcion += f" (Padre: {categoria.id_catpadre.nombre})"
    AuditoriaLogger.registrar_evento(
        accion="CATEGORY_CREATE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )


@receiver(categoria_actualizada)
def registrar_categoria_actualizada(sender, categoria, usuario, ip, cambios, **kwargs):
    campos = ", ".join([f"{c['campo']}: {c['antes']} → {c['despues']}" for c in cambios]) or "Sin cambios detectados"
    descripcion = f"Categoría '{categoria.nombre}' actualizada por {usuario.nombre_usuario} | Cambios: {campos}"
    AuditoriaLogger.registrar_evento(
        accion="CATEGORY_UPDATE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )


@receiver(categoria_movida)
def registrar_categoria_movida(sender, categoria, usuario, ip, origen, destino, motivo=None, **kwargs):
    descripcion = f"Categoría '{categoria.nombre}' movida de '{origen}' a '{destino}' por {usuario.nombre_usuario}"
    if motivo:
        descripcion += f" | Motivo: {motivo}"
    AuditoriaLogger.registrar_evento(
        accion="CATEGORY_MOVE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )


@receiver(categoria_eliminada)
def registrar_categoria_eliminada(sender, categoria, usuario, ip, motivo=None, **kwargs):
    descripcion = f"Categoría '{categoria.nombre}' marcada como INACTIVA por {usuario.nombre_usuario}"
    if motivo:
        descripcion += f" | Motivo: {motivo}"
    AuditoriaLogger.registrar_evento(
        accion="CATEGORY_DELETE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )


@receiver(categoria_restaurada)
def registrar_categoria_restaurada(sender, categoria, usuario, ip, **kwargs):
    AuditoriaLogger.registrar_evento(
        accion="CATEGORY_RESTORE",
        descripcion=f"Categoría '{categoria.nombre}' restaurada por {usuario.nombre_usuario}",
        ip=ip,
        usuario=usuario
    )
