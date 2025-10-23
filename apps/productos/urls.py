from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ProductoViewSet, ConfiguracionLenteViewSet

# Router para los viewsets
router = DefaultRouter()
router.register(r'configuraciones', ConfiguracionLenteViewSet, basename='configuraciones')
router.register(r'', ProductoViewSet, basename='productos')


urlpatterns = [
    path('', include(router.urls)),
]