from django.urls import path
from rest_framework.routers import DefaultRouter
from .views import PaymentMethodViewSet, conciliar_transaccion
app_name = 'pagos'

router = DefaultRouter()
router.register(r'', PaymentMethodViewSet, basename='metodos-pago')

urlpatterns = [
    path('conciliar/', conciliar_transaccion, name='conciliar-transaccion'),
]

urlpatterns += router.urls
