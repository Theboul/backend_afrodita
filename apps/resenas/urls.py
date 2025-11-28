from rest_framework.routers import DefaultRouter

from .views import ResenaViewSet

router = DefaultRouter()
router.register(r'', ResenaViewSet, basename='resenas')

urlpatterns = router.urls
