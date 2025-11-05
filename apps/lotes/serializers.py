from rest_framework import serializers
from django.utils import timezone
from datetime import date
from .models import Lote

class LoteSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source='producto.nombre', read_only=True)
    esta_vencido = serializers.SerializerMethodField()
    dias_por_vencer = serializers.SerializerMethodField()

    class Meta:
        model = Lote
        fields = [
            'id_lote', 'cantidad', 'fecha_vencimiento',
            'producto', 'producto_nombre',
            'esta_vencido', 'dias_por_vencer'
        ]

    def validate_cantidad(self, value):
        if value <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
        return value

    def validate_fecha_vencimiento(self, value):
        if value <= date.today():
            raise serializers.ValidationError("La fecha de vencimiento debe ser futura.")
        return value

    def get_esta_vencido(self, obj):
        return obj.fecha_vencimiento <= timezone.now().date()

    def get_dias_por_vencer(self, obj):
        return (obj.fecha_vencimiento - timezone.now().date()).days
