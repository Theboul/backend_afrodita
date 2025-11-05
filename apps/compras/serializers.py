from decimal import Decimal
from typing import List

from django.db import connection, transaction
from django.utils import timezone
from rest_framework import serializers

from .models import DevolucionCompra, DetalleDevolucionCompra, Compra, DetalleCompra
from apps.productos.models import Producto
from core.constants import APIResponse, Messages


class DetalleDevolucionCompraSerializer(serializers.ModelSerializer):
    id_producto = serializers.CharField(source='id_producto_id', read_only=True)

    class Meta:
        model = DetalleDevolucionCompra
        fields = ['id_detalle', 'id_producto', 'cantidad', 'precio_unit', 'sub_total', 'observacion']


class DevolucionCompraListSerializer(serializers.ModelSerializer):
    id_compra = serializers.IntegerField(source='id_compra_id', read_only=True)

    class Meta:
        model = DevolucionCompra
        fields = [
            'id_devolucion_compra', 'id_compra', 'fecha_devolucion',
            'motivo_general', 'monto_total', 'estado_devolucion'
        ]


class DevolucionCompraDetalleSerializer(serializers.ModelSerializer):
    id_compra = serializers.IntegerField(source='id_compra_id', read_only=True)
    items = DetalleDevolucionCompraSerializer(many=True, read_only=True)

    class Meta:
        model = DevolucionCompra
        fields = [
            'id_devolucion_compra', 'id_compra', 'fecha_devolucion',
            'motivo_general', 'monto_total', 'estado_devolucion', 'items'
        ]


class ItemCrearDevolucionSerializer(serializers.Serializer):
    id_producto = serializers.CharField(max_length=5)
    cantidad = serializers.IntegerField(min_value=1)
    precio_unit = serializers.DecimalField(max_digits=10, decimal_places=2, required=False)
    observacion = serializers.CharField(required=False, allow_blank=True)

    def validate_id_producto(self, value):
        if not Producto.objects.filter(id_producto=value).exists():
            raise serializers.ValidationError('Producto no existe.')
        return value


class CrearDevolucionCompraSerializer(serializers.Serializer):
    id_compra = serializers.IntegerField()
    motivo_general = serializers.CharField(required=False, allow_blank=True)
    items = ItemCrearDevolucionSerializer(many=True)

    def _obtener_cantidad_ordenada(self, id_compra: int, id_producto: str) -> int:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(cantidad),0)
                FROM detalle_compra
                WHERE id_compra = %s AND id_producto = %s
                """,
                [id_compra, id_producto]
            )
            row = cur.fetchone()
            return int(row[0] or 0)

    def _obtener_cantidad_devuelta(self, id_compra: int, id_producto: str) -> int:
        with connection.cursor() as cur:
            cur.execute(
                """
                SELECT COALESCE(SUM(ddc.cantidad),0)
                FROM detalle_devolucion_compra ddc
                JOIN devolucion_compra dc ON dc.id_devolucion_compra = ddc.id_devolucion_compra
                WHERE dc.id_compra = %s AND ddc.id_producto = %s
                """,
                [id_compra, id_producto]
            )
            row = cur.fetchone()
            return int(row[0] or 0)

    def validate(self, attrs):
        id_compra = attrs.get('id_compra')
        items = attrs.get('items') or []

        try:
            compra = Compra.objects.get(id_compra=id_compra)
        except Compra.DoesNotExist:
            raise serializers.ValidationError({'id_compra': 'Compra no existe.'})

        # Validar cantidades vs ordenado - devuelto (si existen registros de detalle_compra)
        errores = {}
        for i, it in enumerate(items):
            prod = it['id_producto']
            cant = it['cantidad']
            ordenado = self._obtener_cantidad_ordenada(id_compra, prod)
            if ordenado > 0:
                devuelto = self._obtener_cantidad_devuelta(id_compra, prod)
                restante = max(ordenado - devuelto, 0)
                if cant > restante:
                    errores[f'items[{i}].cantidad'] = f'Cantidad supera lo pendiente para {prod}. Pendiente: {restante}'
        if errores:
            raise serializers.ValidationError(errores)

        attrs['compra'] = compra
        return attrs

    def create(self, validated_data):
        request = self.context.get('request')
        usuario = getattr(request, 'user', None) if request else None

        compra: Compra = validated_data['compra']
        motivo = validated_data.get('motivo_general')
        items_data: List[dict] = validated_data['items']

        with transaction.atomic():
            # settings.USE_TZ está en False; evitar timezone.localdate() que usa localtime()
            # y falla con datetimes ingenuas. Usar fecha local simple.
            dev = DevolucionCompra.objects.create(
                id_compra=compra,
                fecha_devolucion=timezone.now().date(),
                motivo_general=motivo,
                estado_devolucion='PENDIENTE',
                procesado_por=usuario
            )

            total = Decimal('0.00')
            detalles = []
            for it in items_data:
                precio = it.get('precio_unit')
                sub_total = None
                if precio is not None:
                    sub_total = (Decimal(precio) * Decimal(it['cantidad'])).quantize(Decimal('0.01'))
                    total += sub_total

                det = DetalleDevolucionCompra.objects.create(
                    id_devolucion_compra=dev,
                    id_producto_id=it['id_producto'],
                    cantidad=it['cantidad'],
                    precio_unit=precio,
                    sub_total=sub_total,
                    observacion=it.get('observacion')
                )
                detalles.append(det)

            # Actualizar total (si todos los precios fueron omitidos, quedará 0)
            dev.monto_total = total
            dev.save(update_fields=['monto_total'])

        return dev


# ==========================================================
# ORDENES DE COMPRA (EMITIR / RECEPCIONAR)
# ==========================================================

class ItemCrearOrdenSerializer(serializers.Serializer):
    id_producto = serializers.CharField(max_length=5)
    cantidad = serializers.IntegerField(min_value=1)
    precio = serializers.DecimalField(max_digits=10, decimal_places=2, min_value=0.01)

    def validate_id_producto(self, value):
        if not Producto.objects.filter(id_producto=value).exists():
            raise serializers.ValidationError('Producto no existe.')
        return value


class CrearOrdenCompraSerializer(serializers.Serializer):
    cod_proveedor = serializers.CharField(max_length=6)
    fecha = serializers.DateField(required=False)
    items = ItemCrearOrdenSerializer(many=True)

    def validate_cod_proveedor(self, value):
        from apps.proveedores.models import Proveedor
        if not Proveedor.objects.filter(cod_proveedor=value).exists():
            raise serializers.ValidationError('Proveedor no existe.')
        return value

    def validate(self, attrs):
        if not attrs.get('items'):
            raise serializers.ValidationError({'items': 'Debe especificar al menos un item.'})
        return attrs

    def create(self, validated_data):
        from apps.proveedores.models import Proveedor
        fecha = validated_data.get('fecha') or timezone.now().date()
        cod_prov = validated_data['cod_proveedor']
        items = validated_data['items']

        proveedor = Proveedor.objects.get(cod_proveedor=cod_prov)

        with transaction.atomic():
            compra = Compra.objects.create(
                fecha=fecha,
                monto_total=Decimal('0.00'),
                estado_compra='PENDIENTE',
                cod_proveedor=proveedor
            )

            total = Decimal('0.00')
            with connection.cursor() as cur:
                for it in items:
                    sub_total = (Decimal(it['precio']) * it['cantidad']).quantize(Decimal('0.01'))
                    total += sub_total
                    cur.execute(
                        """
                        INSERT INTO detalle_compra (id_compra, id_producto, cantidad, precio, sub_total)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        [compra.id_compra, it['id_producto'], it['cantidad'], str(it['precio']), str(sub_total)]
                    )

            compra.monto_total = total
            compra.save(update_fields=['monto_total'])

        return compra


class ItemRecepcionSerializer(serializers.Serializer):
    id_producto = serializers.CharField(max_length=5)
    cantidad = serializers.IntegerField(min_value=1)

    def validate_id_producto(self, value):
        if not Producto.objects.filter(id_producto=value).exists():
            raise serializers.ValidationError('Producto no existe.')
        return value


class RegistrarRecepcionSerializer(serializers.Serializer):
    items = ItemRecepcionSerializer(many=True, required=False)
    notas = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        # Validar que no exceda lo ordenado
        view = self.context.get('view')
        compra: Compra = getattr(view, 'compra_obj', None)
        if not compra:
            return attrs

        # Mapear cantidades ordenadas por producto
        ordenado = {}
        for row in DetalleCompra.objects.filter(id_compra=compra).values('id_producto_id', 'cantidad'):
            prod = row['id_producto_id']
            ordenado[prod] = ordenado.get(prod, 0) + int(row['cantidad'])

        items = attrs.get('items')
        if not items:
            # Si no envían items, se recibirán todos los ordenados
            return attrs

        errores = {}
        for i, it in enumerate(items):
            prod = it['id_producto']
            cant = it['cantidad']
            pendiente = ordenado.get(prod, 0)
            if pendiente == 0:
                errores[f'items[{i}].id_producto'] = 'Producto no está en la orden.'
            elif cant > pendiente:
                errores[f'items[{i}].cantidad'] = f'No puede exceder lo ordenado ({pendiente}).'
        if errores:
            raise serializers.ValidationError(errores)

        return attrs


# ==========================================================
# LECTURA DE ÓRDENES (para API navegable y respuestas)
# ==========================================================

class DetalleCompraReadSerializer(serializers.ModelSerializer):
    id_producto = serializers.CharField(source='id_producto_id', read_only=True)

    class Meta:
        model = DetalleCompra
        fields = ['id_producto', 'cantidad', 'precio', 'sub_total']


class OrdenCompraReadSerializer(serializers.ModelSerializer):
    cod_proveedor = serializers.CharField(source='cod_proveedor_id', read_only=True)
    items = DetalleCompraReadSerializer(many=True, read_only=True)

    class Meta:
        model = Compra
        fields = ['id_compra', 'fecha', 'monto_total', 'estado_compra', 'cod_proveedor', 'items']
