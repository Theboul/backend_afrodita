# apps/catalogo/serializers.py
from rest_framework import serializers
from apps.productos.models import Producto, ConfiguracionLente, Medida
from apps.categoria.models import Categoria
from apps.imagenes.models import ImagenProducto


class MedidaCatalogoSerializer(serializers.ModelSerializer):
    """Serializer simple para medidas en el catálogo"""
    
    class Meta:
        model = Medida
        fields = ['id_medida', 'medida', 'descripcion']


class CategoriaCatalogoSerializer(serializers.ModelSerializer):
    """Serializer de categoría para catálogo público"""
    
    class Meta:
        model = Categoria
        fields = ['id_categoria', 'nombre']


class ConfiguracionCatalogoSerializer(serializers.ModelSerializer):
    """Serializer de configuración para catálogo"""
    medida = MedidaCatalogoSerializer(source='id_medida', read_only=True)
    
    class Meta:
        model = ConfiguracionLente
        fields = [
            'id_configuracion',
            'color',
            'curva',
            'diametro',
            'duracion_meses',
            'material',
            'medida'
        ]


class ImagenCatalogoSerializer(serializers.ModelSerializer):
    """Serializer para imágenes en catálogo"""
    
    class Meta:
        model = ImagenProducto
        fields = ['id_imagen', 'url', 'public_id', 'es_principal']


class ProductoCatalogoListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listado de productos en catálogo"""
    categoria = CategoriaCatalogoSerializer(source='id_categoria', read_only=True)
    imagen_principal = serializers.SerializerMethodField()
    color = serializers.CharField(source='id_configuracion.color', read_only=True)
    tiene_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Producto
        fields = [
            'id_producto',
            'nombre',
            'descripcion',
            'precio',
            'stock',
            'categoria',
            'color',
            'imagen_principal',
            'tiene_stock'
        ]
    
    def get_imagen_principal(self, obj):
        """Obtiene la imagen principal del producto"""
        imagen = obj.imagenes.filter(es_principal=True).first()
        if imagen:
            return {
                'url': imagen.url,
                'public_id': imagen.public_id
            }
        return None


class ProductoCatalogoDetalleSerializer(serializers.ModelSerializer):
    """Serializer completo para detalle de producto en catálogo"""
    categoria = CategoriaCatalogoSerializer(source='id_categoria', read_only=True)
    configuracion = ConfiguracionCatalogoSerializer(source='id_configuracion', read_only=True)
    imagenes = ImagenCatalogoSerializer(many=True, read_only=True)
    tiene_stock = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Producto
        fields = [
            'id_producto',
            'nombre',
            'descripcion',
            'precio',
            'stock',
            'categoria',
            'configuracion',
            'imagenes',
            'fecha_creacion',
            'tiene_stock'
        ]


class ColorDisponibleSerializer(serializers.Serializer):
    """Serializer para colores disponibles"""
    color = serializers.CharField()
    productos_disponibles = serializers.IntegerField()


class MedidaDisponibleSerializer(serializers.Serializer):
    """Serializer para medidas disponibles con conteo"""
    id_medida = serializers.IntegerField()
    medida = serializers.CharField()
    descripcion = serializers.CharField(allow_null=True)
    productos_disponibles = serializers.IntegerField()