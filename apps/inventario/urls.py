from rest_framework.routers import DefaultRouter
from .views import InventarioViewSet

router = DefaultRouter()
router.register(r"inventario", InventarioViewSet, basename="inventario")

urlpatterns = router.urls
