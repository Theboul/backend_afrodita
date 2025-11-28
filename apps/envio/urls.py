from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import EnvioViewSet, TipoEnvioViewSet, listar_envios_detallados

router = DefaultRouter()
router.register(r"tipo-envio", TipoEnvioViewSet, basename="tipo-envio")
router.register(r"envios", EnvioViewSet, basename="envios")

urlpatterns = router.urls + [
    path("envios-detallados/", listar_envios_detallados),
]
