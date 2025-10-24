# apps/catalogo/urls.py
from django.urls import path
from . import views

app_name = 'catalogo'

urlpatterns = [
    # Filtros disponibles
    path('filtros/', views.obtener_filtros_disponibles, name='filtros-disponibles'),
    
    # Filtros dependientes
    path('colores-por-categoria/', views.obtener_colores_por_categoria, name='colores-por-categoria'),
    path('medidas-por-color/', views.obtener_medidas_por_color, name='medidas-por-color'),
    
    # Búsqueda y listado
    path('productos/', views.buscar_productos, name='buscar-productos'),
    path('productos/<str:id_producto>/', views.obtener_detalle_producto, name='detalle-producto'),
    
    # Estadísticas
    path('estadisticas/', views.obtener_estadisticas_catalogo, name='estadisticas'),
]