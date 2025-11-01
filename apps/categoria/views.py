from itertools import count
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db import connection
from django.db.models import Count
from django.db.models import Exists, OuterRef
from .models import Categoria
from apps.productos.models import Producto
from .serializers import CategoriaSerializer
from rest_framework.permissions import IsAdminUser
from apps.bitacora.signals import (
    categoria_eliminada,
    categoria_restaurada,
    categoria_creada,
    categoria_actualizada,
    categoria_movida
)
from apps.autenticacion.utils import obtener_ip_cliente
from core.constants import CategoryStatus, APIResponse, Messages


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = [IsAdminUser]

    # === GET /api/categorias/?jerarquia=true ===
    def get_queryset(self):
        jerarquia = self.request.query_params.get('jerarquia')
        base_qs = Categoria.objects.filter(estado_categoria=CategoryStatus.ACTIVA)

        if jerarquia == 'true':
            return base_qs.filter(id_catpadre__isnull=True)
        return base_qs

    #=== POST /api/categorias/ ===
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        categoria = serializer.save()

        ip_cliente = obtener_ip_cliente(request)
        categoria_creada.send(
            sender=self.__class__,
            categoria=categoria,
            usuario=request.user,
            ip=ip_cliente
        )

        return APIResponse.created(
            message=Messages.CATEGORY_CREATED,
            data={"categoria": serializer.data}
        )

    # === PUT/PATCH /api/categorias/{id}/ ===
    @transaction.atomic
    def update(self, request, *args, **kwargs):
        categoria = self.get_object()
        datos_antes = {"nombre": categoria.nombre, "padre": categoria.id_catpadre_id}

        serializer = self.get_serializer(categoria, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        categoria_actualizada_obj = serializer.save()

        datos_despues = {"nombre": categoria_actualizada_obj.nombre, "padre": categoria_actualizada_obj.id_catpadre_id}

        cambios = []
        for campo in datos_antes:
            if datos_antes[campo] != datos_despues[campo]:
                cambios.append({
                    "campo": campo,
                    "antes": datos_antes[campo],
                    "despues": datos_despues[campo]
                })

        if cambios:
            ip_cliente = obtener_ip_cliente(request)
            categoria_actualizada.send(
                sender=self.__class__,
                categoria=categoria_actualizada_obj,
                usuario=request.user,
                ip=ip_cliente,
                cambios=cambios
            )

        return APIResponse.success(
            message=Messages.CATEGORY_UPDATED,
            data={
                "cambios": cambios,
                "categoria": serializer.data
            }
        )

    # === DELETE /api/categorias/{id}/ ===
    def destroy(self, request, *args, **kwargs):
        categoria = self.get_object()

        # No eliminar si tiene subcategorías
        if categoria.subcategorias.exists():
            return APIResponse.error(
                message=Messages.CATEGORY_HAS_SUBCATEGORIES,
                status_code=status.HTTP_409_CONFLICT
            )

        # No eliminar si tiene productos activos
        if Producto.objects.filter(id_categoria=categoria.id_categoria).exists():
            return APIResponse.error(
                message=Messages.CATEGORY_HAS_PRODUCTS,
                status_code=status.HTTP_409_CONFLICT
            )
        
        categoria.estado_categoria = CategoryStatus.INACTIVA
        categoria.save()

        ip_cliente = obtener_ip_cliente(request)

        categoria_eliminada.send(
            sender=self.__class__,
            categoria=categoria,
            usuario=request.user,
            ip=ip_cliente,
            motivo="Eliminación lógica de categoría"
        )
        return Response(status=status.HTTP_204_NO_CONTENT)
    

    # === POST /api/categorias/{id}/restaurar/ ===
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def restaurar(self, request, pk=None):
        categoria = Categoria.objects.filter(id_categoria=pk).first()
        if not categoria:
            return APIResponse.not_found(message=Messages.CATEGORY_NOT_FOUND)

        if categoria.estado_categoria == CategoryStatus.ACTIVA:
            return APIResponse.bad_request(message=Messages.CATEGORY_ALREADY_ACTIVE)

        categoria.estado_categoria = CategoryStatus.ACTIVA
        categoria.save()

        ip_cliente = obtener_ip_cliente(request)
        categoria_restaurada.send(
            sender=self.__class__,
            categoria=categoria,
            usuario=request.user,
            ip=ip_cliente
        )
        return APIResponse.success(
            message=Messages.CATEGORY_RESTORED,
            data={"categoria": CategoriaSerializer(categoria).data}
        )

    # === POST /api/categorias/{id}/mover/ ===
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def mover(self, request, pk=None):
        categoria = self.get_object()
        nuevo_id = request.data.get('nuevo_padre')
        motivo = request.data.get('motivo', '')

        if nuevo_id == categoria.id_categoria:
            return APIResponse.bad_request(message=Messages.CATEGORY_CANNOT_MOVE_TO_SELF)

        nuevo_padre = Categoria.objects.filter(id_categoria=nuevo_id).first() if nuevo_id else None

        # No permitir mover dentro de sus propias subcategorías
        if self._es_descendiente(nuevo_padre, categoria):
            return APIResponse.bad_request(message=Messages.CATEGORY_CANNOT_MOVE_TO_CHILD)

        origen = categoria.id_catpadre.nombre if categoria.id_catpadre else "Raíz"
        destino = nuevo_padre.nombre if nuevo_padre else "Raíz"

        categoria.id_catpadre = nuevo_padre
        categoria.save()

        ip_cliente = obtener_ip_cliente(request)
        categoria_movida.send(
            sender=self.__class__,
            categoria=categoria,
            usuario=request.user,
            ip=ip_cliente,
            origen=origen,
            destino=destino,
            motivo=motivo
        )

        return APIResponse.success(
            message=Messages.CATEGORY_MOVED,
            data={"ruta_nueva": self._build_ruta(categoria)}
        )

    # === GET /api/categorias/{id}/ruta/ ===
    @action(detail=True, methods=['get'])
    def ruta(self, request, pk=None):
        categoria = self.get_object()
        return Response({"ruta": self._build_ruta(categoria)})

    # === GET /api/categorias/estadisticas/ ===
    @action(detail=False, methods=['get'], url_path='estadisticas')
    def estadisticas(self, request):
        total = Categoria.objects.count()
        principales = Categoria.objects.filter(id_catpadre__isnull=True).count()
        sin_productos = Categoria.objects.annotate(
            tiene_productos=Exists(Producto.objects.filter(id_categoria=OuterRef('id_categoria')))
        ).filter(tiene_productos=False).count()
        nivel_maximo = self._profundidad_maxima()

        return Response({
            "total": total,
            "principales": principales,
            "sin_productos": sin_productos,
            "nivel_maximo": nivel_maximo
        })
    
    # === ENDPOINT: /api/categoria/listar_arbol/
    @action(detail=False, methods=['get'], url_path='listar_arbol')
    def listar_arbol(self, request):
        """
        Devuelve todas las categorías activas en estructura jerárquica,
        optimizada con prefetch y conteo de productos.
        """
        categorias = (
            Categoria.objects.filter(estado_categoria=CategoryStatus.ACTIVA)
            .select_related('id_catpadre')
            .prefetch_related('subcategorias', 'productos')
            .annotate(cantidad_productos=Count('productos'))
            .order_by('nombre')
        )

        # Solo las categorías raíz
        categorias_raiz = [c for c in categorias if c.id_catpadre is None]

        serializer = CategoriaSerializer(
            categorias_raiz, many=True, context={"prefetched_categorias": categorias}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)

    # === MÉTODOS AUXILIARES ===
    def _es_descendiente(self, posible_hijo, posible_padre):
        actual = posible_hijo
        while actual:
            if actual.id_categoria == posible_padre.id_categoria:
                return True
            actual = actual.id_catpadre
        return False

    def _build_ruta(self, categoria):
        ruta = []
        actual = categoria
        while actual:
            ruta.insert(0, {"id_categoria": actual.id_categoria, "nombre": actual.nombre})
            actual = actual.id_catpadre
        return ruta

    def _profundidad_maxima(self):
        with connection.cursor() as cursor:
            cursor.execute("""
                WITH RECURSIVE jerarquia AS (
                    SELECT id_categoria, id_catpadre, 1 AS nivel
                    FROM categoria
                    WHERE id_catpadre IS NULL
                    UNION ALL
                    SELECT c.id_categoria, c.id_catpadre, j.nivel + 1
                    FROM categoria c
                    INNER JOIN jerarquia j ON c.id_catpadre = j.id_categoria
                )
                SELECT MAX(nivel) FROM jerarquia;
            """)
            result = cursor.fetchone()
        return result[0] or 0
    
    # NOTA: El método get_queryset() está definido al inicio de la clase (línea ~28)
    # Esta segunda definición fue eliminada para evitar duplicación
