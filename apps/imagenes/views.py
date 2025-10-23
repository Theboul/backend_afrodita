from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Case, When, Value, IntegerField, F
from django.core.exceptions import ValidationError

from apps.productos.models import Producto
from .models import ImagenProducto
from .serializers import ImagenProductoSerializer, SubirImagenSerializer

from apps.bitacora.signals import (
    imagen_subida,
    imagen_eliminada,
    imagen_principal_cambiada,
    imagen_actualizada,
    imagen_restaurada,
    imagen_reordenada
)


class ImagenProductoViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las imágenes del catálogo
    Permite:
    - Listar imágenes de un producto
    - Subir nuevas imágenes (con Cloudinary)
    - Marcar imagen como principal
    - Eliminar imágenes (de BD y Cloudinary)
    """

    queryset = ImagenProducto.objects.select_related('id_producto', 'subido_por')
    serializer_class = ImagenProductoSerializer

    # ==========================================================
    # UTILIDADES
    # ==========================================================
    def get_client_ip(self, request):
        """Obtiene la IP real del usuario"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0]
        return request.META.get('REMOTE_ADDR')

    def get_queryset(self):
        producto_id = self.request.query_params.get('producto')
        qs = super().get_queryset().filter(estado_imagen='ACTIVA')
        if producto_id:
            qs = qs.filter(id_producto__id_producto=producto_id)
        return qs.order_by('orden')


    # ==========================================================
    # ACCIONES PRINCIPALES
    # ==========================================================

    @action(detail=False, methods=['post'], url_path='productos/(?P<producto_id>[^/.]+)/subir')
    def subir_imagen(self, request, producto_id=None):
        """
        Subir nueva imagen para un producto específico
        POST /api/imagenes/productos/{id}/subir/
        """
        try:
            producto = Producto.objects.get(id_producto=producto_id)
        except Producto.DoesNotExist:
            return Response({'detail': 'Producto no encontrado'}, status=404)

        serializer = SubirImagenSerializer(
            data=request.data,
            context={'producto': producto, 'request': request}
        )
        serializer.is_valid(raise_exception=True)

        # Guardar imagen
        imagen = serializer.save()

        # Emitir señal para bitácora
        imagen_subida.send(
            sender=self.__class__,
            imagen=imagen,
            usuario=request.user,
            ip=self.get_client_ip(request)
        )

        return Response(
            ImagenProductoSerializer(imagen).data,
            status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=['post'])
    def marcar_principal(self, request, pk=None):
        """
        Marcar una imagen como principal
        POST /api/imagenes/{id}/marcar_principal/
        """
        imagen = self.get_object()
        imagen.marcar_como_principal()

        # Emitir señal para bitácora
        imagen_principal_cambiada.send(
            sender=self.__class__,
            imagen=imagen,
            usuario=request.user,
            ip=self.get_client_ip(request)
        )

        return Response({
            'id_imagen': imagen.id_imagen,
            'producto': imagen.id_producto.id_producto,
            'message': 'Imagen marcada como principal correctamente'
        })

    @action(detail=True, methods=['delete'])
    def eliminar(self, request, pk=None):
        """
        Eliminar imagen (lógica o física con ?force=true)
        DELETE /api/imagenes/{id}/eliminar/?force=true
        """
        imagen = self.get_object()

        if imagen.es_principal:
            return Response(
                {'detail': 'No se puede eliminar la imagen principal'},
                status=status.HTTP_409_CONFLICT
            )

        force_delete = request.query_params.get('force', 'false').lower() == 'true'


        if force_delete:
            imagen.eliminar_de_cloudinary()
            # Emitir señal para bitácora
            imagen_eliminada.send(
                sender=self.__class__,
                imagen=imagen,
                usuario=request.user,
                ip=self.get_client_ip(request)
            )
            imagen.delete()

            return Response(
                {'message': 'Imagen eliminada definitivamente (Cloudinary + BD)'},
                status=status.HTTP_204_NO_CONTENT
            )


        imagen.estado_imagen = 'INACTIVA'
        imagen.save(update_fields=['estado_imagen'])

        # Emitir señal para bitácora
        imagen_eliminada.send(
            sender=self.__class__,
            imagen=imagen,
            usuario=request.user,
            ip=self.get_client_ip(request)
        )

        return Response(
            {
                'message': 'Imagen marcada como inactiva (eliminación lógica)',
                'id_imagen': imagen.id_imagen,
                'estado': imagen.estado_imagen
            },
            status=status.HTTP_200_OK
        )
    
    @action(detail=True, methods=['post'])
    def restaurar(self, request, pk=None):
        """
        Restaurar una imagen marcada como inactiva.
        POST /api/imagenes/{id}/restaurar/
        """
        imagen = self.get_object()

        if imagen.estado_imagen == 'ACTIVA':
            return Response(
                {'detail': 'La imagen ya está activa.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        imagen.estado_imagen = 'ACTIVA'
        imagen.save(update_fields=['estado_imagen'])

        # Emitir señal para bitácora
        imagen_restaurada.send(
            sender=self.__class__,
            imagen=imagen,
            usuario=request.user,
            ip=self.get_client_ip(request)
        )

        return Response(
            {
                'message': 'Imagen restaurada correctamente',
                'id_imagen': imagen.id_imagen,
                'estado': imagen.estado_imagen
            },
            status=status.HTTP_200_OK
        )

    @action(detail=True, methods=['patch'])
    def actualizar(self, request, pk=None):
        """
        Actualiza metadatos de una imagen existente.
        PATCH /api/imagenes/{id}/actualizar/
        Campos permitidos: es_principal, orden
        """
        imagen = self.get_object()
        data = request.data
        cambios = {}

        campos_editables = ['es_principal', 'orden']

        # Detectar y aplicar cambios
        for campo in campos_editables:
            if campo in data:
                valor_anterior = getattr(imagen, campo)
                valor_nuevo = data[campo]
                if valor_anterior != valor_nuevo:
                    cambios[campo] = {'anterior': valor_anterior, 'nuevo': valor_nuevo}
                    setattr(imagen, campo, valor_nuevo)

        # Si es_principal=True, aplicar lógica para desmarcar las demás
        if data.get('es_principal', False):
            imagen.marcar_como_principal()

        imagen.save()

        # Emitir señal solo si hubo cambios
        if cambios:
            imagen_actualizada.send(
                sender=self.__class__,
                imagen=imagen,
                usuario=request.user,
                ip=self.get_client_ip(request),
                cambios=cambios
            )

        return Response({
            'message': 'Imagen actualizada correctamente',
            'cambios': cambios or 'Sin cambios detectados'
        })


    # ==========================================================
    # ACCIONES OPCIONALES (reordenar / batch)
    # ==========================================================

    @action(detail=False, methods=['post'], url_path='productos/(?P<producto_id>[^/.]+)/reordenar')
    def reordenar(self, request, producto_id=None):
        """
        Reordenar imágenes manualmente (sin colisiones de unique_together)
        POST /api/imagenes/productos/{id}/reordenar/
        Body:
        {
        "orden": [
            {"id_imagen": 10, "orden": 1},
            {"id_imagen": 11, "orden": 2},
            ...
        ]
        }
        """
        # 1) Validar producto
        producto = Producto.objects.filter(id_producto=producto_id).first()
        if not producto:
            return Response({'detail': 'Producto no encontrado'}, status=404)

        data = request.data.get('orden', [])
        if not isinstance(data, list) or not data:
            return Response(
                {'detail': 'Debe enviar una lista no vacía en "orden".'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2) Validaciones de payload
        try:
            ids = [int(item['id_imagen']) for item in data]
            nuevos_ordenes = [int(item['orden']) for item in data]
        except (KeyError, ValueError, TypeError):
            return Response(
                {'detail': 'Cada item debe tener "id_imagen" y "orden" enteros.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # No permitir orden <= 0
        if any(o <= 0 for o in nuevos_ordenes):
            return Response(
                {'detail': 'Todos los "orden" deben ser >= 1.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # No permitir repetidos en órdenes o ids
        if len(set(ids)) != len(ids):
            return Response({'detail': 'Hay id_imagen duplicados.'}, status=400)
        if len(set(nuevos_ordenes)) != len(nuevos_ordenes):
            return Response({'detail': 'Hay valores de "orden" duplicados.'}, status=400)

        # 3) Verificar pertenencia de imágenes al producto
        qs = ImagenProducto.objects.filter(id_producto=producto, id_imagen__in=ids)
        existentes = list(qs.values_list('id_imagen', flat=True))
        faltantes = set(ids) - set(existentes)
        if faltantes:
            return Response(
                {'detail': f'Las imágenes {sorted(list(faltantes))} no pertenecen al producto o no existen.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4) Actualización en dos fases para evitar colisiones:
        #    Fase A: desplazar orden temporalmente (orden + 1000)
        #    Fase B: asignar los nuevos órdenes con CASE WHEN
        mapping = {int(item['id_imagen']): int(item['orden']) for item in data}

        with transaction.atomic():
            # Fase A
            ImagenProducto.objects.filter(id_producto=producto, id_imagen__in=ids).update(
                orden=F('orden') + 1000
            )

            # Fase B - CASE WHEN
            cases = [When(id_imagen=iid, then=Value(new_o)) for iid, new_o in mapping.items()]
            ImagenProducto.objects.filter(id_producto=producto, id_imagen__in=ids).update(
                orden=Case(*cases, default=F('orden'), output_field=IntegerField())
            )

        # 5) Emitir señal de bitácora
        imagen_reordenada.send(
            sender=self.__class__,
            producto=producto,
            usuario=request.user,
            ip=self.get_client_ip(request),
            cantidad=len(ids)
        )

        # 6) Responder con el orden final
        actualizadas = ImagenProducto.objects.filter(id_producto=producto, id_imagen__in=ids).order_by('orden')
        payload = [
            {'id_imagen': img.id_imagen, 'orden': img.orden, 'es_principal': img.es_principal}
            for img in actualizadas
        ]
        return Response(
            {'message': 'Imágenes reordenadas correctamente', 'resultado': payload},
            status=status.HTTP_200_OK
        )
