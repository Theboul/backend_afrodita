from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser

from django.db.models import Q

from core.constants import (
    APIResponse,
    Messages,
    ReviewStatus,
    ReviewPolicy,
    BitacoraActions,
)
from apps.bitacora.services.logger import AuditoriaLogger
from apps.bitacora.middleware import obtener_ip_cliente
from apps.ventas.models import DetalleVenta

from .models import Resena
from .serializers import ResenaSerializer, CrearResenaSerializer


class ResenaViewSet(viewsets.ModelViewSet):
    """
    CU26: Generar Reseñas de Producto.

    - list/retrieve: público (solo reseñas publicadas)
    - create: cliente autenticado con compra previa
    - publicar/rechazar/ocultar: administrador
    - destroy: administrador
    """

    queryset = Resena.objects.select_related('id_producto', 'id_cliente', 'id_cliente__id_cliente')

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        if self.action in ['create']:
            return [IsAuthenticated()]
        return [IsAdminUser()]

    def get_serializer_class(self):
        if self.action == 'create':
            return CrearResenaSerializer
        return ResenaSerializer

    def get_queryset(self):
        qs = super().get_queryset()

        # Filtrar por producto si viene en querystring
        producto_id = self.request.query_params.get('producto')
        if producto_id:
            qs = qs.filter(id_producto__id_producto=producto_id)

        # Público: solo publicadas; Admin puede ver todas y filtrar por estado
        user = self.request.user
        estado = self.request.query_params.get('estado')
        if user and user.is_authenticated and (
            user.is_staff or (user.id_rol and user.id_rol.nombre in ['ADMINISTRADOR', 'VENDEDOR'])
        ):
            if estado and ReviewStatus.is_valid(estado):
                qs = qs.filter(estado=estado)
            return qs

        return qs.filter(estado__in=ReviewStatus.visibles_publico())

    def create(self, request, *args, **kwargs):
        # Solo clientes
        if not request.user.id_rol or request.user.id_rol.nombre != 'CLIENTE':
            return APIResponse.forbidden(message=Messages.REVIEW_FORBIDDEN)

        cliente = getattr(request.user, 'cliente', None)
        if not cliente:
            return APIResponse.forbidden(message=Messages.REVIEW_FORBIDDEN)

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.bad_request(message=Messages.INVALID_DATA, errors=serializer.errors)

        producto = serializer.validated_data['id_producto']
        cliente_usuario = request.user

        if not self._cliente_compro_producto(cliente_usuario, producto.id_producto):
            return APIResponse.forbidden(message=Messages.REVIEW_INVALID_PURCHASE)

        estado_inicial = ReviewStatus.PUBLICADA if ReviewPolicy.AUTO_PUBLICAR else ReviewStatus.PENDIENTE
        resena = Resena.objects.create(
            id_producto=producto,
            id_cliente=cliente,  # OneToOne Cliente
            calificacion=serializer.validated_data['calificacion'],
            comentario=serializer.validated_data['comentario'],
            estado=estado_inicial
        )

        # Bitácora
        AuditoriaLogger.registrar_evento(
            accion=BitacoraActions.REVIEW_CREATED,
            descripcion=f"Resena {resena.id_resena} creada en producto {producto.id_producto}",
            ip=obtener_ip_cliente(request),
            usuario=request.user
        )

        message = Messages.REVIEW_AUTO_PUBLISHED if estado_inicial == ReviewStatus.PUBLICADA else Messages.REVIEW_CREATED_PENDING
        data = ResenaSerializer(resena).data
        return APIResponse.created(message=message, data=data)

    @action(detail=True, methods=['post'])
    def publicar(self, request, pk=None):
        resena = self.get_object()
        resena.estado = ReviewStatus.PUBLICADA
        resena.save(update_fields=['estado'])
        AuditoriaLogger.registrar_evento(
            accion=BitacoraActions.REVIEW_PUBLISHED,
            descripcion=f"Resena {resena.id_resena} publicada",
            ip=obtener_ip_cliente(request),
            usuario=request.user
        )
        return APIResponse.success(message=Messages.REVIEW_PUBLISHED, data=ResenaSerializer(resena).data)

    @action(detail=True, methods=['post'])
    def rechazar(self, request, pk=None):
        resena = self.get_object()
        resena.estado = ReviewStatus.RECHAZADA
        resena.save(update_fields=['estado'])
        AuditoriaLogger.registrar_evento(
            accion=BitacoraActions.REVIEW_REJECTED,
            descripcion=f"Resena {resena.id_resena} rechazada",
            ip=obtener_ip_cliente(request),
            usuario=request.user
        )
        return APIResponse.success(message=Messages.REVIEW_REJECTED, data=ResenaSerializer(resena).data)

    @action(detail=True, methods=['post'])
    def ocultar(self, request, pk=None):
        resena = self.get_object()
        resena.estado = ReviewStatus.OCULTA
        resena.save(update_fields=['estado'])
        AuditoriaLogger.registrar_evento(
            accion=BitacoraActions.REVIEW_HIDDEN,
            descripcion=f"Resena {resena.id_resena} ocultada",
            ip=obtener_ip_cliente(request),
            usuario=request.user
        )
        return APIResponse.success(message=Messages.REVIEW_HIDDEN, data=ResenaSerializer(resena).data)

    def destroy(self, request, *args, **kwargs):
        resena = self.get_object()
        resena.delete()
        AuditoriaLogger.registrar_evento(
            accion=BitacoraActions.REVIEW_DELETED,
            descripcion=f"Resena {resena.id_resena} eliminada",
            ip=obtener_ip_cliente(request),
            usuario=request.user
        )
        return APIResponse.success(message=Messages.REVIEW_DELETED)

    @staticmethod
    def _cliente_compro_producto(usuario, producto_id):
        """Verifica si el cliente compró el producto."""
        try:
            return DetalleVenta.objects.filter(
                id_producto_id=producto_id,
                id_venta__id_cliente__id_cliente_id=usuario.id_usuario
            ).exists()
        except Exception:
            return False
