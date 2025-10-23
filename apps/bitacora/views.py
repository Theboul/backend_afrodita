from rest_framework import generics, filters, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination
from django.db.models import Count, Q, Func, F
from django.db.models.functions import TruncDate
from datetime import datetime, timedelta
from django.utils import timezone

from .models import Bitacora
from .serializers import BitacoraSerializer

class BitacoraPagination(PageNumberPagination):
    """
    Paginación personalizada para la bitácora.
    """
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200
    page_query_param = 'page'

    def get_paginated_response(self, data):
        """
        Personalizar la respuesta paginada para incluir metadata adicional.
        """
        response = super().get_paginated_response(data)
        
        # Agregar información de filtros aplicados
        request = self.request
        applied_filters = {}
        
        if request.query_params.get('fecha_desde'):
            applied_filters['fecha_desde'] = request.query_params.get('fecha_desde')
        if request.query_params.get('fecha_hasta'):
            applied_filters['fecha_hasta'] = request.query_params.get('fecha_hasta')
        if request.query_params.get('accion'):
            applied_filters['accion'] = request.query_params.get('accion')
        if request.query_params.get('usuario_id'):
            applied_filters['usuario_id'] = request.query_params.get('usuario_id')
        if request.query_params.get('search'):
            applied_filters['search'] = request.query_params.get('search')
            
        response.data['filtros_aplicados'] = applied_filters
        return response


class BitacoraListView(generics.ListAPIView):
    """
    Vista para listar registros de bitácora con filtros.
    Solo accesible para administradores.
    
    OPTIMIZADO: Usa select_related para prevenir N+1 queries.
    PAGINADO: Implementa paginación para mejor rendimiento.
    """
    serializer_class = BitacoraSerializer
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    pagination_class = BitacoraPagination
    
    search_fields = ['descripcion', 'ip', 'id_usuario__nombre_usuario']
    ordering_fields = ['fecha_hora', 'accion']
    ordering = ['-fecha_hora']
    
    def get_queryset(self):
        """
        Optimización: select_related previene N+1 queries al acceder a id_usuario.
        """
        # OPTIMIZACIÓN: select_related para cargar usuario en 1 sola query
        queryset = Bitacora.objects.select_related('id_usuario').all()
        
        # Filtro por fechas
        fecha_desde = self.request.query_params.get('fecha_desde')
        fecha_hasta = self.request.query_params.get('fecha_hasta')
        
        if fecha_desde:
            queryset = queryset.filter(fecha_hora__gte=fecha_desde)
        if fecha_hasta:
            queryset = queryset.filter(fecha_hora__lte=fecha_hasta)
        
        # Filtro por acción (opcional)
        accion = self.request.query_params.get('accion')
        if accion:
            queryset = queryset.filter(accion=accion)
        
        # Filtro por usuario (opcional)
        usuario_id = self.request.query_params.get('usuario_id')
        if usuario_id:
            queryset = queryset.filter(id_usuario_id=usuario_id)
            
        return queryset


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def estadisticas_bitacora(request):
    """
    Endpoint para obtener estadísticas de la bitácora.
    
    OPTIMIZADO: 
    - Usa annotate() para reducir queries
    - TruncDate para agrupar por fecha en una sola query
    - Eliminación de loops con queries individuales
    """
    # Parámetros de tiempo
    dias = int(request.query_params.get('dias', 7))
    fecha_limite = timezone.now() - timedelta(days=dias)
    
    stats_por_accion = Bitacora.objects.filter(
        fecha_hora__gte=fecha_limite
    ).values('accion').annotate(
        total=Count('id_bitacora')
    ).order_by('-total')
    
    usuarios_activos = Bitacora.objects.filter(
        fecha_hora__gte=fecha_limite,
        id_usuario__isnull=False
    ).values(
        'id_usuario__nombre_usuario'
    ).annotate(
        total=Count('id_bitacora')
    ).order_by('-total')[:10]
    

    actividad_diaria_raw = Bitacora.objects.filter(
        fecha_hora__gte=fecha_limite
    ).annotate(
        fecha=TruncDate('fecha_hora')
    ).values('fecha').annotate(
        total=Count('id_bitacora')
    ).order_by('fecha')
    
    # Convertir a diccionario para búsqueda rápida
    actividad_dict = {
        item['fecha'].strftime('%Y-%m-%d'): item['total'] 
        for item in actividad_diaria_raw
    }
    
    # Generar lista completa de días (incluso sin actividad)
    actividad_diaria = []
    for i in range(dias):
        fecha = (timezone.now() - timedelta(days=dias-1-i)).date()
        fecha_str = fecha.strftime('%Y-%m-%d')
        actividad_diaria.append({
            'fecha': fecha_str,
            'total': actividad_dict.get(fecha_str, 0)
        })
    
    total_eventos = Bitacora.objects.filter(fecha_hora__gte=fecha_limite).count()
    eventos_anonimos = Bitacora.objects.filter(
        fecha_hora__gte=fecha_limite,
        id_usuario__isnull=True
    ).count()
    eventos_registrados = total_eventos - eventos_anonimos
    
    # Estadísticas adicionales (opcional pero útil)
    top_ips = Bitacora.objects.filter(
        fecha_hora__gte=fecha_limite,
        ip__isnull=False
    ).values('ip').annotate(
        total=Count('id_bitacora')
    ).order_by('-total')[:10]
    
    return Response({
        'periodo': f'Últimos {dias} días',
        'total_eventos': total_eventos,
        'estadisticas_por_accion': list(stats_por_accion),
        'usuarios_mas_activos': list(usuarios_activos),
        'actividad_diaria': actividad_diaria,
        'distribucion_usuarios': {
            'registrados': eventos_registrados,
            'anonimos': eventos_anonimos,
            'porcentaje_anonimos': round((eventos_anonimos / total_eventos * 100), 2) if total_eventos > 0 else 0
        },
        'top_ips': list(top_ips),
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def actividad_usuario(request, usuario_id):
    """
    Endpoint para obtener la actividad de un usuario específico.
    
    OPTIMIZADO: select_related para prevenir N+1 queries.
    PAGINADO: Implementa paginación para mejor rendimiento.
    """
    dias = int(request.query_params.get('dias', 30))
    fecha_limite = timezone.now() - timedelta(days=dias)
    
    actividad = Bitacora.objects.filter(
        id_usuario_id=usuario_id,
        fecha_hora__gte=fecha_limite
    ).select_related('id_usuario').order_by('-fecha_hora')
    
    page = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 50)), 200)  # Máximo 200
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    
    total_eventos = actividad.count()
    eventos_paginados = actividad[start_index:end_index]
    
    serializer = BitacoraSerializer(eventos_paginados, many=True)
    
    # Estadísticas del usuario
    stats_por_accion = Bitacora.objects.filter(
        id_usuario_id=usuario_id,
        fecha_hora__gte=fecha_limite
    ).values('accion').annotate(
        total=Count('id_bitacora')
    ).order_by('-total')
    
    return Response({
        'usuario_id': usuario_id,
        'periodo': f'Últimos {dias} días',
        'total_eventos': total_eventos,
        'estadisticas_por_accion': list(stats_por_accion),
        'paginacion': {
            'pagina_actual': page,
            'tamano_pagina': page_size,
            'total_paginas': (total_eventos + page_size - 1) // page_size,
            'total_eventos': total_eventos
        },
        'eventos': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def mi_actividad(request):
    """
    Endpoint para que un usuario vea su propia actividad.
    
    OPTIMIZADO: select_related y paginación.
    """
    dias = int(request.query_params.get('dias', 7))
    fecha_limite = timezone.now() - timedelta(days=dias)
    
    mi_actividad = Bitacora.objects.filter(
        id_usuario=request.user,
        fecha_hora__gte=fecha_limite
    ).select_related('id_usuario').order_by('-fecha_hora')
    
    page = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 20)), 100)
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    
    total_eventos = mi_actividad.count()
    eventos_paginados = mi_actividad[start_index:end_index]
    
    serializer = BitacoraSerializer(eventos_paginados, many=True)
    
    # Estadísticas personales
    stats_por_accion = Bitacora.objects.filter(
        id_usuario=request.user,
        fecha_hora__gte=fecha_limite
    ).values('accion').annotate(
        total=Count('id_bitacora')
    ).order_by('-total')
    
    return Response({
        'periodo': f'Últimos {dias} días',
        'total_eventos': total_eventos,
        'estadisticas_por_accion': list(stats_por_accion),
        'paginacion': {
            'pagina_actual': page,
            'tamano_pagina': page_size,
            'total_paginas': (total_eventos + page_size - 1) // page_size,
            'total_eventos': total_eventos
        },
        'eventos': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def ultimos_movimientos(request):
    """
    Endpoint para obtener los últimos movimientos del sistema.
    
    OPTIMIZADO: select_related para prevenir N+1 queries.
    PAGINADO: Implementa paginación básica.
    """
    page = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 50)), 200)
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    
    logs = Bitacora.objects.select_related('id_usuario').order_by('-fecha_hora')
    total_logs = logs.count()
    logs_paginados = logs[start_index:end_index]
    
    serializer = BitacoraSerializer(logs_paginados, many=True)
    
    return Response({
        'total': total_logs,
        'paginacion': {
            'pagina_actual': page,
            'tamano_pagina': page_size,
            'total_paginas': (total_logs + page_size - 1) // page_size,
            'total_eventos': total_logs
        },
        'eventos': serializer.data
    })


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsAdminUser])
def eventos_sospechosos(request):
    """
    Endpoint para obtener eventos de seguridad sospechosos.
    
    Incluye:
    - Intentos de login fallidos
    - Actividad sospechosa
    - Ataques de fuerza bruta detectados
    """
    dias = int(request.query_params.get('dias', 7))
    fecha_limite = timezone.now() - timedelta(days=dias)
    
    # Obtener eventos sospechosos con paginación
    eventos_query = Bitacora.objects.filter(
        fecha_hora__gte=fecha_limite,
        accion__in=['FAILED_LOGIN', 'SUSPICIOUS_ACTIVITY', 'ERROR_500']
    ).select_related('id_usuario').order_by('-fecha_hora')
    
    # AGREGADO: Paginación para eventos sospechosos
    page = int(request.query_params.get('page', 1))
    page_size = min(int(request.query_params.get('page_size', 50)), 100)
    start_index = (page - 1) * page_size
    end_index = start_index + page_size
    
    total_eventos = eventos_query.count()
    eventos_paginados = eventos_query[start_index:end_index]
    
    serializer = BitacoraSerializer(eventos_paginados, many=True)
    
    # Estadísticas de seguridad
    intentos_fallidos_count = Bitacora.objects.filter(
        fecha_hora__gte=fecha_limite,
        accion='FAILED_LOGIN'
    ).count()
    
    actividad_sospechosa_count = Bitacora.objects.filter(
        fecha_hora__gte=fecha_limite,
        accion='SUSPICIOUS_ACTIVITY'
    ).count()
    
    # IPs más sospechosas
    ips_sospechosas = Bitacora.objects.filter(
        fecha_hora__gte=fecha_limite,
        accion__in=['FAILED_LOGIN', 'SUSPICIOUS_ACTIVITY']
    ).values('ip').annotate(
        total=Count('id_bitacora')
    ).order_by('-total')[:10]
    
    return Response({
        'periodo': f'Últimos {dias} días',
        'resumen': {
            'intentos_fallidos': intentos_fallidos_count,
            'actividad_sospechosa': actividad_sospechosa_count,
            'total_eventos_seguridad': total_eventos
        },
        'ips_mas_sospechosas': list(ips_sospechosas),
        'paginacion': {
            'pagina_actual': page,
            'tamano_pagina': page_size,
            'total_paginas': (total_eventos + page_size - 1) // page_size,
            'total_eventos': total_eventos
        },
        'eventos': serializer.data
    })
