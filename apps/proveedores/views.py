from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, IsAdminUser

from django_filters.rest_framework import DjangoFilterBackend

from .models import Proveedor
from .serializers import (
    ProveedorListSerializer,
    ProveedorDetalleSerializer,
    CrearProveedorSerializer,
    ActualizarProveedorSerializer,
)
from core.constants import APIResponse, Messages, BitacoraActions
from apps.bitacora.signals import (
    proveedor_creado,
    proveedor_actualizado,
    proveedor_bloqueado,
    proveedor_activado,
)
from apps.autenticacion.utils.helpers import obtener_ip_cliente


class ProveedorViewSet(viewsets.ModelViewSet):
    queryset = Proveedor.objects.all()
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['estado_proveedor', 'pais']
    search_fields = ['cod_proveedor', 'nombre', 'contacto', 'telefono', 'direccion', 'pais']
    ordering_fields = ['nombre', 'cod_proveedor', 'pais']
    ordering = ['nombre']

    def get_permissions(self):
        # Solo administradores autenticados pueden gestionar proveedores
        return [IsAuthenticated(), IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'list':
            return ProveedorListSerializer
        elif self.action == 'create':
            return CrearProveedorSerializer
        elif self.action in ['update', 'partial_update']:
            return ActualizarProveedorSerializer
        return ProveedorDetalleSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        proveedor = serializer.save()

        # Señal de bitácora
        proveedor_creado.send(
            sender=self.__class__,
            proveedor=proveedor,
            usuario=request.user,
            ip=obtener_ip_cliente(request)
        )

        detail = ProveedorDetalleSerializer(proveedor).data
        return APIResponse.created(
            message=Messages.OPERATION_SUCCESS,
            data={'proveedor': detail}
        )

    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        proveedor = serializer.save()

        cambios = serializer.context.get('cambios', {})

        proveedor_actualizado.send(
            sender=self.__class__,
            proveedor=proveedor,
            usuario=request.user,
            ip=obtener_ip_cliente(request),
            cambios=cambios
        )

        detail = ProveedorDetalleSerializer(proveedor).data
        if cambios:
            detail['cambios_realizados'] = cambios
        return APIResponse.success(
            message=Messages.OPERATION_SUCCESS,
            data={'proveedor': detail}
        )

    def partial_update(self, request, *args, **kwargs):
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)

    @action(detail=True, methods=['post'], url_path='bloquear')
    def bloquear(self, request, pk=None):
        proveedor = self.get_object()
        if proveedor.estado_proveedor == 'BLOQUEADO':
            return APIResponse.success(
                message=Messages.OPERATION_SUCCESS,
                data={'proveedor': {'cod_proveedor': proveedor.cod_proveedor, 'estado_proveedor': proveedor.estado_proveedor}}
            )

        estado_anterior = proveedor.estado_proveedor
        proveedor.estado_proveedor = 'BLOQUEADO'
        proveedor.save(update_fields=['estado_proveedor'])

        proveedor_bloqueado.send(
            sender=self.__class__,
            proveedor=proveedor,
            usuario=request.user,
            ip=obtener_ip_cliente(request),
            estado_anterior=estado_anterior,
            estado_nuevo=proveedor.estado_proveedor,
        )

        return APIResponse.success(
            message=Messages.OPERATION_SUCCESS,
            data={
                'proveedor': {
                    'cod_proveedor': proveedor.cod_proveedor,
                    'estado_proveedor': proveedor.estado_proveedor,
                    'estado_anterior': estado_anterior,
                }
            }
        )

    @action(detail=True, methods=['post'], url_path='activar')
    def activar(self, request, pk=None):
        proveedor = self.get_object()
        if proveedor.estado_proveedor == 'ACTIVO':
            return APIResponse.success(
                message=Messages.OPERATION_SUCCESS,
                data={'proveedor': {'cod_proveedor': proveedor.cod_proveedor, 'estado_proveedor': proveedor.estado_proveedor}}
            )

        estado_anterior = proveedor.estado_proveedor
        proveedor.estado_proveedor = 'ACTIVO'
        proveedor.save(update_fields=['estado_proveedor'])

        proveedor_activado.send(
            sender=self.__class__,
            proveedor=proveedor,
            usuario=request.user,
            ip=obtener_ip_cliente(request),
            estado_anterior=estado_anterior,
            estado_nuevo=proveedor.estado_proveedor,
        )

        return APIResponse.success(
            message=Messages.OPERATION_SUCCESS,
            data={
                'proveedor': {
                    'cod_proveedor': proveedor.cod_proveedor,
                    'estado_proveedor': proveedor.estado_proveedor,
                    'estado_anterior': estado_anterior,
                }
            }
        )

