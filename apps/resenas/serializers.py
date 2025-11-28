from rest_framework import serializers

from core.constants import ReviewStatus, Messages
from .models import Resena


class ResenaSerializer(serializers.ModelSerializer):
    """Serializer de lectura para reseñas."""
    producto_id = serializers.CharField(source='id_producto.id_producto', read_only=True)
    producto_nombre = serializers.CharField(source='id_producto.nombre', read_only=True)
    cliente_id = serializers.IntegerField(source='id_cliente.id_cliente_id', read_only=True)
    cliente_nombre = serializers.CharField(source='id_cliente.id_cliente.nombre_completo', read_only=True)

    class Meta:
        model = Resena
        fields = [
            'id_resena',
            'producto_id',
            'producto_nombre',
            'cliente_id',
            'cliente_nombre',
            'calificacion',
            'comentario',
            'estado',
            'fecha_creacion',
        ]
        read_only_fields = fields


class CrearResenaSerializer(serializers.ModelSerializer):
    """Serializer para crear reseñas (cliente)."""

    class Meta:
        model = Resena
        fields = ['id_producto', 'calificacion', 'comentario']

    def validate_calificacion(self, value):
        if value is None:
            raise serializers.ValidationError(Messages.REQUIRED_FIELD)
        if not (1 <= value <= 5):
            raise serializers.ValidationError(Messages.REVIEW_INVALID_RATING)
        return value

    def validate_comentario(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError(Messages.REQUIRED_FIELD)
        if len(value.strip()) < 5:
            raise serializers.ValidationError("El comentario debe tener al menos 5 caracteres.")
        return value.strip()
