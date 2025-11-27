from rest_framework import serializers
from .models import DevolucionCompra, DetalleDevolucionCompra


class DetalleDevolucionCompraSerializer(serializers.ModelSerializer):
    class Meta:
        model = DetalleDevolucionCompra
        fields = "__all__"


class DevolucionCompraSerializer(serializers.ModelSerializer):
    detalles = DetalleDevolucionCompraSerializer(many=True, read_only=True)

    class Meta:
        model = DevolucionCompra
        fields = "__all__"
