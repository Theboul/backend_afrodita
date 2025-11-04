from rest_framework import serializers


class MetodoPagoSerializer(serializers.Serializer):
    id_metodo_pago = serializers.IntegerField()
    tipo = serializers.CharField()
    categoria = serializers.CharField()
    requiere_pasarela = serializers.BooleanField()


class IniciarPagoSerializer(serializers.Serializer):
    id_venta = serializers.IntegerField()
    monto = serializers.DecimalField(max_digits=12, decimal_places=2)
    moneda = serializers.CharField(max_length=3)
    # Puedes enviar 'id_metodo_pago' o 'metodo' (tipo)
    id_metodo_pago = serializers.IntegerField(required=False)
    metodo = serializers.CharField(max_length=30, required=False, allow_blank=True)
    descripcion = serializers.CharField(required=False, allow_blank=True, max_length=120)
    referencia = serializers.CharField(required=False, allow_blank=True, max_length=100)


class ConfirmarPagoSerializer(serializers.Serializer):
    token = serializers.CharField()
