"""
Constantes para acciones de auditoría y bitácora.
Centraliza todas las acciones registrables en el sistema.
"""


class BitacoraActions:
    """Acciones registrables en la bitácora del sistema."""
    
    # =====================================================
    # AUTENTICACIÓN Y SESIONES
    # =====================================================
    LOGIN = 'LOGIN'
    LOGOUT = 'LOGOUT'
    LOGOUT_ERROR = 'LOGOUT_ERROR'
    FAILED_LOGIN = 'FAILED_LOGIN'
    TOKEN_INVALIDATION = 'TOKEN_INVALIDATION'
    
    # =====================================================
    # GESTIÓN DE USUARIOS
    # =====================================================
    REGISTER = 'REGISTER'
    PASSWORD_CHANGE = 'PASSWORD_CHANGE'
    PASSWORD_RESET = 'PASSWORD_RESET'
    PROFILE_UPDATE = 'PROFILE_UPDATE'
    DELETE_ACCOUNT = 'DELETE_ACCOUNT'
    PERMISSION_CHANGE = 'PERMISSION_CHANGE'
    
    # =====================================================
    # NAVEGACIÓN Y ACCESO
    # =====================================================
    VIEW_ACCESS = 'VIEW_ACCESS'
    PAGE_VIEW = 'PAGE_VIEW'
    PRODUCT_VIEW = 'PRODUCT_VIEW'
    
    # =====================================================
    # USUARIOS ANÓNIMOS
    # =====================================================
    ANONYMOUS_VIEW = 'ANONYMOUS_VIEW'
    ANONYMOUS_PRODUCT_VIEW = 'ANONYMOUS_PRODUCT_VIEW'
    ANONYMOUS_SEARCH = 'ANONYMOUS_SEARCH'
    
    # =====================================================
    # GESTIÓN DE CATEGORÍAS
    # =====================================================
    CATEGORY_CREATE = 'CATEGORY_CREATE'
    CATEGORY_UPDATE = 'CATEGORY_UPDATE'
    CATEGORY_MOVE = 'CATEGORY_MOVE'
    CATEGORY_DELETE = 'CATEGORY_DELETE'
    CATEGORY_RESTORE = 'CATEGORY_RESTORE'
    
    # =====================================================
    # GESTIÓN DE PRODUCTOS
    # =====================================================
    PRODUCT_CREATE = 'PRODUCT_CREATE'
    PRODUCT_UPDATE = 'PRODUCT_UPDATE'
    PRODUCT_DELETE = 'PRODUCT_DELETE'
    PRODUCT_STATE_CHANGE = 'PRODUCT_STATE_CHANGE'
    PRODUCT_STOCK_ADJUST = 'PRODUCT_STOCK_ADJUST'
    
    # =====================================================
    # GESTIÓN DE IMÁGENES
    # =====================================================
    IMAGE_UPLOAD = 'IMAGE_UPLOAD'
    IMAGE_DELETE = 'IMAGE_DELETE'
    IMAGE_SET_MAIN = 'IMAGE_SET_MAIN'
    IMAGE_REORDER = 'IMAGE_REORDER'
    IMAGE_RESTORE = 'IMAGE_RESTORE'
    IMAGE_UPDATE = 'IMAGE_UPDATE'
    
    # =====================================================
    # GESTIÓN DE DIRECCIONES DE CLIENTES
    # =====================================================
    ADDRESS_CREATE = 'ADDRESS_CREATE'
    ADDRESS_UPDATE = 'ADDRESS_UPDATE'
    ADDRESS_DELETE = 'ADDRESS_DELETE'
    ADDRESS_SET_PRINCIPAL = 'ADDRESS_SET_PRINCIPAL'
    
    # =====================================================
    # GESTIÓN DE ROLES Y PERMISOS (CU4)
    # =====================================================
    ROLE_CREATED = 'ROLE_CREATED'
    ROLE_UPDATED = 'ROLE_UPDATED'
    ROLE_DELETED = 'ROLE_DELETED'
    PERMISSION_CREATED = 'PERMISSION_CREATED'
    PERMISSION_UPDATED = 'PERMISSION_UPDATED'
    PERMISSION_DELETED = 'PERMISSION_DELETED'
    PERMISSION_ASSIGNED_TO_ROLE = 'PERMISSION_ASSIGNED_TO_ROLE'
    PERMISSION_REMOVED_FROM_ROLE = 'PERMISSION_REMOVED_FROM_ROLE'
    PERMISSION_GRANTED_TO_USER = 'PERMISSION_GRANTED_TO_USER'
    PERMISSION_REVOKED_FROM_USER = 'PERMISSION_REVOKED_FROM_USER'
    
    # =====================================================
    # ERRORES Y SEGURIDAD
    # =====================================================
    ERROR_404 = 'ERROR_404'
    ERROR_500 = 'ERROR_500'
    SUSPICIOUS_ACTIVITY = 'SUSPICIOUS_ACTIVITY'
    
    # =====================================================
    # MÉTODOS HELPER
    # =====================================================
    @classmethod
    def choices(cls):
        """
        Retorna tuplas para usar en choices de Django.
        """
        return [
            # Autenticación
            (cls.LOGIN, 'Inicio de sesión'),
            (cls.LOGOUT, 'Cierre de sesión'),
            (cls.LOGOUT_ERROR, 'Error al cerrar sesión'),
            (cls.FAILED_LOGIN, 'Intento fallido de inicio de sesión'),
            (cls.TOKEN_INVALIDATION, 'Invalidación de token'),
            
            # Usuarios
            (cls.REGISTER, 'Registro de usuario'),
            (cls.PASSWORD_CHANGE, 'Cambio de contraseña'),
            (cls.PASSWORD_RESET, 'Reseteo de contraseña'),
            (cls.PROFILE_UPDATE, 'Actualización de perfil'),
            (cls.DELETE_ACCOUNT, 'Eliminación de cuenta'),
            (cls.PERMISSION_CHANGE, 'Cambio de permisos'),
            
            # Navegación
            (cls.VIEW_ACCESS, 'Acceso a vista'),
            (cls.PAGE_VIEW, 'Vista de página'),
            (cls.PRODUCT_VIEW, 'Vista de producto'),
            
            # Anónimos
            (cls.ANONYMOUS_VIEW, 'Vista de usuario anónimo'),
            (cls.ANONYMOUS_PRODUCT_VIEW, 'Vista de producto por usuario anónimo'),
            (cls.ANONYMOUS_SEARCH, 'Búsqueda por usuario anónimo'),
            
            # Categorías
            (cls.CATEGORY_CREATE, 'Creación de categoría'),
            (cls.CATEGORY_UPDATE, 'Actualización de categoría'),
            (cls.CATEGORY_MOVE, 'Movimiento de categoría'),
            (cls.CATEGORY_DELETE, 'Eliminación lógica de categoría'),
            (cls.CATEGORY_RESTORE, 'Restauración de categoría'),
            
            # Productos
            (cls.PRODUCT_CREATE, 'Creación de producto'),
            (cls.PRODUCT_UPDATE, 'Actualización de producto'),
            (cls.PRODUCT_DELETE, 'Eliminación de producto'),
            (cls.PRODUCT_STATE_CHANGE, 'Cambio de estado de producto'),
            (cls.PRODUCT_STOCK_ADJUST, 'Ajuste de stock de producto'),
            
            # Imágenes
            (cls.IMAGE_UPLOAD, 'Subida de imagen de producto'),
            (cls.IMAGE_DELETE, 'Eliminación de imagen de producto'),
            (cls.IMAGE_SET_MAIN, 'Cambio de imagen principal'),
            (cls.IMAGE_REORDER, 'Reordenamiento de imágenes'),
            (cls.IMAGE_RESTORE, 'Restauración de imagen de producto'),
            (cls.IMAGE_UPDATE, 'Actualización de metadatos de imagen'),
            
            # Direcciones
            (cls.ADDRESS_CREATE, 'Creación de dirección de cliente'),
            (cls.ADDRESS_UPDATE, 'Actualización de dirección de cliente'),
            (cls.ADDRESS_DELETE, 'Eliminación de dirección de cliente'),
            (cls.ADDRESS_SET_PRINCIPAL, 'Cambio de dirección principal'),
            
            # Roles y Permisos
            (cls.ROLE_CREATED, 'Creación de rol'),
            (cls.ROLE_UPDATED, 'Actualización de rol'),
            (cls.ROLE_DELETED, 'Eliminación de rol'),
            (cls.PERMISSION_CREATED, 'Creación de permiso'),
            (cls.PERMISSION_UPDATED, 'Actualización de permiso'),
            (cls.PERMISSION_DELETED, 'Eliminación de permiso'),
            (cls.PERMISSION_ASSIGNED_TO_ROLE, 'Asignación de permiso a rol'),
            (cls.PERMISSION_REMOVED_FROM_ROLE, 'Remoción de permiso de rol'),
            (cls.PERMISSION_GRANTED_TO_USER, 'Concesión de permiso individual a usuario'),
            (cls.PERMISSION_REVOKED_FROM_USER, 'Revocación de permiso individual de usuario'),
            
            # Errores
            (cls.ERROR_404, 'Página no encontrada'),
            (cls.ERROR_500, 'Error interno del servidor'),
            (cls.SUSPICIOUS_ACTIVITY, 'Actividad sospechosa'),
        ]
    
    @classmethod
    def all(cls):
        """Retorna lista de todas las acciones válidas."""
        return [choice[0] for choice in cls.choices()]
    
    @classmethod
    def is_valid(cls, accion):
        """Valida si una acción es válida."""
        return accion in cls.all()
    
    @classmethod
    def get_description(cls, accion):
        """Obtiene la descripción de una acción."""
        for choice in cls.choices():
            if choice[0] == accion:
                return choice[1]
        return 'Acción desconocida'
