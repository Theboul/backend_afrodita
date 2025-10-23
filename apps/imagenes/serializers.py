from rest_framework import serializers
from .models import ImagenProducto


class ImagenProductoSerializer(serializers.ModelSerializer):
    subido_por = serializers.SerializerMethodField()
    metadata = serializers.SerializerMethodField()

    class Meta:
        model = ImagenProducto
        fields = [
            'id_imagen', 'url', 'public_id', 'formato',
            'es_principal', 'orden', 'estado_imagen',
            'subido_por', 'fecha_subida', 'fecha_actualizacion', 'metadata'
        ]
        read_only_fields = ['id_imagen', 'url', 'public_id', 'formato']


    def get_subido_por(self, obj):
            if obj.subido_por:
                return {
                    'id': obj.subido_por.id_usuario,
                    'nombre': obj.subido_por.nombre_completo
                }
            return None

    def get_metadata(self, obj):
        return {
                'thumbnail': f"https://res.cloudinary.com/afrodita/image/upload/c_thumb,w_150,h_150/{obj.public_id}.jpg",
                'medium': f"https://res.cloudinary.com/afrodita/image/upload/c_fill,w_400,h_400/{obj.public_id}.jpg"
        }


class SubirImagenSerializer(serializers.Serializer):
    imagen = serializers.ImageField(required=True)
    es_principal = serializers.BooleanField(default=False)
    orden = serializers.IntegerField(default=1, min_value=1)

    def create(self, validated_data):
        producto = self.context['producto']
        usuario = self.context['request'].user
        archivo = validated_data['imagen']
        orden = validated_data.get('orden', 1)

        resultado = ImagenProducto.subir_a_cloudinary(
            archivo, producto.id_producto, orden
        )

        imagen = ImagenProducto.objects.create(
            id_producto=producto,
            url=resultado['url'],
            public_id=resultado['public_id'],
            formato=resultado['formato'],
            es_principal=validated_data['es_principal'],
            orden=orden,
            subido_por=usuario
        )

        if imagen.es_principal:
            imagen.marcar_como_principal()

        return imagen