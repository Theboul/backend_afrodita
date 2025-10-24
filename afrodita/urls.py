from django.contrib import admin
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.decorators import api_view
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)

@api_view(['GET'])
def api_root(request, format=None):
    """Vista raíz del API – muestra los módulos disponibles."""
    return Response({
        "auth": request.build_absolute_uri("/api/auth/"),
        "usuarios": request.build_absolute_uri("/api/usuarios/"),
        "categorias": request.build_absolute_uri("/api/categorias/"),
        "productos": request.build_absolute_uri("/api/productos/"),
        "ventas": request.build_absolute_uri("/api/ventas/"),
        "compras": request.build_absolute_uri("/api/compras/"),
        "bitacora": request.build_absolute_uri("/api/bitacora/"),
        "imagenes": request.build_absolute_uri("/api/imagenes/"),
        "documentacion": {
            "swagger": request.build_absolute_uri("/api/docs/"),
            "redoc": request.build_absolute_uri("/api/redoc/"),
            "schema": request.build_absolute_uri("/api/schema/")
        }
    })

urlpatterns = [
    path("admin/", admin.site.urls),

    # Vista raíz del API
    path("api/", api_root, name="api-root"),

    # Módulos
    path("api/auth/", include("apps.autenticacion.urls")),
    path("api/usuarios/", include("apps.usuarios.urls")),
    path("api/categorias/", include("apps.categoria.urls")),
    path("api/productos/", include("apps.productos.urls")),
    path("api/ventas/", include("apps.ventas.urls")),
    path("api/compras/", include("apps.compras.urls")),
    path("api/bitacora/", include("apps.bitacora.urls")),
    path("api/imagenes/", include("apps.imagenes.urls")),
    path('api/catalogo/', include('apps.catalogo.urls')),

    # Documentación automática
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
]