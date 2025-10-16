from django.urls import path
from . import views

urlpatterns = [
    # Lista de registros de bitácora (solo admins)
    path('logs/', views.BitacoraListView.as_view(), name='bitacora_logs'),
    
    # Estadísticas generales (solo admins)
    path('estadisticas/', views.estadisticas_bitacora, name='bitacora_estadisticas'),
    
    # Actividad de un usuario específico (solo admins)
    path('usuario/<int:usuario_id>/', views.actividad_usuario, name='actividad_usuario'),
    
    # Mi propia actividad (usuarios autenticados)
    path('mi-actividad/', views.mi_actividad, name='mi_actividad'),

    # Últimos 50 registros recientes (solo admins)
    path('ultimos-movimientos/', views.ultimos_movimientos, name='ultimos_movimientos'),
]