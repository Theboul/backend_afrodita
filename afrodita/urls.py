"""
URL configuration for afrodita project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from apps.clientes.views import ClienteViewSet

router = DefaultRouter()
router.register('clientes', ClienteViewSet)

urlpatterns = [
    path('admin/', admin.site.urls),
    path("api/auth/", include("apps.autenticacion.urls")), 
    path("api/", include("apps.usuarios.urls")),
    path("api/productos/", include("apps.productos.urls")),
    path("api/clientes/", include("apps.clientes.urls")),
    path('api/', include(router.urls)),
    path("api/ventas/", include("apps.ventas.urls")),
    path("api/compras/", include("apps.compras.urls")),
]
