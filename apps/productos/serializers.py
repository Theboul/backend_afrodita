from rest_framework import serializers
from .models import Producto, ConfiguracionLente, Medida
from apps.categoria.models import Categoria
from apps.imagenes.models import ImagenProducto
from apps.imagenes.serializers import ImagenProductoSerializer
from rest_framework.pagination import PageNumberPagination

class ProductoPagination(PageNumberPagination):
    page_size = 9           # Cantidad de productos por página
    page_size_query_param = 'page_size'  # Permite cambiar por query param
    max_page_size = 50      # Límite máximo

# ==========================================================
# SERIALIZERS AUXILIARES
# ==========================================================

class MedidaSerializer(serializers.ModelSerializer):
    """Serializer simple para medidas"""
    class Meta:
        model = Medida
        fields = ['id_medida', 'medida', 'descripcion']


class ConfiguracionLenteSerializer(serializers.ModelSerializer):
    """Serializer completo para configuración de lentes"""
    medida_info = MedidaSerializer(source='id_medida', read_only=True)
    
    class Meta:
        model = ConfiguracionLente
        fields = [
            'id_configuracion', 'color', 'curva', 'diametro', 
            'duracion_meses', 'material', 'id_medida', 'medida_info'
        ]


class CategoriaSimpleSerializer(serializers.ModelSerializer):
    """Serializer ligero de categoría para productos"""
    id = serializers.IntegerField(source='id_categoria', read_only=True)
    padre = serializers.SerializerMethodField()
    
    class Meta:
        model = Categoria
        fields = ['id', 'nombre', 'padre', 'estado_categoria']
    
    def get_padre(self, obj):
        if obj.id_catpadre:
            return obj.id_catpadre.nombre
        return None

# ==========================================================
# SERIALIZERS DE PRODUCTO
# ==========================================================
class ProductoConImagenSerializer(serializers.ModelSerializer):
    categoria_nombre = serializers.CharField(source="id_categoria.nombre", read_only=True)
    configuracion = ConfiguracionLenteSerializer(source="id_configuracion", read_only=True)
    id_configuracion = serializers.CharField(source="id_configuracion.id_configuracion", read_only=True)
    imagen_principal = serializers.SerializerMethodField()
    pagination_class = ProductoPagination

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
            "id_categoria",
            "categoria_nombre",
            "imagen_principal",
        ]

    def get_imagen_principal(self, obj):
        imagen = ImagenProducto.objects.filter(
            id_producto=obj, es_principal=True, estado_imagen="ACTIVA"
        ).first()
        if imagen:
            return ImagenProductoSerializer(imagen).data
        return None

class ProductoListSerializer(serializers.ModelSerializer):
    """Serializer ligero para listado de productos"""
    categoria = CategoriaSimpleSerializer(source='id_categoria', read_only=True)
    configuracion = ConfiguracionLenteSerializer(source='id_configuracion', read_only=True)
    imagen_principal = serializers.SerializerMethodField()
    imagenes = ImagenProductoSerializer(many=True, read_only=True)
    tiene_stock = serializers.BooleanField(read_only=True)
    stock_bajo = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Producto
        fields = [
            'id_producto', 'nombre', 'descripcion', 'precio', 'stock',
            'estado_producto', 'categoria', 'configuracion', 
            'imagen_principal', 'imagenes', 'fecha_creacion', 'tiene_stock', 'stock_bajo'
        ]
    
    def get_imagen_principal(self, obj):
        imagen = obj.imagenes.filter(es_principal=True).first()
        if imagen:
            return {
                'id': imagen.id_imagen,
                'url': imagen.url,
                'public_id': imagen.public_id
            }
        return None

    def get_imagen_principal(self, obj):
        """Obtiene la imagen principal del producto"""
        imagen = obj.imagenes.filter(es_principal=True).first()
        if imagen:
            return {
                'id': imagen.id_imagen,
                'url': imagen.url,
                'public_id': imagen.public_id
            }
        return None


class ProductoDetalleSerializer(serializers.ModelSerializer):
    """Serializer completo con todas las relaciones"""
    categoria = CategoriaSimpleSerializer(source='id_categoria', read_only=True)
    configuracion = ConfiguracionLenteSerializer(source='id_configuracion', read_only=True)
    imagenes = ImagenProductoSerializer(many=True, read_only=True)
    tiene_stock = serializers.BooleanField(read_only=True)
    stock_bajo = serializers.BooleanField(read_only=True)
    esta_activo = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = Producto
        fields = [
            'id_producto', 'nombre', 'descripcion', 'precio', 'stock',
            'estado_producto', 'categoria', 'configuracion', 'imagenes',
            'fecha_creacion', 'ultima_actualizacion', 
            'tiene_stock', 'stock_bajo', 'esta_activo'
        ]


class CrearProductoSerializer(serializers.ModelSerializer):
    """Serializer para crear productos"""
    
    class Meta:
        model = Producto
        fields = [
            'id_producto', 'nombre', 'descripcion', 'precio', 
            'stock', 'id_categoria', 'id_configuracion'
        ]
    
    def validate_id_producto(self, value):
        """Valida que el ID sea único"""
        if Producto.objects.filter(id_producto=value).exists():
            raise serializers.ValidationError("Ya existe un producto con este ID")
        return value.upper()  # Convertir a mayúsculas
    
    def validate_precio(self, value):
        """Valida que el precio sea positivo"""
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0")
        return value
    
    def validate_stock(self, value):
        """Valida que el stock no sea negativo"""
        if value < 0:
            raise serializers.ValidationError("El stock no puede ser negativo")
        return value
    
    def validate(self, attrs):
        """Validaciones cruzadas"""
        # Validar que la categoría existe
        categoria = attrs.get('id_categoria')
        if not categoria:
            raise serializers.ValidationError({
                'id_categoria': 'La categoría es requerida'
            })
        
        # Validar que si tiene configuración, esta exista
        configuracion = attrs.get('id_configuracion')
        if configuracion and not ConfiguracionLente.objects.filter(
            id_configuracion=configuracion.id_configuracion
        ).exists():
            raise serializers.ValidationError({
                'id_configuracion': 'La configuración seleccionada no existe'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Crea el producto"""
        producto = Producto.objects.create(**validated_data)
        return producto


class ActualizarProductoSerializer(serializers.ModelSerializer):
    """Serializer para actualizar productos"""
    
    class Meta:
        model = Producto
        fields = [
            'nombre', 'descripcion', 'precio', 
            'stock', 'id_categoria', 'id_configuracion'
        ]
    
    def validate_precio(self, value):
        if value <= 0:
            raise serializers.ValidationError("El precio debe ser mayor a 0")
        return value
    
    def validate_stock(self, value):
        if value < 0:
            raise serializers.ValidationError("El stock no puede ser negativo")
        return value
    
    def update(self, instance, validated_data):
        """Actualiza el producto y guarda el diff de cambios"""
        # Guardar valores anteriores para auditoría
        cambios = {}
        for field, new_value in validated_data.items():
            old_value = getattr(instance, field)
            
            # Manejar ForeignKeys
            if hasattr(old_value, 'pk'):
                old_value = str(old_value)
            if hasattr(new_value, 'pk'):
                new_value = str(new_value)
            
            if old_value != new_value:
                cambios[field] = {
                    'anterior': old_value,
                    'nuevo': new_value
                }
        
        # Actualizar
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Guardar cambios en el contexto para el response
        self.context['cambios'] = cambios
        
        return instance


class CambiarEstadoSerializer(serializers.Serializer):
    """Serializer para cambiar estado del producto"""
    estado_producto = serializers.ChoiceField(
        choices=['ACTIVO', 'INACTIVO'],
        required=True
    )
    motivo = serializers.CharField(
        max_length=200,
        required=False,
        allow_blank=True
    )
    
    def validate_estado_producto(self, value):
        """Valida que el estado sea válido"""
        if value not in ['ACTIVO', 'INACTIVO']:
            raise serializers.ValidationError(
                "Estado inválido. Use ACTIVO o INACTIVO"
            )
        return value


class AjustarStockSerializer(serializers.Serializer):
    """Serializer para ajustar stock del producto"""
    TIPOS_AJUSTE = ['INCREMENTO', 'DECREMENTO', 'CORRECCION']
    
    tipo_ajuste = serializers.ChoiceField(
        choices=TIPOS_AJUSTE,
        required=True
    )
    cantidad = serializers.IntegerField(
        required=True,
        min_value=0
    )
    motivo = serializers.CharField(
        max_length=200,
        required=True
    )
    
    def validate_tipo_ajuste(self, value):
        if value not in self.TIPOS_AJUSTE:
            raise serializers.ValidationError(
                f"Tipo de ajuste inválido. Use: {', '.join(self.TIPOS_AJUSTE)}"
            )
        return value
    
    def validate(self, attrs):
        """Validaciones cruzadas"""
        tipo = attrs.get('tipo_ajuste')
        cantidad = attrs.get('cantidad')
        
        # Si es decremento, validar en el método de ajuste
        # (necesitamos el stock actual que está en la instancia)
        
        if cantidad < 0:
            raise serializers.ValidationError({
                'cantidad': 'La cantidad no puede ser negativa'
            })
        
        return attrs