from django.db import transaction
from rest_framework import serializers

from core.constants.promocion import PromotionStatus, PromotionType
from core.constants import Messages

from .models import Promocion, PromocionProducto
from apps.productos.models import Producto


class ProductoPromoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Producto
        fields = ['id_producto', 'nombre', 'precio', 'estado_producto']


class PromocionSerializer(serializers.ModelSerializer):
    productos = ProductoPromoSerializer(many=True, read_only=True)

    class Meta:
        model = Promocion
        fields = [
            'id_promocion',
            'nombre',
            'descripcion',
            'codigo_descuento',
            'tipo',
            'valor_descuento',
            'fecha_inicio',
            'fecha_fin',
            'estado',
            'productos',
        ]


class PromocionCreateSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=50)
    descripcion = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    codigo_descuento = serializers.CharField(max_length=20)
    tipo = serializers.ChoiceField(choices=PromotionType.choices())
    valor_descuento = serializers.DecimalField(
        max_digits=6,
        decimal_places=2,
        required=False,
        allow_null=True,
    )
    fecha_inicio = serializers.DateField()
    fecha_fin = serializers.DateField()
    productos = serializers.ListField(
        child=serializers.CharField(),
        allow_empty=False,
    )

    def validate(self, attrs):
        inicio = attrs.get('fecha_inicio')
        fin = attrs.get('fecha_fin')
        tipo = attrs.get('tipo')
        valor = attrs.get('valor_descuento')
        productos_ids = attrs.get('productos') or []
        codigo = attrs.get('codigo_descuento')
        nombre = attrs.get('nombre')

        if fin < inicio:
            raise serializers.ValidationError({'fecha_fin': Messages.PROMO_DATE_INVALID})

        # Valor requerido si aplica
        if PromotionType.requires_value(tipo) and valor in [None, '']:
            raise serializers.ValidationError({'valor_descuento': Messages.PROMO_VALUE_REQUIRED})

        # Productos obligatorios
        if not productos_ids:
            raise serializers.ValidationError({'productos': Messages.PROMO_PRODUCTS_REQUIRED})

        # Normalizar lista (sin duplicados)
        productos_ids = list({str(pid) for pid in productos_ids})
        attrs['productos'] = productos_ids

        # Unicidad
        if Promocion.objects.filter(codigo_descuento=codigo).exists():
            raise serializers.ValidationError({'codigo_descuento': 'El código de descuento ya existe.'})
        if Promocion.objects.filter(nombre=nombre).exists():
            raise serializers.ValidationError({'nombre': 'El nombre de la promoción ya existe.'})

        # Validar productos existentes
        productos_encontrados = Producto.objects.filter(id_producto__in=productos_ids)
        faltantes = set(productos_ids) - set(prod.id_producto for prod in productos_encontrados)
        if faltantes:
            raise serializers.ValidationError({'productos': f"Productos no encontrados: {', '.join(faltantes)}"})

        # Validar solapamiento con promociones activas
        promociones_conflictivas = Promocion.objects.filter(
            estado=PromotionStatus.ACTIVA,
            fecha_inicio__lte=fin,
            fecha_fin__gte=inicio,
        ).filter(
            promociones_productos__producto_id__in=productos_ids
        ).distinct()

        if promociones_conflictivas.exists():
            raise serializers.ValidationError({'productos': Messages.PROMO_CONFLICT})

        return attrs

    def create(self, validated_data):
        productos_ids = validated_data.pop('productos', [])

        with transaction.atomic():
            promocion = Promocion.objects.create(
                estado=PromotionStatus.ACTIVA,
                **validated_data
            )
            promocion_productos = [
                PromocionProducto(
                    promocion=promocion,
                    producto_id=pid
                )
                for pid in productos_ids
            ]
            PromocionProducto.objects.bulk_create(promocion_productos)
        return promocion
