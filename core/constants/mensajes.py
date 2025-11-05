"""
Mensajes centralizados de la aplicación.
Facilita la internacionalización y consistencia en mensajes.
"""


class Messages:
    """Mensajes estandarizados del sistema."""
    
    # =====================================================
    # MENSAJES GENERALES
    # =====================================================
    OPERATION_SUCCESS = 'Operación realizada exitosamente.'
    OPERATION_FAILED = 'No se pudo completar la operación.'
    INVALID_DATA = 'Los datos enviados son inválidos.'
    UNAUTHORIZED = 'No tiene autorización para realizar esta acción.'
    FORBIDDEN = 'Acceso prohibido.'
    NOT_FOUND = 'El recurso solicitado no existe.'
    SERVER_ERROR = 'Error interno del servidor.'
    
    # =====================================================
    # USUARIOS
    # =====================================================
    USER_CREATED = 'Usuario creado exitosamente.'
    USER_UPDATED = 'Usuario actualizado correctamente.'
    USER_DELETED = 'Usuario eliminado correctamente.'
    USER_NOT_FOUND = 'Usuario no encontrado.'
    USER_INACTIVE = 'El usuario está inactivo.'
    
    # Usuarios - Validaciones
    CANNOT_DELETE_MAIN_ADMIN = 'No se puede eliminar al administrador principal.'
    CANNOT_DELETE_SELF = 'No puede eliminar su propio usuario.'
    USER_HAS_ACTIVE_SALES = 'No se puede eliminar usuario con ventas activas.'
    USER_ALREADY_EXISTS = 'Ya existe un usuario con estos datos.'
    
    # Usuarios - Estado
    USER_STATUS_CHANGED = 'Estado del usuario cambiado correctamente.'
    USER_STATE_CHANGED = 'Estado del usuario cambiado correctamente.'  # Alias para compatibilidad
    CANNOT_LOGOUT_INACTIVE_USER = 'No se puede forzar logout de usuario inactivo.'
    
    # Usuarios - Sesión
    LOGOUT_FORCED = 'Se forzó el cierre de sesión en todos los dispositivos.'
    TOKENS_INVALIDATED = 'Tokens invalidados correctamente.'
    
    # =====================================================
    # AUTENTICACIÓN
    # =====================================================
    # Login
    INVALID_CREDENTIALS = 'Correo electrónico o contraseña incorrectos.'
    ACCOUNT_INACTIVE = 'Tu cuenta está inactiva. Contacta al administrador.'
    LOGIN_SUCCESS = 'Inicio de sesión exitoso.'
    WELCOME_USER = 'Bienvenido/a {nombre}.'
    
    # Logout
    LOGOUT_SUCCESS = 'Has cerrado sesión correctamente.'
    SESSION_CLOSED = 'Sesión cerrada exitosamente.'
    
    # Token Refresh
    TOKEN_REFRESHED = 'Token actualizado correctamente.'
    INVALID_REFRESH_TOKEN = 'El token de actualización es inválido o ha expirado.'
    
    # Seguridad
    ACCOUNT_BLOCKED = 'Cuenta bloqueada por múltiples intentos fallidos.'
    IP_BLOCKED = 'Tu IP ha sido bloqueada temporalmente.'
    SECURITY_ERROR = 'Error de seguridad. Intenta nuevamente.'
    
    # Validaciones
    MISSING_CREDENTIALS = 'Debe proporcionar correo electrónico y contraseña.'
    INVALID_EMAIL_FORMAT = 'El formato del correo electrónico es inválido.'
    
    # =====================================================
    # CLIENTES
    # =====================================================
    NOT_A_CLIENT = 'Este usuario no es un cliente.'
    CLIENT_NOT_FOUND = 'Cliente no encontrado en la base de datos.'
    ONLY_CLIENTS_HAVE_ADDRESSES = 'Solo los clientes tienen direcciones.'
    
    # =====================================================
    # DIRECCIONES
    # =====================================================
    ADDRESS_CREATED = 'Dirección creada correctamente.'
    ADDRESS_UPDATED = 'Dirección actualizada correctamente.'
    ADDRESS_DELETED = 'Dirección eliminada correctamente.'
    ADDRESS_NOT_FOUND = 'Dirección no encontrada.'
    ADDRESS_NOT_BELONGS = 'Dirección no encontrada o no pertenece a este cliente.'
    ADDRESS_MARKED_PRINCIPAL = 'Dirección marcada como principal correctamente.'
    
    # Direcciones - Listado
    ADDRESSES_RETRIEVED = 'Direcciones obtenidas correctamente.'
    NO_ADDRESSES_FOUND = 'No se encontraron direcciones.'
    
    # Direcciones - Errores
    ERROR_FETCHING_ADDRESSES = 'Error al obtener las direcciones.'
    ERROR_CREATING_ADDRESS = 'Error al crear la dirección.'
    ERROR_UPDATING_ADDRESS = 'Error al editar la dirección.'
    ERROR_DELETING_ADDRESS = 'Error al eliminar la dirección.'
    ERROR_MARKING_PRINCIPAL = 'Error al marcar dirección como principal.'
    
    # =====================================================
    # CATEGORÍAS
    # =====================================================
    CATEGORY_CREATED = 'Categoría creada correctamente.'
    CATEGORY_UPDATED = 'Categoría actualizada correctamente.'
    CATEGORY_DELETED = 'Categoría eliminada correctamente.'
    CATEGORY_RESTORED = 'Categoría restaurada exitosamente.'
    CATEGORY_MOVED = 'Categoría movida correctamente.'
    CATEGORY_NOT_FOUND = 'Categoría no encontrada.'
    CATEGORY_ALREADY_ACTIVE = 'La categoría ya está activa.'
    CATEGORY_HAS_SUBCATEGORIES = 'No se puede eliminar una categoría con subcategorías.'
    CATEGORY_HAS_PRODUCTS = 'No se puede eliminar una categoría con productos activos.'
    CATEGORY_CANNOT_MOVE_TO_SELF = 'No se puede mover una categoría a sí misma.'
    CATEGORY_CANNOT_MOVE_TO_CHILD = 'No se puede mover una categoría dentro de sus subcategorías.'
    
    # =====================================================
    # AUTENTICACIÓN
    # =====================================================
    LOGIN_SUCCESS = 'Inicio de sesión exitoso.'
    LOGIN_FAILED = 'Credenciales incorrectas.'
    LOGOUT_SUCCESS = 'Sesión cerrada correctamente.'
    TOKEN_INVALID = 'Token inválido o expirado.'
    TOKEN_REFRESHED = 'Token actualizado correctamente.'
    
    # =====================================================
    # CONTRASEÑAS
    # =====================================================
    PASSWORD_CHANGED = 'Contraseña cambiada exitosamente.'
    PASSWORD_MISMATCH = 'Las contraseñas no coinciden.'
    PASSWORD_WEAK = 'La contraseña no cumple con los requisitos de seguridad.'
    
    # =====================================================
    # PERFIL
    # =====================================================
    PROFILE_RETRIEVED = 'Perfil obtenido correctamente.'
    PROFILE_UPDATED = 'Perfil actualizado correctamente.'
    STATISTICS_RETRIEVED = 'Estadísticas obtenidas correctamente.'
    
    # =====================================================
    # VALIDACIONES
    # =====================================================
    REQUIRED_FIELD = 'Este campo es obligatorio.'
    FIELD_REQUIRED = 'El campo {field} es requerido.'  # Con formato dinámico
    INVALID_FORMAT = 'Formato inválido.'
    EMAIL_ALREADY_EXISTS = 'El correo ya está registrado.'
    USERNAME_ALREADY_EXISTS = 'El nombre de usuario ya está en uso.'
    PHONE_INVALID = 'El teléfono debe contener solo números (8-15 dígitos).'
    
    # =====================================================
    # PRODUCTOS
    # =====================================================
    PRODUCT_CREATED = 'Producto creado exitosamente.'
    PRODUCT_UPDATED = 'Producto actualizado correctamente.'
    PRODUCT_DELETED = 'Producto eliminado exitosamente.'
    PRODUCT_NOT_FOUND = 'Producto no encontrado.'
    PRODUCT_STATE_CHANGED = 'Estado actualizado correctamente.'
    PRODUCT_STOCK_ADJUSTED = 'Stock ajustado exitosamente.'
    PRODUCT_ID_EXISTS = 'Ya existe un producto con este ID.'
    PRODUCT_PRICE_INVALID = 'El precio debe ser mayor a 0.'
    PRODUCT_STOCK_NEGATIVE = 'El stock no puede ser negativo.'
    PRODUCT_CATEGORY_REQUIRED = 'La categoría es requerida.'
    PRODUCT_CONFIG_NOT_EXISTS = 'La configuración seleccionada no existe.'
    PRODUCT_STATE_INVALID = 'Estado inválido. Use ACTIVO o INACTIVO.'
    PRODUCT_STOCK_INSUFFICIENT = 'Stock insuficiente para el ajuste.'
    PRODUCT_ADJUSTMENT_INVALID = 'Tipo de ajuste inválido. Use: {types}.'
    PRODUCT_QUANTITY_NEGATIVE = 'La cantidad no puede ser negativa.'
    NO_REASON_SPECIFIED = 'Sin motivo especificado.'
    
    # =====================================================
    # CATEGORÍAS
    # =====================================================
    CATEGORY_CREATED = 'Categoría creada exitosamente.'
    CATEGORY_UPDATED = 'Categoría actualizada correctamente.'
    CATEGORY_DELETED = 'Categoría eliminada correctamente.'
    CATEGORY_NOT_FOUND = 'Categoría no encontrada.'
    CATEGORY_RESTORED = 'Categoría restaurada correctamente.'
    
    # =====================================================
    # VENTAS
    # =====================================================
    SALE_CREATED = 'Venta registrada exitosamente.'
    SALE_UPDATED = 'Venta actualizada correctamente.'
    SALE_CANCELLED = 'Venta cancelada correctamente.'
    SALE_NOT_FOUND = 'Venta no encontrada.'
    
    # =====================================================
    # CATÁLOGO PÚBLICO
    # =====================================================
    # Filtros
    FILTERS_LOADED = 'Filtros disponibles cargados exitosamente.'
    CATEGORY_PARAM_REQUIRED = 'Debe proporcionar el parámetro "categoria".'
    COLOR_PARAM_REQUIRED = 'Debe proporcionar el parámetro "color".'
    CATEGORY_NOT_ACTIVE = 'La categoría seleccionada no existe o no está activa.'
    NO_PRODUCTS_IN_CATEGORY = 'No hay productos disponibles en esta categoría.'
    NO_PRODUCTS_IN_COLOR = 'No hay productos disponibles en este tono.'
    NO_MEASURES_FOR_COLOR = 'No hay medidas asociadas a este tono.'
    NO_MEASURES_IN_CATEGORY = 'No hay medidas asociadas a este tono en la categoría seleccionada.'
    
    # Productos
    PRODUCT_NOT_AVAILABLE = 'Producto no encontrado o no disponible.'
    
    # =====================================================
    # IMÁGENES
    # =====================================================
    IMAGE_UPLOADED = 'Imagen subida correctamente.'
    IMAGE_MARKED_AS_PRINCIPAL = 'Imagen marcada como principal correctamente.'
    IMAGE_DELETED_PERMANENTLY = 'Imagen eliminada definitivamente (Cloudinary + BD).'
    IMAGE_DELETED_LOGICALLY = 'Imagen marcada como inactiva (eliminación lógica).'
    IMAGE_ALREADY_ACTIVE = 'La imagen ya está activa.'
    IMAGE_RESTORED = 'Imagen restaurada correctamente.'
    IMAGE_UPDATED = 'Imagen actualizada correctamente.'
    IMAGE_REORDERED = 'Imágenes reordenadas correctamente.'
    
    # Imágenes - Errores
    CANNOT_DELETE_PRINCIPAL_IMAGE = 'No se puede eliminar la imagen principal.'
    INVALID_ORDER_LIST = 'Debe enviar una lista no vacía en "orden".'
    INVALID_ORDER_FORMAT = 'Cada item debe tener "id_imagen" y "orden" enteros.'
    ORDER_MUST_BE_POSITIVE = 'Todos los "orden" deben ser >= 1.'
    DUPLICATE_IMAGE_IDS = 'Hay id_imagen duplicados.'
    DUPLICATE_ORDER_VALUES = 'Hay valores de "orden" duplicados.'
    IMAGES_NOT_BELONG_TO_PRODUCT = 'Las imágenes {ids} no pertenecen al producto o no existen.'
    NO_CHANGES_DETECTED = 'Sin cambios detectados.'
    
    # =====================================================
    # MÉTODOS DE PAGO
    # =====================================================
    PAYMENT_METHOD_CREATED = 'Método de pago creado correctamente.'
    PAYMENT_METHOD_UPDATED = 'Método de pago actualizado correctamente.'
    PAYMENT_METHOD_ACTIVATED = 'Método de pago activado correctamente.'
    PAYMENT_METHOD_DEACTIVATED = 'Método de pago desactivado correctamente.'
    PAYMENT_METHOD_ALREADY_ACTIVE = 'El método de pago ya está activo.'
    PAYMENT_METHOD_ALREADY_INACTIVE = 'El método de pago ya está inactivo.'
    PAYMENT_METHOD_NOT_FOUND = 'Método de pago no encontrado.'
    PAYMENT_METHOD_NAME_EXISTS = 'Ya existe un método con este nombre.'
    PAYMENT_METHOD_TYPE_INVALID = 'Tipo inválido. Use EFECTIVO, TARJETA o QR.'
    PAYMENT_METHOD_STATE_INVALID = 'Estado inválido. Use ACTIVO o INACTIVO.'
    
    # =====================================================
    # MÉTODOS HELPER
    # =====================================================
    @classmethod
    def get_error_detail(cls, field, error_type='invalid'):
        """
        Genera mensajes de error para campos específicos.
        
        Args:
            field (str): Nombre del campo
            error_type (str): Tipo de error (required, invalid, exists)
        """
        errors = {
            'required': f'El campo {field} es obligatorio.',
            'invalid': f'El valor del campo {field} es inválido.',
            'exists': f'El {field} ya existe.',
            'min_length': f'El {field} debe tener al menos los caracteres requeridos.',
            'max_length': f'El {field} excede la longitud máxima permitida.',
        }
        return errors.get(error_type, cls.INVALID_DATA)
