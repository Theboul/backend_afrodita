from rest_framework.routers import DefaultRouter
from .views import LoteViewSet

router = DefaultRouter()
router.register(r'', LoteViewSet, basename='lotes')

urlpatterns = router.urls
