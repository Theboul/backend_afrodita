from django.contrib import admin
from .models import Permiso, Rol, RolPermiso, UsuarioPermiso

# =====================================================
# ADMIN DE PERMISOS
# =====================================================

@admin.register(Permiso)
class PermisoAdmin(admin.ModelAdmin):
    list_display = ['codigo', 'nombre', 'modulo', 'activo', 'fecha_creacion']
    list_filter = ['modulo', 'activo', 'fecha_creacion']
    search_fields = ['nombre', 'codigo', 'descripcion']
    ordering = ['modulo', 'nombre']
    readonly_fields = ['fecha_creacion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'codigo', 'modulo')
        }),
        ('Detalles', {
            'fields': ('descripcion', 'activo')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )


# =====================================================
# INLINE DE PERMISOS PARA ROL
# =====================================================

class RolPermisoInline(admin.TabularInline):
    model = Rol.permisos.through
    extra = 1
    verbose_name = "Permiso"
    verbose_name_plural = "Permisos Asignados"
    autocomplete_fields = ['permiso']
    readonly_fields = ['fecha_asignacion', 'asignado_por']
    
    def get_queryset(self, request):
        """Mostrar solo permisos activos"""
        qs = super().get_queryset(request)
        return qs.select_related('permiso', 'asignado_por')


# =====================================================
# ADMIN DE ROLES
# =====================================================

@admin.register(Rol)
class RolAdmin(admin.ModelAdmin):
    list_display = ['nombre', 'es_sistema', 'activo', 'cantidad_permisos', 'cantidad_usuarios', 'fecha_creacion']
    list_filter = ['es_sistema', 'activo', 'fecha_creacion']
    search_fields = ['nombre', 'descripcion']
    ordering = ['nombre']
    readonly_fields = ['fecha_creacion', 'fecha_modificacion']
    inlines = [RolPermisoInline]
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('nombre', 'descripcion')
        }),
        ('Configuración', {
            'fields': ('es_sistema', 'activo')
        }),
        ('Auditoría', {
            'fields': ('fecha_creacion', 'fecha_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def cantidad_permisos(self, obj):
        """Mostrar cantidad de permisos asignados"""
        return obj.permisos.count()
    cantidad_permisos.short_description = 'Permisos'
    
    def cantidad_usuarios(self, obj):
        """Mostrar cantidad de usuarios con este rol"""
        return obj.usuarios.count()
    cantidad_usuarios.short_description = 'Usuarios'
    
    def get_readonly_fields(self, request, obj=None):
        """Hacer nombre readonly para roles de sistema"""
        readonly = list(self.readonly_fields)
        if obj and obj.es_sistema:
            readonly.append('nombre')
            readonly.append('es_sistema')
        return readonly


# =====================================================
# ADMIN DE ROL-PERMISO (Tabla Intermedia)
# =====================================================

@admin.register(RolPermiso)
class RolPermisoAdmin(admin.ModelAdmin):
    list_display = ['rol', 'permiso', 'asignado_por', 'fecha_asignacion']
    list_filter = ['rol', 'fecha_asignacion']
    search_fields = ['rol__nombre', 'permiso__nombre', 'permiso__codigo']
    ordering = ['-fecha_asignacion']
    readonly_fields = ['fecha_asignacion']
    autocomplete_fields = ['rol', 'permiso', 'asignado_por']
    
    def get_queryset(self, request):
        """Optimizar consultas"""
        return super().get_queryset(request).select_related('rol', 'permiso', 'asignado_por')


# =====================================================
# ADMIN DE USUARIO-PERMISO
# =====================================================

@admin.register(UsuarioPermiso)
class UsuarioPermisoAdmin(admin.ModelAdmin):
    list_display = [
        'usuario', 'permiso', 'tipo_permiso', 'activo', 
        'fecha_expiracion', 'asignado_por', 'fecha_asignacion'
    ]
    list_filter = ['concedido', 'activo', 'fecha_expiracion', 'fecha_asignacion']
    search_fields = [
        'usuario__nombre_completo', 'usuario__nombre_usuario',
        'permiso__nombre', 'permiso__codigo'
    ]
    ordering = ['-fecha_asignacion']
    readonly_fields = ['fecha_asignacion', 'activo']
    autocomplete_fields = ['usuario', 'permiso', 'asignado_por']

    fieldsets = (
        ('Asignación', {
            'fields': ('usuario', 'permiso', 'concedido')
        }),
        ('Detalles', {
            'fields': ('fecha_expiracion', 'motivo')
        }),
        ('Auditoría', {
            'fields': ('asignado_por', 'fecha_asignacion', 'activo'),
            'classes': ('collapse',)
        }),
    )

    def tipo_permiso(self, obj):
        """Mostrar si es concesión o revocación"""
        return "Concedido" if obj.concedido else "Revocado"
    tipo_permiso.short_description = 'Tipo'

    def get_queryset(self, request):
        """Optimizar consultas"""
        return super().get_queryset(request).select_related('usuario', 'permiso', 'asignado_por')


# =====================================================
# CONFIGURACIÓN DEL ADMIN
# =====================================================

# Configurar búsquedas autocomplete
admin.site.empty_value_display = '(Ninguno)'

