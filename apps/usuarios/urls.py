from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegistroClienteStep1View,
    RegistroClienteStep2View,
    RegistroVendedorView,
    RegistroAdministradorView,
    UsuarioListView,
    UsuarioDetailView,
    UsuarioUpdateView,
    PerfilClienteViewSet,
    DireccionClienteViewSet,
    buscar_clientes
    
)

# Importar las NUEVAS views de gestión administrativa
from .views.gestion_usuarios import UsuarioAdminViewSet

# Configurar el router para los endpoints administrativos y de perfil
router = DefaultRouter()

# Endpoints administrativos (solo para administradores)
router.register(r'admin/usuarios', UsuarioAdminViewSet, basename='admin-usuario')

# Endpoints de perfil del cliente (auto-gestión)
router.register(r'perfil', PerfilClienteViewSet, basename='perfil-cliente')

# Endpoints de direcciones del cliente
router.register(r'perfil/direcciones', DireccionClienteViewSet, basename='direcciones-cliente')

urlpatterns = [
    
    # --- Registro cliente (2 pasos)
    path("register/cliente/step1/", RegistroClienteStep1View.as_view(), name="register_cliente_step1"),
    path("register/cliente/step2/", RegistroClienteStep2View.as_view(), name="register_cliente_step2"),

    # --- Registro roles internos
    path("register/vendedor/", RegistroVendedorView.as_view(), name="register_vendedor"),
    path("register/admin/", RegistroAdministradorView.as_view(), name="register_admin"),

    # --- Gestión usuarios (básica - existente)
    path("list/", UsuarioListView.as_view(), name="usuario_list"),
    path("detail/<int:id_usuario>/", UsuarioDetailView.as_view(), name="usuario_detail"),
    path("update/<int:id_usuario>/", UsuarioUpdateView.as_view(), name="usuario_update"),
    path("buscar/", buscar_clientes, name="buscar_clientes"),
    
    # =================================================
    # ENDPOINTS CON ROUTER (ADMIN + PERFIL CLIENTE)
    # =================================================
    path("", include(router.urls)),
]