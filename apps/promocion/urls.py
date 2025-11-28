from rest_framework.routers import DefaultRouter
from .views import PromocionViewSet

router = DefaultRouter()
router.register(r'', PromocionViewSet, basename='promociones')

urlpatterns = router.urls
