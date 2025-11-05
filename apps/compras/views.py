from django.http import JsonResponse
from django.db import transaction
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from django_filters.rest_framework import DjangoFilterBackend

from .models import DevolucionCompra, Compra, DetalleCompra
from .serializers import (
    DevolucionCompraListSerializer,
    DevolucionCompraDetalleSerializer,
    CrearDevolucionCompraSerializer,
    CrearOrdenCompraSerializer,
    RegistrarRecepcionSerializer,
)
from core.constants import APIResponse, Messages, ProductConfig
from apps.bitacora.services.logger import AuditoriaLogger
from apps.bitacora.signals import producto_stock_ajustado
from apps.autenticacion.utils.helpers import obtener_ip_cliente
from apps.productos.models import Producto


def index(request):
    return JsonResponse({"message": "API de compras funcionando"})


class DevolucionCompraViewSet(viewsets.ModelViewSet):
    queryset = DevolucionCompra.objects.select_related('id_compra', 'procesado_por').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado_devolucion', 'id_compra__id_compra']
    search_fields = ['id_devolucion_compra', 'id_compra__id_compra']
    ordering_fields = ['id_devolucion_compra', 'fecha_devolucion', 'monto_total']
    ordering = ['-id_devolucion_compra']

    def get_permissions(self):
        return [IsAuthenticated(), IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'list':
            return DevolucionCompraListSerializer
        elif self.action == 'create':
            return CrearDevolucionCompraSerializer
        return DevolucionCompraDetalleSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        devolucion = serializer.save()

        data = DevolucionCompraDetalleSerializer(devolucion).data
        return APIResponse.created(
            message='Devolución registrada correctamente.',
            data={'devolucion': data}
        )

    @action(detail=True, methods=['post'], url_path='anular')
    def anular(self, request, pk=None):
        dev = self.get_object()
        if dev.estado_devolucion == 'ANULADA':
            return APIResponse.success(
                message='Devolución ya estaba anulada.',
                data={'devolucion': {'id_devolucion_compra': dev.id_devolucion_compra, 'estado': dev.estado_devolucion}}
            )
        dev.estado_devolucion = 'ANULADA'
        dev.save(update_fields=['estado_devolucion'])
        return APIResponse.success(
            message='Devolución anulada.',
            data={'devolucion': {'id_devolucion_compra': dev.id_devolucion_compra, 'estado': dev.estado_devolucion}}
        )


class OrdenCompraViewSet(viewsets.ModelViewSet):
    queryset = Compra.objects.select_related('cod_proveedor').all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado_compra', 'cod_proveedor__cod_proveedor']
    search_fields = ['id_compra', 'cod_proveedor__cod_proveedor']
    ordering_fields = ['id_compra', 'fecha', 'monto_total']
    ordering = ['-id_compra']

    def get_permissions(self):
        return [IsAuthenticated(), IsAdminUser()]

    def get_serializer_class(self):
        from .serializers import OrdenCompraReadSerializer
        if self.action == 'create':
            return CrearOrdenCompraSerializer
        if self.action == 'registrar_recepcion':
            # Necesario para que la API navegable pueda construir el formulario
            # en la vista GET de la acción personalizada.
            return RegistrarRecepcionSerializer
        if self.action in ['list', 'retrieve']:
            # Proveer serializer para API browsable aunque usemos respuesta custom
            return OrdenCompraReadSerializer
        # Fallback seguro
        return OrdenCompraReadSerializer

    def list(self, request, *args, **kwargs):
        qs = self.filter_queryset(self.get_queryset())
        data = [
            {
                'id_compra': c.id_compra,
                'fecha': c.fecha,
                'monto_total': c.monto_total,
                'estado_compra': c.estado_compra,
                'cod_proveedor': c.cod_proveedor_id,
                'items': list(
                    DetalleCompra.objects.filter(id_compra=c).values(
                        'id_producto_id', 'cantidad', 'precio', 'sub_total'
                    )
                )
            }
            for c in qs
        ]
        return APIResponse.success(message='Listado de órdenes', data={'resultados': data})

    def retrieve(self, request, pk=None):
        c = self.get_object()
        data = {
            'id_compra': c.id_compra,
            'fecha': c.fecha,
            'monto_total': c.monto_total,
            'estado_compra': c.estado_compra,
            'cod_proveedor': c.cod_proveedor_id,
            'items': list(
                DetalleCompra.objects.filter(id_compra=c).values(
                    'id_producto_id', 'cantidad', 'precio', 'sub_total'
                )
            )
        }
        return APIResponse.success(message='Detalle de orden', data={'orden': data})

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        compra = serializer.save()

        # Bitácora
        ip = obtener_ip_cliente(request)
        AuditoriaLogger.registrar_evento(
            accion='PURCHASE_ORDER_CREATE',
            descripcion=f"Orden de compra #{compra.id_compra} para proveedor {compra.cod_proveedor_id}",
            ip=ip,
            usuario=request.user
        )

        # Respuesta
        data = {
            'id_compra': compra.id_compra,
            'fecha': compra.fecha,
            'monto_total': compra.monto_total,
            'estado_compra': compra.estado_compra,
            'cod_proveedor': compra.cod_proveedor_id,
            'items': list(
                DetalleCompra.objects.filter(id_compra=compra).values(
                    'id_producto_id', 'cantidad', 'precio', 'sub_total'
                )
            )
        }
        return APIResponse.created(message='Orden de compra creada.', data={'orden': data})

    @action(detail=True, methods=['post'], url_path='registrar-recepcion')
    def registrar_recepcion(self, request, pk=None):
        compra = self.get_object()
        if compra.estado_compra == 'FINALIZADA':
            return APIResponse.error('La compra ya está finalizada.', status_code=409)

        # Guardar compra en el contexto del serializer para validación
        self.compra_obj = compra
        serializer = RegistrarRecepcionSerializer(data=request.data or {}, context={'view': self})
        serializer.is_valid(raise_exception=True)

        items_req = serializer.validated_data.get('items')

        # Mapear cantidades a recibir
        if items_req:
            recibir = {it['id_producto']: it['cantidad'] for it in items_req}
        else:
            # Recibir todo lo ordenado
            recibir = {}
            for row in DetalleCompra.objects.filter(id_compra=compra).values('id_producto_id', 'cantidad'):
                prod = row['id_producto_id']
                recibir[prod] = recibir.get(prod, 0) + int(row['cantidad'])

        # Transacción: ajustar stock y cerrar orden
        ip = obtener_ip_cliente(request)
        with transaction.atomic():
            for id_prod, cant in recibir.items():
                try:
                    prod = Producto.objects.select_for_update().get(id_producto=id_prod)
                except Producto.DoesNotExist:
                    return APIResponse.not_found(message=f'Producto {id_prod} no existe.')
                stock_anterior = prod.stock
                prod.stock = stock_anterior + cant
                prod.save(update_fields=['stock'])

                # Señal de bitácora existente para consistencia
                producto_stock_ajustado.send(
                    sender=self.__class__,
                    producto=prod,
                    usuario=request.user,
                    ip=ip,
                    tipo_ajuste=ProductConfig.STOCK_INCREMENT,
                    cantidad=cant,
                    stock_anterior=stock_anterior,
                    stock_nuevo=prod.stock,
                    motivo=f'Recepción de compra #{compra.id_compra}'
                )

            compra.estado_compra = 'FINALIZADA'
            compra.save(update_fields=['estado_compra'])

            AuditoriaLogger.registrar_evento(
                accion='PURCHASE_RECEIPT',
                descripcion=f"Recepción registrada para compra #{compra.id_compra}",
                ip=ip,
                usuario=request.user
            )

        return APIResponse.success(
            message='Recepción registrada y compra finalizada.',
            data={'id_compra': compra.id_compra, 'estado_compra': compra.estado_compra, 'items_recibidos': recibir}
        )
