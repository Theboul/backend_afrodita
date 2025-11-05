from rest_framework.routers import DefaultRouter
from .views import PaymentMethodViewSet
app_name = 'pagos'

router = DefaultRouter()
router.register(r'', PaymentMethodViewSet, basename='metodos-pago')

urlpatterns = router.urls
