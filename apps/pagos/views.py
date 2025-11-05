from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from django.db import transaction
from django.db.models import Q
from .models import MetodoPago
from .serializers import MetodoPagoSerializer
from core.constants import APIResponse, Messages
from apps.autenticacion.utils import obtener_ip_cliente
from apps.bitacora.signals import (
    metodo_pago_creado,
    metodo_pago_actualizado,
    metodo_pago_estado_cambiado,
)


class PaymentMethodViewSet(viewsets.ModelViewSet):
    queryset = MetodoPago.objects.all()
    serializer_class = MetodoPagoSerializer
    permission_classes = [IsAdminUser]

    def get_queryset(self):
        qs = MetodoPago.objects.all()
        tipo = self.request.query_params.get('tipo')
        categoria = self.request.query_params.get('categoria')
        requiere = self.request.query_params.get('requiere_pasarela')
        activo = self.request.query_params.get('activo')
        search = self.request.query_params.get('search')
        
        if tipo:
            qs = qs.filter(tipo__icontains=tipo.strip())
        if categoria:
            qs = qs.filter(categoria=categoria.strip().upper())
        if requiere in ['true', 'false', 'True', 'False', '1', '0']:
            val = requiere.lower() in ['true', '1']
            qs = qs.filter(requiere_pasarela=val)
        if activo in ['true', 'false', 'True', 'False', '1', '0']:
            val = activo.lower() in ['true', '1']
            qs = qs.filter(activo=val)
        if search:
            s = search.strip()
            qs = qs.filter(Q(tipo__icontains=s) | Q(descripcion__icontains=s))
        return qs.order_by('tipo')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        metodo = serializer.save()

        ip = obtener_ip_cliente(request)
        metodo_pago_creado.send(sender=self.__class__, metodo=metodo, usuario=request.user, ip=ip)

        return APIResponse.created(Messages.PAYMENT_METHOD_CREATED, {"metodo": serializer.data})

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        metodo = self.get_object()
        before = {
            'tipo': metodo.tipo,
            'categoria': metodo.categoria,
            'requiere_pasarela': metodo.requiere_pasarela,
        }
        serializer = self.get_serializer(metodo, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        metodo_actualizado = serializer.save()
        
        after = {
            'tipo': metodo_actualizado.tipo,
            'categoria': metodo_actualizado.categoria,
            'requiere_pasarela': metodo_actualizado.requiere_pasarela,
        }
        cambios = [
            {"campo": k, "antes": before[k], "despues": after[k]}
            for k in before if before[k] != after[k]
        ]

        if cambios:
            ip = obtener_ip_cliente(request)
            metodo_pago_actualizado.send(
                sender=self.__class__, metodo=metodo_actualizado,
                usuario=request.user, ip=ip, cambios=cambios
            )

        return APIResponse.success(Messages.PAYMENT_METHOD_UPDATED, {"metodo": serializer.data, "cambios": cambios})

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        metodo = self.get_object()
        if not metodo.activo:
            return APIResponse.success(Messages.PAYMENT_METHOD_ALREADY_INACTIVE)
        
        anterior = metodo.activo
        metodo.activo = False
        metodo.save(update_fields=['activo'])

        ip = obtener_ip_cliente(request)
        metodo_pago_estado_cambiado.send(
            sender=self.__class__, metodo=metodo, usuario=request.user, ip=ip,
            estado_anterior=anterior, estado_nuevo=metodo.activo
        )
        return APIResponse.success(Messages.PAYMENT_METHOD_DEACTIVATED)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def activar(self, request, pk=None):
        metodo = self.get_object()
        if metodo.activo:
            return APIResponse.success(Messages.PAYMENT_METHOD_ALREADY_ACTIVE)
        
        anterior = metodo.activo
        metodo.activo = True
        metodo.save(update_fields=['activo'])

        ip = obtener_ip_cliente(request)
        metodo_pago_estado_cambiado.send(
            sender=self.__class__, metodo=metodo, usuario=request.user, ip=ip,
            estado_anterior=anterior, estado_nuevo=metodo.activo
        )
        return APIResponse.success(Messages.PAYMENT_METHOD_ACTIVATED)