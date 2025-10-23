from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import ImagenProductoViewSet

router = DefaultRouter()
router.register(r'', ImagenProductoViewSet, basename='imagenes')

urlpatterns = [
    path('', include(router.urls)),
]
