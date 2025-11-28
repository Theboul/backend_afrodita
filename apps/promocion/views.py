from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser

from core.constants import APIResponse, Messages
from core.constants.promocion import PromotionStatus
from .models import Promocion
from .serializers import PromocionSerializer, PromocionCreateSerializer


class PromocionViewSet(viewsets.ModelViewSet):
    """
    Controlador para gestionar promociones (CU23).
    """

    queryset = Promocion.objects.prefetch_related('productos').all()
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action in ['create']:
            return PromocionCreateSerializer
        return PromocionSerializer

    def list(self, request, *args, **kwargs):
        serializer = self.get_serializer(self.get_queryset(), many=True)
        return APIResponse.success(message=Messages.OPERATION_SUCCESS, data=serializer.data)

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return APIResponse.success(message=Messages.OPERATION_SUCCESS, data=serializer.data)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        promocion = serializer.save()
        response_data = PromocionSerializer(promocion).data
        return APIResponse.created(message=Messages.PROMO_CREATED, data=response_data)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def desactivar(self, request, pk=None):
        promocion = self.get_object()
        if promocion.estado == PromotionStatus.INACTIVA:
            return APIResponse.success(message=Messages.PROMO_ALREADY_INACTIVE)
        promocion.estado = PromotionStatus.INACTIVA
        promocion.save(update_fields=['estado'])
        return APIResponse.success(message=Messages.PROMO_DEACTIVATED)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def activar(self, request, pk=None):
        promocion = self.get_object()
        if promocion.estado == PromotionStatus.ACTIVA:
            return APIResponse.success(message=Messages.PROMO_ALREADY_ACTIVE)
        promocion.estado = PromotionStatus.ACTIVA
        promocion.save(update_fields=['estado'])
        return APIResponse.success(message=Messages.PROMO_ACTIVATED)
