from django.urls import path
from . import views

urlpatterns = [
    path("", views.index, name="ventas-index"),
    # Pasarela de pagos (alineada a Neon, requiere auth)
    path("metodos-pago/", views.PaymentMethodsDBView.as_view(), name="ventas-metodos-pago"),
    path("iniciar-pago/", views.InitiatePaymentDBView.as_view(), name="ventas-iniciar-pago"),
    path("pagos/<str:referencia>/", views.PaymentStatusDBView.as_view(), name="ventas-estado-pago"),
    path("confirmar-pago/", views.ConfirmarPagoDBView.as_view(), name="ventas-confirmar-pago"),
    path("venta/<int:id_venta>/resumen/", views.VentaPaymentSummaryView.as_view(), name="ventas-resumen-venta"),
    # Stripe endpoints
    path("stripe/create-intent/", views.StripeCreateIntentView.as_view(), name="ventas-stripe-create-intent"),
    path("stripe/webhook/", views.StripeWebhookView.as_view(), name="ventas-stripe-webhook"),
    path("create-payment-intent/", views.create_payment_intent, name="ventas-create-payment-intent"),
]
