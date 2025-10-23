from django.urls import path
from . import views

urlpatterns = [
    # Lista de registros de bitácora (solo admins) - PAGINADO
    path('logs/', views.BitacoraListView.as_view(), name='bitacora_logs'),
    
    # Estadísticas generales (solo admins)
    path('estadisticas/', views.estadisticas_bitacora, name='bitacora_estadisticas'),
    
    # Actividad de un usuario específico (solo admins) - PAGINADO
    path('usuario/<int:usuario_id>/actividad/', views.actividad_usuario, name='actividad_usuario'),
    
    # Mi propia actividad (usuarios autenticados) - PAGINADO
    path('mi-actividad/', views.mi_actividad, name='mi_actividad'),

    # Últimos movimientos (solo admins) - PAGINADO
    path('ultimos-movimientos/', views.ultimos_movimientos, name='ultimos_movimientos'),
    
    # Eventos sospechosos (solo admins) - PAGINADO - NUEVO ENDPOINT
    path('eventos-sospechosos/', views.eventos_sospechosos, name='eventos_sospechosos'),
]