from rest_framework.routers import DefaultRouter
from .views import EnvioViewSet, TipoEnvioViewSet

router = DefaultRouter()
router.register(r"tipo-envio", TipoEnvioViewSet, basename="tipo-envio")
router.register(r"envios", EnvioViewSet, basename="envios")

urlpatterns = router.urls
