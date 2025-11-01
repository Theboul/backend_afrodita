from django.shortcuts import render

# apps/catalogo/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework import status
from django.db.models import Q, Count
import math

from apps.productos.models import Producto, ConfiguracionLente, Medida
from apps.categoria.models import Categoria
from core.constants import APIResponse, Messages, ProductStatus, CategoryStatus, CatalogConfig
from .serializers import (
    ProductoCatalogoListSerializer,
    ProductoCatalogoDetalleSerializer,
    CategoriaCatalogoSerializer,
    MedidaCatalogoSerializer,
    ColorDisponibleSerializer,
    MedidaDisponibleSerializer
)


# ==========================================================
# CU12: CONSULTAR CATÁLOGO CON FILTROS DEPENDIENTES
# ==========================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_filtros_disponibles(request):
    """
    GET /api/catalogo/filtros/
    
    Retorna todos los filtros disponibles para el catálogo público:
    - Categorías activas con productos disponibles
    - Colores (tonos) disponibles
    - Medidas disponibles
    
    Respuesta:
    {
        "categorias": [...],
        "colores": ["Azul", "Verde", ...],
        "medidas": [...],
        "mensaje": "Filtros cargados exitosamente"
    }
    """
    # Categorías con productos activos y stock
    categorias = Categoria.objects.filter(
        estado_categoria=CategoryStatus.ACTIVA,
        productos__estado_producto=ProductStatus.ACTIVO,
        productos__stock__gt=0
    ).distinct().order_by('nombre')
    
    # Colores disponibles (de productos activos con stock)
    colores = ConfiguracionLente.objects.filter(
        productos__estado_producto=ProductStatus.ACTIVO,
        productos__stock__gt=0
    ).values_list('color', flat=True).distinct().order_by('color')
    
    # Medidas disponibles (de productos activos con stock)
    medidas = Medida.objects.filter(
        configuraciones__productos__estado_producto=ProductStatus.ACTIVO,
        configuraciones__productos__stock__gt=0
    ).distinct().order_by('medida')
    
    return APIResponse.success(
        data={
            'categorias': CategoriaCatalogoSerializer(categorias, many=True).data,
            'colores': list(colores),
            'medidas': MedidaCatalogoSerializer(medidas, many=True).data,
            'total_categorias': categorias.count(),
            'total_colores': len(colores),
            'total_medidas': medidas.count(),
        },
        message=Messages.FILTERS_LOADED
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_colores_por_categoria(request):
    """
    GET /api/catalogo/colores-por-categoria/?categoria=1
    
    Retorna los colores (tonos) disponibles para una categoría específica.
    
    Parámetros:
    - categoria (int): ID de la categoría
    
    Respuesta:
    {
        "categoria": {"id": 1, "nombre": "Lentes de Contacto"},
        "colores": [
            {"color": "Azul", "productos_disponibles": 5},
            {"color": "Verde", "productos_disponibles": 3}
        ],
        "total_colores": 2
    }
    """
    categoria_id = request.query_params.get('categoria')
    
    if not categoria_id:
        return APIResponse.bad_request(
            message=Messages.CATEGORY_PARAM_REQUIRED
        )
    
    # Verificar que la categoría existe y está activa
    try:
        categoria = Categoria.objects.get(
            id_categoria=categoria_id,
            estado_categoria=CategoryStatus.ACTIVA
        )
    except Categoria.DoesNotExist:
        return APIResponse.not_found(
            message=Messages.CATEGORY_NOT_ACTIVE
        )
    
    # Obtener colores disponibles para esa categoría
    colores = ConfiguracionLente.objects.filter(
        productos__id_categoria_id=categoria_id,
        productos__estado_producto=ProductStatus.ACTIVO,
        productos__stock__gt=0
    ).values_list('color', flat=True).distinct().order_by('color')
    
    if not colores:
        return APIResponse.success(
            data={
                'categoria': CategoriaCatalogoSerializer(categoria).data,
                'colores': [],
                'total_colores': 0,
            },
            message=Messages.NO_PRODUCTS_IN_CATEGORY
        )
    
    # Contar productos por color
    colores_data = []
    for color in colores:
        count = Producto.objects.filter(
            estado_producto=ProductStatus.ACTIVO,
            stock__gt=0,
            id_categoria_id=categoria_id,
            id_configuracion__color=color
        ).count()
        
        colores_data.append({
            'color': color,
            'productos_disponibles': count
        })
    
    return APIResponse.success(
        data={
            'categoria': CategoriaCatalogoSerializer(categoria).data,
            'colores': colores_data,
            'total_colores': len(colores_data)
        }
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_medidas_por_color(request):
    """
    GET /api/catalogo/medidas-por-color/?color=Azul
    GET /api/catalogo/medidas-por-color/?color=Azul&categoria=1
    
    ENDPOINT CLAVE PARA FILTROS DEPENDIENTES
    
    Retorna las medidas disponibles para un color (tono) específico.
    Opcionalmente puede filtrarse también por categoría.
    
    Parámetros:
    - color (str): Nombre del color (REQUERIDO)
    - categoria (int): ID de la categoría (OPCIONAL)
    
    Respuesta:
    {
        "color": "Azul",
        "categoria_id": 1,
        "medidas": [
            {
                "id_medida": 1,
                "medida": "-1.00",
                "descripcion": "Miopía leve",
                "productos_disponibles": 3
            }
        ],
        "total_medidas": 1
    }
    
    Excepciones:
    - No existe el color: retorna medidas vacías con mensaje
    - No hay medidas para ese color: retorna medidas vacías con mensaje
    """
    color = request.query_params.get('color')
    categoria_id = request.query_params.get('categoria')
    
    if not color:
        return APIResponse.bad_request(
            message=Messages.COLOR_PARAM_REQUIRED
        )
    
    # Validar que el color existe en productos activos con stock
    if not ConfiguracionLente.objects.filter(
        color=color,
        productos__estado_producto=ProductStatus.ACTIVO,
        productos__stock__gt=0
    ).exists():
        return APIResponse.success(
            data={
                'color': color,
                'categoria_id': categoria_id,
                'medidas': [],
                'total_medidas': 0,
            },
            message=Messages.NO_PRODUCTS_IN_COLOR
        )
    
    # Base queryset: medidas de ese color con stock
    queryset = Medida.objects.filter(
        configuraciones__color=color,
        configuraciones__productos__estado_producto=ProductStatus.ACTIVO,
        configuraciones__productos__stock__gt=0
    )
    
    # Si viene categoría, filtrar también por ella
    if categoria_id:
        queryset = queryset.filter(
            configuraciones__productos__id_categoria_id=categoria_id
        )
    
    medidas = queryset.distinct().order_by('medida')
    
    if not medidas.exists():
        mensaje = Messages.NO_MEASURES_FOR_COLOR
        if categoria_id:
            mensaje = Messages.NO_MEASURES_IN_CATEGORY
        
        return APIResponse.success(
            data={
                'color': color,
                'categoria_id': categoria_id,
                'medidas': [],
                'total_medidas': 0,
            },
            message=mensaje
        )
    
    # Contar productos por medida
    medidas_data = []
    for medida in medidas:
        count_productos = Producto.objects.filter(
            estado_producto=ProductStatus.ACTIVO,
            stock__gt=0,
            id_configuracion__color=color,
            id_configuracion__id_medida=medida
        )
        
        if categoria_id:
            count_productos = count_productos.filter(id_categoria_id=categoria_id)
        
        medidas_data.append({
            'id_medida': medida.id_medida,
            'medida': str(medida.medida),
            'descripcion': medida.descripcion,
            'productos_disponibles': count_productos.count()
        })
    
    return APIResponse.success(
        data={
            'color': color,
            'categoria_id': categoria_id,
            'medidas': medidas_data,
            'total_medidas': len(medidas_data)
        }
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def buscar_productos(request):
    """
    GET /api/catalogo/productos/
    
    Endpoint principal para buscar productos con filtros dependientes.
    
    Parámetros de filtrado:
    - categoria (int): ID de categoría
    - color (str): Color/tono del lente
    - medida (int): ID de medida
    - search (str): Búsqueda por texto (nombre, descripción, ID)
    - precio_min (decimal): Precio mínimo
    - precio_max (decimal): Precio máximo
    - orden (str): Ordenamiento (nombre, precio_asc, precio_desc, recientes)
    - page (int): Número de página (default: 1)
    - page_size (int): Productos por página (default: 12)
    
    Ejemplos:
    - /api/catalogo/productos/
    - /api/catalogo/productos/?categoria=1
    - /api/catalogo/productos/?categoria=1&color=Azul
    - /api/catalogo/productos/?categoria=1&color=Azul&medida=2
    - /api/catalogo/productos/?search=acuvue&color=Azul
    - /api/catalogo/productos/?precio_min=50&precio_max=150
    
    Respuesta:
    {
        "resultados": [...],
        "total": 25,
        "pagina_actual": 1,
        "productos_por_pagina": 12,
        "total_paginas": 3,
        "filtros_aplicados": {...}
    }
    """
    # Iniciar con productos activos y con stock
    queryset = Producto.objects.filter(
        estado_producto=ProductStatus.ACTIVO,
        stock__gt=0
    ).select_related(
        'id_categoria',
        'id_configuracion',
        'id_configuracion__id_medida'
    ).prefetch_related('imagenes')
    
    # === FILTROS ===
    
    # Filtro por categoría
    categoria_id = request.query_params.get('categoria')
    if categoria_id:
        queryset = queryset.filter(id_categoria_id=categoria_id)
    
    # Filtro por color (tono)
    color = request.query_params.get('color')
    if color:
        queryset = queryset.filter(id_configuracion__color=color)
    
    # Filtro por medida (dependiente del color)
    medida_id = request.query_params.get('medida')
    if medida_id:
        queryset = queryset.filter(id_configuracion__id_medida_id=medida_id)
    
    # Búsqueda por texto
    search = request.query_params.get('search')
    if search:
        queryset = queryset.filter(
            Q(nombre__icontains=search) | 
            Q(descripcion__icontains=search) |
            Q(id_producto__icontains=search)
        )
    
    # Filtro por rango de precio
    precio_min = request.query_params.get('precio_min')
    precio_max = request.query_params.get('precio_max')
    
    if precio_min:
        try:
            queryset = queryset.filter(precio__gte=float(precio_min))
        except ValueError:
            pass
    
    if precio_max:
        try:
            queryset = queryset.filter(precio__lte=float(precio_max))
        except ValueError:
            pass
    
    # === ORDENAMIENTO ===
    orden = request.query_params.get('orden', CatalogConfig.get_default_sort())
    
    if orden == CatalogConfig.SORT_PRECIO_ASC:
        queryset = queryset.order_by('precio')
    elif orden == CatalogConfig.SORT_PRECIO_DESC:
        queryset = queryset.order_by('-precio')
    elif orden == CatalogConfig.SORT_NOMBRE:
        queryset = queryset.order_by('nombre')
    elif orden == CatalogConfig.SORT_RECIENTES:
        queryset = queryset.order_by('-fecha_creacion')
    else:
        queryset = queryset.order_by('nombre')
    
    # === PAGINACIÓN ===
    total_productos = queryset.count()
    
    try:
        page = int(request.query_params.get('page', CatalogConfig.PAGE_MIN))
        page_size = int(request.query_params.get('page_size', CatalogConfig.PAGE_SIZE_DEFAULT))
    except ValueError:
        page = CatalogConfig.PAGE_MIN
        page_size = CatalogConfig.PAGE_SIZE_DEFAULT
    
    # Validar página
    if page < CatalogConfig.PAGE_MIN:
        page = CatalogConfig.PAGE_MIN
    
    if page_size < CatalogConfig.PAGE_MIN or page_size > CatalogConfig.PAGE_SIZE_MAX:
        page_size = CatalogConfig.PAGE_SIZE_DEFAULT
    
    start = (page - 1) * page_size
    end = start + page_size
    
    productos_paginados = queryset[start:end]
    
    # Calcular total de páginas
    total_paginas = math.ceil(total_productos / page_size) if total_productos > 0 else 1
    
    # === SERIALIZAR ===
    serializer = ProductoCatalogoListSerializer(productos_paginados, many=True)
    
    return APIResponse.success(
        data={
            'resultados': serializer.data,
            'total': total_productos,
            'pagina_actual': page,
            'productos_por_pagina': page_size,
            'total_paginas': total_paginas,
            'tiene_siguiente': page < total_paginas,
            'tiene_anterior': page > 1,
            'filtros_aplicados': {
                'categoria': categoria_id,
                'color': color,
                'medida': medida_id,
                'search': search,
                'precio_min': precio_min,
                'precio_max': precio_max,
                'orden': orden
            }
        }
    )


@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_detalle_producto(request, id_producto):
    """
    GET /api/catalogo/productos/{id_producto}/
    
    Retorna el detalle completo de un producto específico.
    
    Parámetros:
    - id_producto (str): ID del producto
    
    Respuesta: Producto con toda su información
    """
    try:
        producto = Producto.objects.select_related(
            'id_categoria',
            'id_configuracion',
            'id_configuracion__id_medida'
        ).prefetch_related('imagenes').get(
            id_producto=id_producto,
            estado_producto=ProductStatus.ACTIVO
        )
    except Producto.DoesNotExist:
        return APIResponse.not_found(
            message=Messages.PRODUCT_NOT_AVAILABLE
        )
    
    serializer = ProductoCatalogoDetalleSerializer(producto)
    return APIResponse.success(data=serializer.data)


@api_view(['GET'])
@permission_classes([AllowAny])
def obtener_estadisticas_catalogo(request):
    """
    GET /api/catalogo/estadisticas/
    
    Retorna estadísticas generales del catálogo.
    Útil para mostrar información en el dashboard del cliente.
    
    Respuesta:
    {
        "total_productos": 45,
        "total_categorias": 5,
        "total_colores": 8,
        "productos_con_stock": 42,
        "productos_sin_stock": 3
    }
    """
    total_productos = Producto.objects.filter(estado_producto=ProductStatus.ACTIVO).count()
    productos_con_stock = Producto.objects.filter(
        estado_producto=ProductStatus.ACTIVO,
        stock__gt=0
    ).count()
    productos_sin_stock = total_productos - productos_con_stock
    
    total_categorias = Categoria.objects.filter(
        estado_categoria=CategoryStatus.ACTIVA,
        productos__estado_producto=ProductStatus.ACTIVO
    ).distinct().count()
    
    total_colores = ConfiguracionLente.objects.filter(
        productos__estado_producto=ProductStatus.ACTIVO
    ).values('color').distinct().count()
    
    return APIResponse.success(
        data={
            'total_productos': total_productos,
            'total_categorias': total_categorias,
            'total_colores': total_colores,
            'productos_con_stock': productos_con_stock,
            'productos_sin_stock': productos_sin_stock,
            'porcentaje_disponibilidad': round(
                (productos_con_stock / total_productos * 100) if total_productos > 0 else 0,
                2
            )
        }
    )