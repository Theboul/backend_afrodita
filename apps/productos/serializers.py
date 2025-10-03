from rest_framework import serializers
from .models import Producto

class ProductoSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(
        source="categoria.nombre", read_only=True
    )
    # este campo te devuelve el valor real de la FK
    id_configuracion = serializers.CharField(
        source="configuracion.id_configuracion", read_only=True
    )

    class Meta:
        model = Producto
        fields = [
            "id_producto",
            "nombre",
            "precio",
            "stock",
            "descripcion",
            "estado_producto",
            "configuracion",       
            "id_configuracion",    
            "categoria",
            "categoria_nombre",
        ]
