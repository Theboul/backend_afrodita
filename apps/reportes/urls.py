from django.urls import path

from .views import (
    BitacoraActionsView,
    GenerarReporteView,
    ReportTypesView,
    buscar_usuarios,
)

urlpatterns = [
    path("tipos/", ReportTypesView.as_view(), name="reportes-tipos"),
    path("generar/", GenerarReporteView.as_view(), name="reportes-generar"),
    path(
        "bitacora/acciones/",
        BitacoraActionsView.as_view(),
        name="reportes-bitacora-acciones",
    ),
    path(
        "usuarios/buscar/",
        buscar_usuarios,
        name="reportes-usuarios-buscar",
    ),
]
