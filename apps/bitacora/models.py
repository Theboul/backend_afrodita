from django.db import models
from django.conf import settings

class Bitacora(models.Model):
    """
    Modelo adaptado a la tabla existente `bitacora`,
    pero con mejoras modernas para auditoría y extensibilidad.
    """
    ACCIONES = [
        # =====================================================
        # Autenticación y sesiones
        # =====================================================
        ('LOGIN', 'Inicio de sesión'),
        ('LOGOUT', 'Cierre de sesión'),
        ('LOGOUT_ERROR', 'Error al cerrar sesión'),
        ('FAILED_LOGIN', 'Intento fallido de inicio de sesión'),
        ('TOKEN_INVALIDATION', 'Invalidación de token'),

        # =====================================================
        # Gestión de usuarios
        # =====================================================
        ('REGISTER', 'Registro de usuario'),
        ('PASSWORD_CHANGE', 'Cambio de contraseña'),
        ('PASSWORD_RESET', 'Reseteo de contraseña'),
        ('PROFILE_UPDATE', 'Actualización de perfil'),
        ('DELETE_ACCOUNT', 'Eliminación de cuenta'),
        ('PERMISSION_CHANGE', 'Cambio de permisos'),

        # =====================================================
        # Navegación y acceso
        # =====================================================
        ('VIEW_ACCESS', 'Acceso a vista'),
        ('PAGE_VIEW', 'Vista de página'),
        ('PRODUCT_VIEW', 'Vista de producto'),

        # =====================================================
        # Usuarios anónimos (para una dashboard pública)
        # =====================================================
        ('ANONYMOUS_VIEW', 'Vista de usuario anónimo'),
        ('ANONYMOUS_PRODUCT_VIEW', 'Vista de producto por usuario anónimo'),
        ('ANONYMOUS_SEARCH', 'Búsqueda por usuario anónimo'),

        # =====================================================
        # Gestión de categorías
        # =====================================================
        ('CATEGORY_CREATE', 'Creación de categoría'),
        ('CATEGORY_UPDATE', 'Actualización de categoría'),
        ('CATEGORY_MOVE', 'Movimiento de categoría'),
        ('CATEGORY_DELETE', 'Eliminación lógica de categoría'),
        ('CATEGORY_RESTORE', 'Restauración de categoría'),

        # =====================================================
        # Gestión de productos
        # =====================================================
        ('PRODUCT_CREATE', 'Creación de producto'),
        ('PRODUCT_UPDATE', 'Actualización de producto'),
        ('PRODUCT_DELETE', 'Eliminación de producto'),
        ('PRODUCT_STATE_CHANGE', 'Cambio de estado de producto'),
        ('PRODUCT_STOCK_ADJUST', 'Ajuste de stock de producto'),

        # =====================================================
        # Gestión de imágenes del catálogo
        # =====================================================
        ('IMAGE_UPLOAD', 'Subida de imagen de producto'),
        ('IMAGE_DELETE', 'Eliminación de imagen de producto'),
        ('IMAGE_SET_MAIN', 'Cambio de imagen principal'),
        ('IMAGE_REORDER', 'Reordenamiento de imágenes'),
        ('IMAGE_RESTORE', 'Restauración de imagen de producto'),
        ('IMAGE_UPDATE', 'Actualización de metadatos de imagen'),

        # =====================================================
        # Errores y seguridad
        # =====================================================
        ('ERROR_404', 'Página no encontrada'),
        ('ERROR_500', 'Error interno del servidor'),
        ('SUSPICIOUS_ACTIVITY', 'Actividad sospechosa'),
    ]


    id_bitacora = models.AutoField(primary_key=True)
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")
    accion = models.CharField(max_length=255, choices=ACCIONES)
    descripcion = models.TextField(blank=True, null=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column='id_usuario',
        related_name='bitacora_eventos',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'bitacora'
        ordering = ['-fecha_hora']

    def __str__(self):
        usuario = self.id_usuario.nombre_usuario if self.id_usuario else "Usuario anónimo"
        return f"{self.accion} - {usuario} - {self.fecha_hora}"