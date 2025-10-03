from rest_framework import serializers
from .models import Categoria

class CategoriaSerializer(serializers.ModelSerializer):
    codigo = serializers.ReadOnlyField()
    categoria_padre_nombre = serializers.CharField(
        source="categoria_padre.nombre", read_only=True
    )

    class Meta:
        model = Categoria
        fields = [
            "id_categoria", "codigo", "nombre", 
            "categoria_padre", "categoria_padre_nombre"
        ]
