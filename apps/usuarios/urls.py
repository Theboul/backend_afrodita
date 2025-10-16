from django.urls import path
from .views import (
    RegistroClienteStep1View,
    RegistroClienteStep2View,
    RegistroVendedorView,
    RegistroAdministradorView,
    UsuarioListView,
    UsuarioDetailView,
    UsuarioUpdateView,
)

urlpatterns = [
    # --- Registro cliente (2 pasos)
    path("register/cliente/step1/", RegistroClienteStep1View.as_view(), name="register_cliente_step1"),
    path("register/cliente/step2/", RegistroClienteStep2View.as_view(), name="register_cliente_step2"),

    # --- Registro roles internos
    path("register/vendedor/", RegistroVendedorView.as_view(), name="register_vendedor"),
    path("register/admin/", RegistroAdministradorView.as_view(), name="register_admin"),

    # --- Gestión usuarios
    path("list/", UsuarioListView.as_view(), name="usuario_list"),
    path("detail/<int:id_usuario>/", UsuarioDetailView.as_view(), name="usuario_detail"),
    path("update/<int:id_usuario>/", UsuarioUpdateView.as_view(), name="usuario_update"),
]
