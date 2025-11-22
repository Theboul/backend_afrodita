from django.urls import path
from .views import (
    crear_venta_presencial,
    anular_venta,
    obtener_venta,
    listar_ventas,
    confirmar_pago_manual,
    PaymentMethodsDBView,
    InitiatePaymentDBView,
    PaymentStatusDBView,
    ConfirmarPagoDBView,
    VentaPaymentSummaryView,
    StripeCreateIntentView,
    StripeWebhookView,
    create_payment_intent,
)

urlpatterns = [

    # ----------- RUTAS PRINCIPALES SIN CONFLICTOS -----------
    path("", listar_ventas, name="listar_ventas"),
    path("presencial/", crear_venta_presencial, name="venta_presencial"),

    # ----------- RUTAS DE PAGOS (ANTES DE <int:id_venta>!) -----------
    path("metodos-pago/", PaymentMethodsDBView.as_view(), name="ventas-metodos-pago"),
    path("iniciar-pago/", InitiatePaymentDBView.as_view(), name="ventas-iniciar-pago"),
    path("pagos/<str:referencia>/", PaymentStatusDBView.as_view(), name="ventas-estado-pago"),
    path("confirmar-pago/", ConfirmarPagoDBView.as_view(), name="ventas-confirmar-pago"),
    path("venta/<int:id_venta>/resumen/", VentaPaymentSummaryView.as_view(), name="ventas-resumen-venta"),

    # ----------- STRIPE -----------
    path("stripe/create-intent/", StripeCreateIntentView.as_view(), name="ventas-stripe-create-intent"),
    path("stripe/webhook/", StripeWebhookView.as_view(), name="ventas-stripe-webhook"),

    # ----------- TEST -----------
    path("create-payment-intent/", create_payment_intent, name="ventas-create-payment-intent"),

    # ----------- RUTAS NUMÉRICAS -----------
    path("<int:id_venta>/", obtener_venta, name="obtener_venta"),
    path("<int:id_venta>/anular/", anular_venta, name="anular_venta"),
    path("<int:id_venta>/confirmar/", confirmar_pago_manual, name="confirmar_pago_manual"),

]
