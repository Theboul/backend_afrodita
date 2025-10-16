from django.contrib import admin
from .models import Bitacora

@admin.register(Bitacora)
class BitacoraAdmin(admin.ModelAdmin):
    """
    Configuración del admin para gestionar registros de bitácora.
    """
    list_display = [
        'id_bitacora', 
        'fecha_hora', 
        'accion', 
        'get_usuario', 
        'ip', 
        'descripcion_corta'
    ]
    
    list_filter = [
        'accion',
        'fecha_hora',
        'id_usuario',
    ]
    
    search_fields = [
        'accion',
        'descripcion',
        'ip',
        'id_usuario__nombre_usuario',
        'id_usuario__correo'
    ]
    
    readonly_fields = [
        'id_bitacora',
        'fecha_hora',
        'accion',
        'descripcion',
        'ip',
        'id_usuario'
    ]
    
    ordering = ['-fecha_hora']
    
    list_per_page = 50
    
    date_hierarchy = 'fecha_hora'
    
    def get_usuario(self, obj):
        """Muestra el usuario o 'Anónimo' si es None."""
        return obj.id_usuario.nombre_usuario if obj.id_usuario else "Anónimo"
    get_usuario.short_description = 'Usuario'
    get_usuario.admin_order_field = 'id_usuario__nombre_usuario'
    
    def descripcion_corta(self, obj):
        """Muestra una versión corta de la descripción."""
        return obj.descripcion[:50] + '...' if obj.descripcion and len(obj.descripcion) > 50 else obj.descripcion
    descripcion_corta.short_description = 'Descripción'
    
    def has_add_permission(self, request):
        """No permitir agregar registros manualmente."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No permitir editar registros."""
        return False
