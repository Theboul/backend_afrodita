from rest_framework import serializers
from .models import Carrito, DetalleCarrito


class DetalleCarritoSerializer(serializers.ModelSerializer):
    nombre_producto = serializers.CharField(source='id_producto.nombre', read_only=True)
    precio_unitario = serializers.DecimalField(
        source='id_producto.precio', max_digits=10, decimal_places=2, read_only=True
    )

    class Meta:
        model = DetalleCarrito
        fields = [
            'id_producto',
            'nombre_producto',
            'cantidad',
            'precio_unitario',
            'precio_total'
        ]


class CarritoSerializer(serializers.ModelSerializer):
    detalles = DetalleCarritoSerializer(many=True, read_only=True)
    total_general = serializers.SerializerMethodField()

    class Meta:
        model = Carrito
        fields = [
            'id_carrito',
            'id_cliente',
            'fecha_creacion',
            'estado_carrito',
            'detalles',
            'total_general'
        ]

    def get_total_general(self, obj):
        return sum(det.precio_total for det in obj.detalles.all())