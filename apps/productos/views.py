from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q
from django.utils import timezone

from .models import Producto, ConfiguracionLente
from .serializers import (
    ProductoListSerializer,
    ProductoDetalleSerializer,
    CrearProductoSerializer,
    ActualizarProductoSerializer,
    CambiarEstadoSerializer,
    AjustarStockSerializer,
    ConfiguracionLenteSerializer
)

# Importar señales
from apps.bitacora.signals import (
    producto_creado,
    producto_actualizado,
    producto_eliminado,
    producto_estado_cambiado,
    producto_stock_ajustado
)


class ProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestión completa de productos
    
    Endpoints:
    - GET    /productos/          - Listar productos
    - GET    /productos/{id}/     - Obtener producto específico
    - POST   /productos/          - Crear producto
    - PUT    /productos/{id}/     - Actualizar producto completo
    - PATCH  /productos/{id}/     - Actualizar producto parcial
    - DELETE /productos/{id}/     - Eliminar producto
    
    Acciones personalizadas:
    - PATCH  /productos/{id}/cambiar-estado/  - Cambiar estado
    - POST   /productos/{id}/ajustar-stock/   - Ajustar stock
    """
    
    queryset = Producto.objects.select_related(
        'id_categoria',
        'id_configuracion',
        'id_configuracion__id_medida'
    ).prefetch_related('imagenes')
    
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['id_categoria', 'estado_producto']
    search_fields = ['nombre', 'descripcion', 'id_producto']
    ordering_fields = ['nombre', 'precio', 'stock', 'fecha_creacion']
    ordering = ['-fecha_creacion']
    
    def get_serializer_class(self):
        """Retorna el serializer según la acción"""
        if self.action == 'list':
            return ProductoListSerializer
        elif self.action == 'create':
            return CrearProductoSerializer
        elif self.action in ['update', 'partial_update']:
            return ActualizarProductoSerializer
        return ProductoDetalleSerializer
    
    def get_permissions(self):
        """
        Permisos por acción:
        - Listar y ver: público (AllowAny)
        - Crear, editar, eliminar: autenticado (IsAuthenticated)
        """
        if self.action in ['list', 'retrieve']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        """Aplicar filtros adicionales por query params"""
        queryset = super().get_queryset()
        
        # Filtro por rango de precio
        precio_min = self.request.query_params.get('precio_min')
        precio_max = self.request.query_params.get('precio_max')
        
        if precio_min:
            queryset = queryset.filter(precio__gte=precio_min)
        
        if precio_max:
            queryset = queryset.filter(precio__lte=precio_max)
        
        # Filtro por stock
        stock_min = self.request.query_params.get('stock_min')
        if stock_min:
            queryset = queryset.filter(stock__gte=stock_min)
        
        # Filtro por tiene_medida (lentes con/sin medida)
        tiene_medida = self.request.query_params.get('tiene_medida')
        if tiene_medida is not None:
            if tiene_medida.lower() == 'true':
                # Lentes con medida (medida != 0.00)
                queryset = queryset.filter(
                    id_configuracion__isnull=False
                ).exclude(
                    id_configuracion__id_medida__medida=0.00
                )
            else:
                # Lentes sin medida o productos sin configuración
                queryset = queryset.filter(
                    Q(id_configuracion__isnull=True) |
                    Q(id_configuracion__id_medida__medida=0.00)
                )
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """Listar productos con paginación"""
        queryset = self.filter_queryset(self.get_queryset())
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, *args, **kwargs):
        """Obtener producto específico con todos los detalles"""
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return Response(serializer.data)
    
    def create(self, request, *args, **kwargs):
        """Crear nuevo producto"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        producto = serializer.save()
        
        # Emitir señal para bitácora
        producto_creado.send(
            sender=self.__class__,
            producto=producto,
            usuario=request.user,
            ip=self.get_client_ip(request)
        )
        
        # Retornar con serializer de detalle
        response_serializer = ProductoDetalleSerializer(producto)
        return Response(
            response_serializer.data,
            status=status.HTTP_201_CREATED
        )
    
    def update(self, request, *args, **kwargs):
        """Actualizar producto (PUT completo o PATCH parcial)"""
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        serializer = self.get_serializer(
            instance, 
            data=request.data, 
            partial=partial,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)
        producto = serializer.save()
        
        # Obtener cambios del contexto
        cambios = serializer.context.get('cambios', {})
        
        # Emitir señal para bitácora
        producto_actualizado.send(
            sender=self.__class__,
            producto=producto,
            usuario=request.user,
            ip=self.get_client_ip(request),
            cambios=cambios
        )
        
        # Retornar con serializer de detalle
        response_serializer = ProductoDetalleSerializer(producto)
        response_data = response_serializer.data
        
        # Agregar información de cambios si existen
        if cambios:
            response_data['cambios_realizados'] = cambios
        
        return Response(response_data)
    
    def partial_update(self, request, *args, **kwargs):
        """Actualización parcial (PATCH)"""
        kwargs['partial'] = True
        return self.update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        """Eliminar producto"""
        instance = self.get_object()
        
        # Validar si tiene ventas (esto lo implementaremos después)
        # Por ahora permitir eliminación
        
        # Guardar datos para bitácora antes de eliminar
        producto_id = instance.id_producto
        producto_nombre = instance.nombre
        
        # Eliminar
        instance.delete()
        
        # Emitir señal para bitácora
        # Como el objeto ya no existe, pasamos la info guardada
        from types import SimpleNamespace
        producto_eliminado_data = SimpleNamespace(
            id_producto=producto_id,
            nombre=producto_nombre
        )
        
        producto_eliminado.send(
            sender=self.__class__,
            producto=producto_eliminado_data,
            usuario=request.user,
            ip=self.get_client_ip(request),
            motivo=request.data.get('motivo', 'Sin motivo especificado')
        )
        
        return Response(
            {'message': 'Producto eliminado exitosamente'},
            status=status.HTTP_204_NO_CONTENT
        )
    
    @action(detail=True, methods=['patch'], url_path='cambiar-estado')
    def cambiar_estado(self, request, pk=None):
        """
        Cambiar estado del producto (ACTIVO/INACTIVO)
        
        POST /productos/{id}/cambiar-estado/
        Body: {
            "estado_producto": "INACTIVO",
            "motivo": "Producto descontinuado"
        }
        """
        producto = self.get_object()
        serializer = CambiarEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        nuevo_estado = serializer.validated_data['estado_producto']
        motivo = serializer.validated_data.get('motivo', 'Sin motivo especificado')
        
        # Guardar estado anterior
        estado_anterior = producto.estado_producto
        
        # Cambiar estado
        producto.estado_producto = nuevo_estado
        producto.save()
        
        # Emitir señal para bitácora
        producto_estado_cambiado.send(
            sender=self.__class__,
            producto=producto,
            usuario=request.user,
            ip=self.get_client_ip(request),
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            motivo=motivo
        )
        
        return Response({
            'id_producto': producto.id_producto,
            'estado_producto': producto.estado_producto,
            'estado_anterior': estado_anterior,
            'motivo': motivo,
            'message': 'Estado actualizado correctamente',
            'visible_en_catalogo': nuevo_estado == 'ACTIVO'
        })
    
    @action(detail=True, methods=['post'], url_path='ajustar-stock')
    def ajustar_stock(self, request, pk=None):
        """
        Ajustar stock del producto
        
        POST /productos/{id}/ajustar-stock/
        Body: {
            "tipo_ajuste": "INCREMENTO",  // INCREMENTO, DECREMENTO, CORRECCION
            "cantidad": 10,
            "motivo": "Recepción de compra #045"
        }
        """
        producto = self.get_object()
        serializer = AjustarStockSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        tipo_ajuste = serializer.validated_data['tipo_ajuste']
        cantidad = serializer.validated_data['cantidad']
        motivo = serializer.validated_data['motivo']
        
        # Guardar stock anterior
        stock_anterior = producto.stock
        
        # Realizar ajuste
        if tipo_ajuste == 'INCREMENTO':
            producto.stock += cantidad
        elif tipo_ajuste == 'DECREMENTO':
            if producto.stock < cantidad:
                return Response(
                    {
                        'detail': 'Stock insuficiente para el ajuste',
                        'stock_actual': producto.stock,
                        'cantidad_solicitada': cantidad,
                        'deficit': cantidad - producto.stock
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            producto.stock -= cantidad
        elif tipo_ajuste == 'CORRECCION':
            producto.stock = cantidad
        
        producto.save()
        
        # Emitir señal para bitácora
        producto_stock_ajustado.send(
            sender=self.__class__,
            producto=producto,
            usuario=request.user,
            ip=self.get_client_ip(request),
            tipo_ajuste=tipo_ajuste,
            cantidad=cantidad,
            stock_anterior=stock_anterior,
            stock_nuevo=producto.stock,
            motivo=motivo
        )
        
        return Response({
            'id_producto': producto.id_producto,
            'stock_anterior': stock_anterior,
            'stock_nuevo': producto.stock,
            'ajuste': cantidad if tipo_ajuste != 'CORRECCION' else producto.stock - stock_anterior,
            'tipo_ajuste': tipo_ajuste,
            'motivo': motivo,
            'fecha_ajuste': timezone.now(),
            'usuario': request.user.nombre_usuario,
            'message': 'Stock ajustado exitosamente'
        })
    
    def get_client_ip(self, request):
        """Obtener IP real del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ConfiguracionLenteViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet de solo lectura para configuraciones de lentes
    Útil para que el frontend cargue las opciones disponibles
    """
    queryset = ConfiguracionLente.objects.select_related('id_medida').all()
    serializer_class = ConfiguracionLenteSerializer
    permission_classes = [AllowAny]
    
    def get_queryset(self):
        """Filtros opcionales"""
        queryset = super().get_queryset()
        
        # Filtrar por color
        color = self.request.query_params.get('color')
        if color:
            queryset = queryset.filter(color__icontains=color)
        
        # Filtrar por medida
        medida = self.request.query_params.get('medida')
        if medida:
            queryset = queryset.filter(id_medida__medida=medida)
        
        return queryset