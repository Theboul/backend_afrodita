from rest_framework import serializers
from .models import Venta, DetalleVenta

class DetalleVentaSerializer(serializers.ModelSerializer):
    nombre_producto = serializers.CharField(source='id_producto.nombre', read_only=True)

    class Meta:
        model = DetalleVenta
        fields = [
            'id_detalle_venta',
            'id_producto',
            'nombre_producto',
            'cantidad',
            'precio',
            'sub_total',
        ]


class VentaSerializer(serializers.ModelSerializer):
    detalles = DetalleVentaSerializer(many=True, read_only=True)

    # Cliente y Vendedor → Usuario → nombre_completo
    cliente_nombre = serializers.CharField(
        source='id_cliente.id_cliente.nombre_completo',
        read_only=True
    )
    vendedor_nombre = serializers.CharField(
        source='id_vendedor.id_vendedor.nombre_completo',
        read_only=True
    )

    metodo_pago_tipo = serializers.CharField(
        source='id_metodo_pago.tipo',
        read_only=True
    )

    class Meta:
        model = Venta
        fields = [
            'id_venta',
            'fecha',
            'monto_total',
            'estado',
            'id_metodo_pago',
            'metodo_pago_tipo',
            'id_cliente',
            'cliente_nombre',
            'id_vendedor',
            'vendedor_nombre',
            'detalles',
        ]


class ProcesarVentaSerializer(serializers.Serializer):
    id_metodo_pago = serializers.IntegerField(required=True)
    id_promocion = serializers.IntegerField(required=False, allow_null=True)
    cod_envio = serializers.IntegerField(required=False, allow_null=True)



#--- Ventas Presenciales Serializers ---

class ProductoVentaPresencialSerializer(serializers.Serializer):
    id_producto = serializers.IntegerField()
    cantidad = serializers.IntegerField(min_value=1)


class VentaPresencialSerializer(serializers.Serializer):
    cliente_id = serializers.IntegerField(required=False, allow_null=True)
    metodo_pago = serializers.IntegerField(required=True)

    productos = serializers.ListField(
        child=serializers.DictField(), min_length=1, required=True
    )