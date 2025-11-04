from django.contrib import admin
from .models import PaymentTransaction, MetodoPago


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "id_transaccion", "id_venta", "id_metodo_pago", "monto",
        "estado_transaccion", "referencia_externa", "fecha_transaccion", "procesado_por"
    )
    list_filter = ("estado_transaccion", "id_metodo_pago", "fecha_transaccion")
    search_fields = ("referencia_externa", "descripcion")


@admin.register(MetodoPago)
class MetodoPagoAdmin(admin.ModelAdmin):
    list_display = ("id_metodo_pago", "tipo", "categoria", "requiere_pasarela", "activo")
    list_filter = ("activo", "categoria", "requiere_pasarela")
    search_fields = ("tipo",)
