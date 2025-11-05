from rest_framework import serializers
from .models import Inventario


class InventarioSerializer(serializers.ModelSerializer):
    # campos de solo lectura para mostrar info útil
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    usuario_actualiza_nombre = serializers.CharField(
        source="usuario_actualiza.nombre_usuario",
        read_only=True
    )

    class Meta:
        model = Inventario
        fields = [
            "id_inventario",
            "producto",
            "producto_nombre",
            "cantidad_actual",
            "stock_minimo",
            "ubicacion",
            "fecha_actualizacion",
            "usuario_actualiza",
            "usuario_actualiza_nombre",
        ]
        read_only_fields = ["fecha_actualizacion"]
