from rest_framework import serializers
from .models import Carrito, DetalleCarrito
from apps.productos.models import Producto

class DetalleCarritoSerializer(serializers.ModelSerializer):
    nombre_producto = serializers.CharField(source='id_producto.nombre', read_only=True)
    precio_unitario = serializers.DecimalField(
        source='id_producto.precio', read_only=True, max_digits=10, decimal_places=2
    )

    class Meta:
        model = DetalleCarrito
        fields = ['id_producto', 'nombre_producto', 'cantidad', 'precio_unitario', 'precio_total']


class CarritoSerializer(serializers.ModelSerializer):
    detalles = DetalleCarritoSerializer(many=True, read_only=True)

    class Meta:
        model = Carrito
        fields = ['id_carrito', 'fecha_creacion', 'estado_carrito', 'id_cliente', 'detalles']
