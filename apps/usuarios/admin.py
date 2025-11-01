from django.contrib import admin
from .models import Usuario, Cliente, Vendedor, Administrador, DireccionCliente
from apps.seguridad.models import Rol

# =====================================================
# ADMIN PARA USUARIO
# =====================================================
@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ['id_usuario', 'nombre_usuario', 'nombre_completo', 'correo', 'id_rol', 'estado_usuario']
    list_filter = ['id_rol', 'estado_usuario', 'sexo']
    search_fields = ['nombre_usuario', 'nombre_completo', 'correo']
    ordering = ['-fecha_registro']


# =====================================================
# ADMIN PARA CLIENTE
# =====================================================
@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ['id_cliente', 'get_nombre', 'get_correo']
    search_fields = ['id_cliente__nombre_usuario', 'id_cliente__nombre_completo']
    
    def get_nombre(self, obj):
        return obj.id_cliente.nombre_completo
    get_nombre.short_description = 'Nombre'
    
    def get_correo(self, obj):
        return obj.id_cliente.correo
    get_correo.short_description = 'Correo'


# =====================================================
# ADMIN PARA VENDEDOR
# =====================================================
@admin.register(Vendedor)
class VendedorAdmin(admin.ModelAdmin):
    list_display = ['id_vendedor', 'get_nombre', 'tipo_vendedor', 'fecha_contrato']
    list_filter = ['tipo_vendedor']
    search_fields = ['id_vendedor__nombre_usuario', 'id_vendedor__nombre_completo']
    
    def get_nombre(self, obj):
        return obj.id_vendedor.nombre_completo
    get_nombre.short_description = 'Nombre'


# =====================================================
# ADMIN PARA ADMINISTRADOR
# =====================================================
@admin.register(Administrador)
class AdministradorAdmin(admin.ModelAdmin):
    list_display = ['id_administrador', 'get_nombre', 'fecha_contrato']
    search_fields = ['id_administrador__nombre_usuario', 'id_administrador__nombre_completo']
    
    def get_nombre(self, obj):
        return obj.id_administrador.nombre_completo
    get_nombre.short_description = 'Nombre'


# =====================================================
# ADMIN PARA DIRECCION CLIENTE
# =====================================================
@admin.register(DireccionCliente)
class DireccionClienteAdmin(admin.ModelAdmin):
    list_display = [
        'id_direccion', 'get_cliente', 'etiqueta', 'direccion', 
        'ciudad', 'es_principal', 'guardada', 'fecha_creacion'
    ]
    list_filter = ['es_principal', 'guardada', 'ciudad', 'pais']
    search_fields = [
        'id_cliente__id_cliente__nombre_completo',
        'id_cliente__id_cliente__nombre_usuario',
        'direccion', 'ciudad', 'etiqueta'
    ]
    ordering = ['-fecha_creacion']
    
    def get_cliente(self, obj):
        return obj.id_cliente.id_cliente.nombre_completo
    get_cliente.short_description = 'Cliente'

