from rest_framework import serializers
from django.db.models import Count
from .models import Categoria
from apps.productos.models import Producto


class CategoriaSerializer(serializers.ModelSerializer):
    subcategorias = serializers.SerializerMethodField()
    cantidad_productos = serializers.IntegerField(read_only=True)

    class Meta:
        model = Categoria
        fields = [
            'id_categoria',
            'nombre',
            'id_catpadre',
            'subcategorias',
            'cantidad_productos',
        ]

    def get_subcategorias(self, obj):
        """
        Usa un cache local en el contexto del serializer para evitar repetir queries.
        """
        all_categorias = self.context.get("prefetched_categorias")
        if not all_categorias:
            all_categorias = (
                Categoria.objects.filter(estado_categoria='ACTIVA')
                .select_related('id_catpadre')
                .prefetch_related('subcategorias')
                .annotate(cantidad_productos=Count('producto'))
            )
            self.context["prefetched_categorias"] = all_categorias

        hijos = [c for c in all_categorias if c.id_catpadre_id == obj.id_categoria]
        return CategoriaSerializer(hijos, many=True, context=self.context).data
