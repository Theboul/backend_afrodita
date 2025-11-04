from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="ventas-index"),
    # Endpoints alineados a Neon (con autenticación)
    path("metodos-pago/", views.PaymentMethodsDBView.as_view(), name="ventas-metodos-pago"),
    path("iniciar-pago/", views.InitiatePaymentDBView.as_view(), name="ventas-iniciar-pago"),
    path("pagos/<str:referencia>/", views.PaymentStatusDBView.as_view(), name="ventas-estado-pago"),
    path("confirmar-pago/", views.ConfirmarPagoDBView.as_view(), name="ventas-confirmar-pago"),
]
