from rest_framework import permissions
from .models import Cliente

# =====================================================
# PERMISOS PERSONALIZADOS PARA CLIENTE
# =====================================================

class EsPropietarioPerfil(permissions.BasePermission):
    """
    Permiso: Solo el dueño del perfil puede verlo/editarlo
    Se aplica a nivel de objeto
    """
    message = "No tienes permiso para acceder a este perfil."
    
    def has_object_permission(self, request, view, obj):
        # obj es un Usuario
        return obj.id_usuario == request.user.id_usuario


class EsPropietarioDireccion(permissions.BasePermission):
    """
    Permiso: Solo el cliente dueño de la dirección puede gestionarla
    """
    message = "No tienes permiso para acceder a esta dirección."
    
    def has_object_permission(self, request, view, obj):
        # obj es una DireccionCliente
        # Verificar que la dirección pertenezca al cliente del usuario logueado
        try:
            cliente = Cliente.objects.get(id_cliente=request.user)
            return obj.id_cliente == cliente
        except Cliente.DoesNotExist:
            return False


class EsCliente(permissions.BasePermission):
    """
    Permiso: Solo usuarios con rol CLIENTE pueden acceder
    """
    message = "Solo clientes pueden acceder a este recurso."
    
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.id_rol and 
            request.user.id_rol.nombre == 'CLIENTE'
        )


class EsClienteOAdmin(permissions.BasePermission):
    """
    Permiso: Permite acceso a clientes (solo sus recursos) y administradores/vendedores (todos los recursos)
    """
    message = "No tienes permisos para acceder a este recurso."
    
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        
        if not request.user.id_rol:
            return False
        
        # Permitir si es CLIENTE, ADMINISTRADOR o VENDEDOR
        return request.user.id_rol.nombre in ['CLIENTE', 'ADMINISTRADOR', 'VENDEDOR']
