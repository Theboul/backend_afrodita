from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'devoluciones', views.DevolucionCompraViewSet, basename='devolucion-compra')
router.register(r'ordenes', views.OrdenCompraViewSet, basename='orden-compra')

urlpatterns = [
    path('', views.index, name='compras-index'),
    path('', include(router.urls)),
]
