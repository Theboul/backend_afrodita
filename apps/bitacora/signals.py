import logging
from django.dispatch import receiver, Signal
from apps.bitacora.services.logger import AuditoriaLogger
from apps.bitacora.utils import (
    sanitizar_user_agent, 
    es_user_agent_sospechoso,
    obtener_atributo_seguro,
    formatear_cambios,
    ofuscar_credencial,
    detectar_intento_fuerza_bruta
)

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

# --- GESTIÓN DE CATEGORÍAS ---
categoria_creada = Signal()        # args: categoria, usuario, ip
categoria_actualizada = Signal()   # args: categoria, usuario, ip, cambios
categoria_movida = Signal()        # args: categoria, usuario, ip, origen, destino, motivo
categoria_eliminada = Signal()     # args: categoria, usuario, ip, motivo
categoria_restaurada = Signal()    # args: categoria, usuario, ip

# --- SEÑALES: GESTIÓN DE PRODUCTOS ---
producto_creado = Signal()           # args: producto, usuario, ip
producto_actualizado = Signal()      # args: producto, usuario, ip, cambios
producto_eliminado = Signal()        # args: producto, usuario, ip, motivo
producto_estado_cambiado = Signal()  # args: producto, usuario, ip, estado_anterior, estado_nuevo, motivo
producto_stock_ajustado = Signal()   # args: producto, usuario, ip, tipo_ajuste, cantidad, stock_anterior, stock_nuevo, motivo

# --- Señales específicas del módulo de imágenes ---
imagen_subida = Signal()              # args: imagen, usuario, ip
imagen_eliminada = Signal()           # args: imagen, usuario, ip
imagen_actualizada = Signal()         # args: imagen, usuario, ip, cambios
imagen_principal_cambiada = Signal()  # args: imagen, usuario, ip
imagen_restaurada = Signal()          # args: imagen, usuario, ip
imagen_reordenada = Signal()          # args: imagen, usuario, ip, orden_anterior, orden_nuevo


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
    """
    Registra intentos fallidos de login de forma segura.
    Funcionalidades:
    - Ofusca la credencial para prevenir enumeración de usuarios
    - Detecta intentos de fuerza bruta
    - Usa fingerprinting para rastrear patrones de ataque
    """
    # Detectar si es un intento de fuerza bruta
    es_fuerza_bruta, cantidad_intentos = detectar_intento_fuerza_bruta(ip)
    
    # Ofuscar credencial para prevenir enumeración
    credencial_ofuscada = ofuscar_credencial(credencial, modo='parcial')
    
    # Construir descripción base
    descripcion = f"Intento fallido de inicio de sesión desde IP {ip}"
    
    # Agregar información ofuscada
    if credencial_ofuscada:
        descripcion += f" | Credencial: {credencial_ofuscada}"
    
    # Si es fuerza bruta, agregar warning
    if es_fuerza_bruta:
        descripcion += f" | ALERTA: Posible ataque de fuerza bruta ({cantidad_intentos} intentos)"
        
        # Registrar evento adicional de actividad sospechosa
        AuditoriaLogger.registrar_evento(
            accion="SUSPICIOUS_ACTIVITY",
            descripcion=f"Ataque de fuerza bruta detectado desde IP {ip} con {cantidad_intentos} intentos fallidos",
            ip=ip,
            usuario=None
        )
    
    # Registrar el evento principal
    AuditoriaLogger.registrar_evento(
        accion="FAILED_LOGIN",
        descripcion=descripcion,
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
# ====================================================
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
    
    ACTUALIZADO: Ahora sanitiza el User-Agent antes de guardarlo.
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

    # SANITIZAR USER-AGENT ANTES DE AGREGAR A LA DESCRIPCIÓN
    # para evitar posibles ataques de inyección de código
    if user_agent:
        # Sanitizar el user agent
        user_agent_sanitizado = sanitizar_user_agent(user_agent, max_length=150)
        
        # Verificar si es sospechoso (opcional, para logging)
        es_sospechoso, razon = es_user_agent_sospechoso(user_agent)
        if es_sospechoso:
            # Loguear advertencia pero igual registrar el evento
            logger.warning(
                f"User-Agent sospechoso detectado: {razon} | "
                f"IP: {ip} | Ruta: {ruta}"
            )
            # Opcionalmente, agregar el flag a la descripción
            descripcion += f" | [UA Sospechoso: {razon}]"
        
        # Agregar user agent sanitizado a la descripción
        descripcion += f" | User-Agent: {user_agent_sanitizado}"

    # Registrar el evento con AuditoriaLogger
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
    """Registra la creación de una categoría"""
    descripcion = f"Categoría '{categoria.nombre}' creada por {usuario.nombre_usuario}"
    
    # Validación segura del padre
    if categoria.id_catpadre:
        nombre_padre = obtener_atributo_seguro(
            categoria.id_catpadre, 
            'nombre', 
            'Categoría padre sin nombre'
        )
        descripcion += f" (Padre: {nombre_padre})"
    
    AuditoriaLogger.registrar_evento(
        accion="CATEGORY_CREATE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )

@receiver(categoria_actualizada)
def registrar_categoria_actualizada(sender, categoria, usuario, ip, cambios, **kwargs):
    """Registra la actualización de una categoría"""
    # Usar helper para formatear cambios
    campos = formatear_cambios(cambios)
    
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


# =====================================================
# RECEIVERS: GESTIÓN DE PRODUCTOS
# =====================================================
@receiver(producto_creado)
def registrar_producto_creado(sender, producto, usuario, ip, **kwargs):
    """Registra la creación de un producto"""
    descripcion = f"Producto '{producto.nombre}' (ID: {producto.id_producto}) creado por {usuario.nombre_usuario}"
    descripcion += f" | Precio: {producto.precio} | Stock: {producto.stock}"
    if producto.id_categoria:
        descripcion += f" | Categoría: {producto.id_categoria.nombre}"
    
    AuditoriaLogger.registrar_evento(
        accion="PRODUCT_CREATE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )

@receiver(producto_actualizado)
def registrar_producto_actualizado(sender, producto, usuario, ip, cambios, **kwargs):
    """Registra la actualización de un producto"""
    if cambios:
        campos = ", ".join([
            f"{campo}: {datos['anterior']} → {datos['nuevo']}" 
            for campo, datos in cambios.items()
        ])
        descripcion = f"Producto '{producto.nombre}' (ID: {producto.id_producto}) actualizado por {usuario.nombre_usuario} | Cambios: {campos}"
    else:
        descripcion = f"Producto '{producto.nombre}' actualizado sin cambios detectados"
    
    AuditoriaLogger.registrar_evento(
        accion="PRODUCT_UPDATE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )

@receiver(producto_eliminado)
def registrar_producto_eliminado(sender, producto, usuario, ip, motivo=None, **kwargs):
    """Registra la eliminación de un producto"""
    descripcion = f"Producto '{producto.nombre}' (ID: {producto.id_producto}) eliminado por {usuario.nombre_usuario}"
    if motivo:
        descripcion += f" | Motivo: {motivo}"
    
    AuditoriaLogger.registrar_evento(
        accion="PRODUCT_DELETE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )

@receiver(producto_estado_cambiado)
def registrar_producto_estado_cambiado(sender, producto, usuario, ip, estado_anterior, estado_nuevo, motivo=None, **kwargs):
    """Registra el cambio de estado de un producto"""
    descripcion = f"Estado de producto '{producto.nombre}' (ID: {producto.id_producto}) cambiado: {estado_anterior} → {estado_nuevo} por {usuario.nombre_usuario}"
    if motivo:
        descripcion += f" | Motivo: {motivo}"
    
    AuditoriaLogger.registrar_evento(
        accion="PRODUCT_STATE_CHANGE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )

@receiver(producto_stock_ajustado)
def registrar_producto_stock_ajustado(sender, producto, usuario, ip, tipo_ajuste, cantidad, stock_anterior, stock_nuevo, motivo, **kwargs):
    """Registra el ajuste de stock de un producto"""
    descripcion = f"Ajuste de stock {tipo_ajuste} en producto '{producto.nombre}' (ID: {producto.id_producto})"
    descripcion += f" | Stock anterior: {stock_anterior} → Stock nuevo: {stock_nuevo} | Cantidad ajustada: {cantidad}"
    descripcion += f" | Motivo: {motivo} | Ejecutado por: {usuario.nombre_usuario}"
    
    AuditoriaLogger.registrar_evento(
        accion="PRODUCT_STOCK_ADJUST",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )


# =====================================================
# RECEIVERS: GESTIÓN DE IMÁGENES DEL CATÁLOGO
# =====================================================
@receiver(imagen_subida)
def registrar_imagen_subida(sender, imagen, usuario, ip, **kwargs):
    """Registra la subida de una imagen al catálogo"""
    # Validación segura del producto
    nombre_producto = obtener_atributo_seguro(
        imagen.id_producto,
        'nombre',
        'Producto desconocido'
    )
    id_producto = obtener_atributo_seguro(
        imagen.id_producto,
        'id_producto',
        'N/A'
    )
    
    descripcion = (
        f"Imagen subida para el producto '{nombre_producto}' "
        f"(ID producto: {id_producto}) | "
        f"URL: {imagen.url} | Principal: {imagen.es_principal}"
    )
    AuditoriaLogger.registrar_evento(
        accion="IMAGE_UPLOAD",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )

@receiver(imagen_eliminada)
def registrar_imagen_eliminada(sender, imagen, usuario, ip, **kwargs):
    """Registra la eliminación (lógica o física) de una imagen"""
    # Validación segura del producto
    nombre_producto = obtener_atributo_seguro(
        imagen.id_producto,
        'nombre',
        'Producto desconocido'
    )
    id_producto = obtener_atributo_seguro(
        imagen.id_producto,
        'id_producto',
        'N/A'
    )
    
    descripcion = (
        f"Imagen eliminada del producto '{nombre_producto}' "
        f"(ID producto: {id_producto}) | "
        f"URL: {imagen.url}"
    )
    AuditoriaLogger.registrar_evento(
        accion="IMAGE_DELETE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )

@receiver(imagen_principal_cambiada)
def registrar_imagen_principal_cambiada(sender, imagen, usuario, ip, **kwargs):
    """Registra el cambio de imagen principal"""
    # Validación segura del producto
    nombre_producto = obtener_atributo_seguro(
        imagen.id_producto,
        'nombre',
        'Producto desconocido'
    )
    id_producto = obtener_atributo_seguro(
        imagen.id_producto,
        'id_producto',
        'N/A'
    )
    
    descripcion = (
        f"Imagen marcada como principal para el producto '{nombre_producto}' "
        f"(ID producto: {id_producto}) | "
        f"Public ID: {imagen.public_id}"
    )
    AuditoriaLogger.registrar_evento(
        accion="IMAGE_SET_MAIN",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )

@receiver(imagen_restaurada)
def registrar_imagen_restaurada(sender, imagen, usuario, ip, **kwargs):
    """Registra la restauración de una imagen previamente inactiva"""
    # Validación segura del producto
    nombre_producto = obtener_atributo_seguro(
        imagen.id_producto,
        'nombre',
        'Producto desconocido'
    )
    
    descripcion = (
        f"Imagen restaurada para el producto '{nombre_producto}' "
        f"(ID Imagen: {imagen.id_imagen}, Public ID: {imagen.public_id}) "
        f"por el usuario {usuario.nombre_usuario}."
    )
    AuditoriaLogger.registrar_evento(
        accion="IMAGE_RESTORE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )

@receiver(imagen_reordenada)
def registrar_imagen_reordenada(sender, producto, usuario, ip, cantidad, **kwargs):
    """Registra el reordenamiento de imágenes de un producto"""
    # Este receiver recibe el producto directamente, no necesita validación adicional
    descripcion = (
        f"Se reordenaron {cantidad} imágenes del producto '{producto.nombre}' "
        f"por el usuario {usuario.nombre_usuario}."
    )
    AuditoriaLogger.registrar_evento(
        accion="IMAGE_REORDER",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )

@receiver(imagen_actualizada)
def registrar_imagen_actualizada(sender, imagen, usuario, ip, cambios, **kwargs):
    """Registra la actualización de metadatos de una imagen"""
    # Usar helper para formatear cambios
    campos = formatear_cambios(cambios)
    
    # Validación segura del producto
    nombre_producto = obtener_atributo_seguro(
        imagen.id_producto,
        'nombre',
        'Producto desconocido'
    )
    id_producto = obtener_atributo_seguro(
        imagen.id_producto,
        'id_producto',
        'N/A'
    )

    descripcion = (
        f"Metadatos de la imagen del producto '{nombre_producto}' "
        f"(ID producto: {id_producto}) actualizados por {usuario.nombre_usuario} | "
        f"Cambios: {campos}"
    )

    AuditoriaLogger.registrar_evento(
        accion="IMAGE_UPDATE",
        descripcion=descripcion,
        ip=ip,
        usuario=usuario
    )
