from rest_framework import viewsets, status
from rest_framework.decorators import action
from django.db import transaction
from django.db.models import Case, When, Value, IntegerField, F
from django.core.exceptions import ValidationError

from apps.productos.models import Producto
from apps.autenticacion.utils.helpers import obtener_ip_cliente
from core.constants import APIResponse, Messages, ImageStatus
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

    def get_queryset(self):
        producto_id = self.request.query_params.get('producto')
        qs = super().get_queryset().filter(estado_imagen=ImageStatus.ACTIVA)
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
            return APIResponse.not_found(message=Messages.PRODUCT_NOT_FOUND)

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
            ip=obtener_ip_cliente(request)
        )

        return APIResponse.created(
            data=ImagenProductoSerializer(imagen).data,
            message=Messages.IMAGE_UPLOADED
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
            ip=obtener_ip_cliente(request)
        )

        return APIResponse.success(
            data={
                'id_imagen': imagen.id_imagen,
                'producto': imagen.id_producto.id_producto,
            },
            message=Messages.IMAGE_MARKED_AS_PRINCIPAL
        )

    @action(detail=True, methods=['delete'])
    def eliminar(self, request, pk=None):
        """
        Eliminar imagen (lógica o física con ?force=true)
        DELETE /api/imagenes/{id}/eliminar/?force=true
        """
        imagen = self.get_object()

        if imagen.es_principal:
            return APIResponse.error(
                message=Messages.CANNOT_DELETE_PRINCIPAL_IMAGE,
                status_code=status.HTTP_409_CONFLICT
            )

        force_delete = request.query_params.get('force', 'false').lower() == 'true'

        if force_delete:
            imagen.eliminar_de_cloudinary()
            # Emitir señal para bitácora
            imagen_eliminada.send(
                sender=self.__class__,
                imagen=imagen,
                usuario=request.user,
                ip=obtener_ip_cliente(request)
            )
            imagen.delete()

            return APIResponse.success(
                message=Messages.IMAGE_DELETED_PERMANENTLY,
                status_code=status.HTTP_204_NO_CONTENT
            )

        imagen.estado_imagen = ImageStatus.INACTIVA
        imagen.save(update_fields=['estado_imagen'])

        # Emitir señal para bitácora
        imagen_eliminada.send(
            sender=self.__class__,
            imagen=imagen,
            usuario=request.user,
            ip=obtener_ip_cliente(request)
        )

        return APIResponse.success(
            data={
                'id_imagen': imagen.id_imagen,
                'estado': imagen.estado_imagen
            },
            message=Messages.IMAGE_DELETED_LOGICALLY
        )
    
    @action(detail=True, methods=['post'])
    def restaurar(self, request, pk=None):
        """
        Restaurar una imagen marcada como inactiva.
        POST /api/imagenes/{id}/restaurar/
        """
        imagen = self.get_object()

        if imagen.estado_imagen == ImageStatus.ACTIVA:
            return APIResponse.bad_request(
                message=Messages.IMAGE_ALREADY_ACTIVE
            )

        imagen.estado_imagen = ImageStatus.ACTIVA
        imagen.save(update_fields=['estado_imagen'])

        # Emitir señal para bitácora
        imagen_restaurada.send(
            sender=self.__class__,
            imagen=imagen,
            usuario=request.user,
            ip=obtener_ip_cliente(request)
        )

        return APIResponse.success(
            data={
                'id_imagen': imagen.id_imagen,
                'estado': imagen.estado_imagen
            },
            message=Messages.IMAGE_RESTORED
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
                ip=obtener_ip_cliente(request),
                cambios=cambios
            )

        return APIResponse.success(
            data={
                'cambios': cambios if cambios else Messages.NO_CHANGES_DETECTED
            },
            message=Messages.IMAGE_UPDATED
        )


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
            return APIResponse.not_found(message=Messages.PRODUCT_NOT_FOUND)

        data = request.data.get('orden', [])
        if not isinstance(data, list) or not data:
            return APIResponse.bad_request(
                message=Messages.INVALID_ORDER_LIST
            )

        # 2) Validaciones de payload
        try:
            ids = [int(item['id_imagen']) for item in data]
            nuevos_ordenes = [int(item['orden']) for item in data]
        except (KeyError, ValueError, TypeError):
            return APIResponse.bad_request(
                message=Messages.INVALID_ORDER_FORMAT
            )

        # No permitir orden <= 0
        if any(o <= 0 for o in nuevos_ordenes):
            return APIResponse.bad_request(
                message=Messages.ORDER_MUST_BE_POSITIVE
            )

        # No permitir repetidos en órdenes o ids
        if len(set(ids)) != len(ids):
            return APIResponse.bad_request(message=Messages.DUPLICATE_IMAGE_IDS)
        if len(set(nuevos_ordenes)) != len(nuevos_ordenes):
            return APIResponse.bad_request(message=Messages.DUPLICATE_ORDER_VALUES)

        # 3) Verificar pertenencia de imágenes al producto
        qs = ImagenProducto.objects.filter(id_producto=producto, id_imagen__in=ids)
        existentes = list(qs.values_list('id_imagen', flat=True))
        faltantes = set(ids) - set(existentes)
        if faltantes:
            return APIResponse.bad_request(
                message=Messages.IMAGES_NOT_BELONG_TO_PRODUCT.format(ids=sorted(list(faltantes)))
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
            ip=obtener_ip_cliente(request),
            cantidad=len(ids)
        )

        # 6) Responder con el orden final
        actualizadas = ImagenProducto.objects.filter(id_producto=producto, id_imagen__in=ids).order_by('orden')
        payload = [
            {'id_imagen': img.id_imagen, 'orden': img.orden, 'es_principal': img.es_principal}
            for img in actualizadas
        ]
        return APIResponse.success(
            data={'resultado': payload},
            message=Messages.IMAGE_REORDERED
        )
