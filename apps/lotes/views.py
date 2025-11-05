from rest_framework import viewsets, permissions, decorators, response, status
from django.utils import timezone
from django.db.models import Q
from .models import Lote
from .serializers import LoteSerializer

class LoteViewSet(viewsets.ModelViewSet):
    queryset = Lote.objects.select_related('producto').all()
    serializer_class = LoteSerializer
    permission_classes = [permissions.IsAuthenticated]
    lookup_field = 'id_lote'

    def list(self, request, *args, **kwargs):
        search = request.query_params.get('search')
        qs = self.get_queryset()
        if search:
            search = search.strip()
            qs = qs.filter(
                Q(id_lote__icontains=search) |
                Q(producto__id_producto__icontains=search) |
                Q(producto__nombre__icontains=search)
            )
        page = self.paginate_queryset(qs)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        serializer = self.get_serializer(qs, many=True)
        return response.Response(serializer.data)

    @decorators.action(detail=False, methods=['get'], url_path='por-vencer')
    def por_vencer(self, request):
        """Lotes que vencen en los próximos N días (default 30)."""
        try:
            dias = int(request.query_params.get('dias', '30'))
        except ValueError:
            dias = 30

        hoy = timezone.now().date()
        limite = hoy + timezone.timedelta(days=dias)
        qs = self.get_queryset().filter(
            fecha_vencimiento__range=[hoy, limite]
        ).order_by('fecha_vencimiento')
        serializer = self.get_serializer(qs, many=True)
        return response.Response(serializer.data)

    @decorators.action(detail=False, methods=['get'], url_path=r'trazabilidad/(?P<id_producto>[^/.]+)')
    def trazabilidad(self, request, id_producto=None):
        """Todos los lotes de un producto (ordenado por vencimiento)."""
        qs = self.get_queryset().filter(producto__id_producto=id_producto).order_by('fecha_vencimiento')
        serializer = self.get_serializer(qs, many=True)
        return response.Response(serializer.data)
 