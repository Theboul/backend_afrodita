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
)

# Importar las NUEVAS views de gestión administrativa
from .views.gestion_usuarios import UsuarioAdminViewSet

# Configurar el router para los endpoints administrativos
router = DefaultRouter()
router.register(r'admin/usuarios', UsuarioAdminViewSet, basename='admin-usuario')

urlpatterns = [
    # =================================================
    # ENDPOINTS EXISTENTES (SE MANTIENEN IGUAL)
    # =================================================
    
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
    
    # =================================================
    # NUEVOS ENDPOINTS ADMINISTRATIVOS (SE AGREGAN)
    # =================================================
    path("", include(router.urls)),
]