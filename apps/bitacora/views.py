from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from django.db.models import Count, Q
from datetime import datetime, timedelta
from django.utils import timezone

from .models import Bitacora
from .serializers import BitacoraSerializer

class BitacoraListView(generics.ListAPIView):
    """
    Vista para listar registros de bitácora con filtros.
    Solo accesible para administradores.
    """
    queryset = Bitacora.objects.all()
    serializer_class = BitacoraSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    
    search_fields = ['descripcion', 'ip', 'id_usuario__nombre_usuario']
    ordering_fields = ['fecha_hora', 'accion']
    ordering = ['-fecha_hora']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        # Filtro por fechas
        fecha_desde = self.request.query_params.get('fecha_desde')
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        
        if fecha_desde:
            queryset = queryset.filter(fecha_hora__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_hora__lte=fecha_hasta)
            
        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def estadisticas_bitacora(request):
    """
    Endpoint para obtener estadísticas de la bitácora.
    """
    # Parámetros de tiempo
    dias = int(request.query_params.get('dias', 7))
    fecha_limite = timezone.now() - timedelta(days=dias)
    
    # Estadísticas por acción
    stats_por_accion = Bitacora.objects.filter(
        fecha_hora__gte=fecha_limite
    ).values('accion').annotate(
        total=Count('id_bitacora')
    ).order_by('-total')
    
    # Usuarios más activos
    usuarios_activos = Bitacora.objects.filter(
        fecha_hora__gte=fecha_limite,
        id_usuario__isnull=False
    ).values(
        'id_usuario__nombre_usuario'
    ).annotate(
        total=Count('id_bitacora')
    ).order_by('-total')[:10]
    
    # Actividad por día
    actividad_diaria = []
    for i in range(dias):
        fecha = timezone.now() - timedelta(days=i)
        inicio_dia = fecha.replace(hour=0, minute=0, second=0, microsecond=0)
        fin_dia = inicio_dia + timedelta(days=1)
        
        count = Bitacora.objects.filter(
            fecha_hora__gte=inicio_dia,
            fecha_hora__lt=fin_dia
        ).count()
        
        actividad_diaria.append({
            'fecha': inicio_dia.strftime('%Y-%m-%d'),
            'total': count
        })
    
    # Actividad de usuarios anónimos vs registrados
    total_eventos = Bitacora.objects.filter(fecha_hora__gte=fecha_limite).count()
    eventos_anonimos = Bitacora.objects.filter(
        fecha_hora__gte=fecha_limite,
        id_usuario__isnull=True
    ).count()
    eventos_registrados = total_eventos - eventos_anonimos
    
    return Response({
        'periodo': f'Últimos {dias} días',
        'total_eventos': total_eventos,
        'estadisticas_por_accion': list(stats_por_accion),
        'usuarios_mas_activos': list(usuarios_activos),
        'actividad_diaria': actividad_diaria,
        'distribucion_usuarios': {
            'registrados': eventos_registrados,
            'anonimos': eventos_anonimos
        }
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def actividad_usuario(request, usuario_id):
    """
    Endpoint para obtener la actividad de un usuario específico.
    """
    dias = int(request.query_params.get('dias', 30))
    fecha_limite = timezone.now() - timedelta(days=dias)
    
    actividad = Bitacora.objects.filter(
        id_usuario_id=usuario_id,
        fecha_hora__gte=fecha_limite
    ).order_by('-fecha_hora')
    
    serializer = BitacoraSerializer(actividad, many=True)
    
    return Response({
        'usuario_id': usuario_id,
        'periodo': f'Últimos {dias} días',
        'total_eventos': actividad.count(),
        'eventos': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mi_actividad(request):
    """
    Endpoint para que un usuario vea su propia actividad.
    """
    dias = int(request.query_params.get('dias', 7))
    fecha_limite = timezone.now() - timedelta(days=dias)
    
    mi_actividad = Bitacora.objects.filter(
        id_usuario=request.user,
        fecha_hora__gte=fecha_limite
    ).order_by('-fecha_hora')
    
    serializer = BitacoraSerializer(mi_actividad, many=True)
    
    return Response({
        'periodo': f'Últimos {dias} días',
        'total_eventos': mi_actividad.count(),
        'eventos': serializer.data
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])  # o AllowAny si deseas acceso público
def ultimos_movimientos(request):
    logs = Bitacora.objects.select_related("id_usuario").order_by('-fecha_hora')[:50]
    serializer = BitacoraSerializer(logs, many=True)
    return Response(serializer.data)