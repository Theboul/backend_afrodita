from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductoViewSet, ConfiguracionLenteViewSet, ProductoConImagenViewSet

# Router para los viewsets
router = DefaultRouter()
router.register(r'productos-imagen', ProductoConImagenViewSet, basename='producto-imagen')
router.register(r'', ProductoViewSet, basename='productos')
router.register(r'configuraciones', ConfiguracionLenteViewSet, basename='configuraciones')


urlpatterns = [
    path('', include(router.urls)),
]