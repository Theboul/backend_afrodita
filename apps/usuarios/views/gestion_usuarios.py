from rest_framework import viewsets, status, permissions
from rest_framework.response import Response
from rest_framework.decorators import action
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

# Importar para JWT
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

# Importar utilidades centralizadas
from apps.autenticacion.utils.helpers import obtener_ip_cliente

# Importar signals
from apps.bitacora.signals import (
    usuario_creado, usuario_actualizado, usuario_eliminado,
    usuario_estado_cambiado, usuario_password_cambiado, logout_forzado,
    token_invalidado,
    direccion_creada, direccion_actualizada, direccion_eliminada,
    direccion_principal_cambiada
)
import logging

from ..models import Usuario, Vendedor, Administrador, Cliente, DireccionCliente
from ..serializers.gestion_usuarios import (
    UsuarioAdminListSerializer,
    UsuarioAdminDetailSerializer,
    UsuarioAdminCreateSerializer,
    UsuarioAdminUpdateSerializer,
    CambiarContraseñaSerializer,
    CambiarEstadoSerializer,
    ForzarLogoutSerializer,
)
from ..serializers.direccion_cliente import DireccionClienteSerializer

# Importar constantes
from core.constants import UserStatus, APIResponse, Messages

logger = logging.getLogger(__name__)

# =====================================================
# PERMISOS PERSONALIZADOS
# =====================================================
class EsAdministradorPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and 
            request.user.id_rol and 
            request.user.id_rol.nombre == 'ADMINISTRADOR'
        )

# ====================================
# VIEWSET DE GESTIÓN ADMINISTRATIVA 
# ====================================
class UsuarioAdminViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated, EsAdministradorPermission]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ['id_rol__nombre', 'estado_usuario']
    search_fields = ['nombre_completo', 'nombre_usuario', 'correo']
    ordering_fields = ['fecha_registro', 'nombre_completo', 'last_login']
    ordering = ['-fecha_registro']

    def get_queryset(self):
        return Usuario.objects.select_related('id_rol').all()

    def get_serializer_class(self):
        if self.action == 'list':
            return UsuarioAdminListSerializer
        elif self.action == 'create':
            return UsuarioAdminCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return UsuarioAdminUpdateSerializer
        return UsuarioAdminDetailSerializer

    # =======================
    # MÉTODOS UTILITARIOS
    # =======================

    def _invalidar_tokens_usuario(self, usuario):
        """Invalida TODOS los tokens JWT del usuario"""
        try:
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken, BlacklistedToken
            
            tokens_activos = OutstandingToken.objects.filter(user=usuario)
            tokens_invalidados = 0
            
            for token in tokens_activos:
                try:
                    if not BlacklistedToken.objects.filter(token=token).exists():
                        BlacklistedToken.objects.create(token=token)
                        tokens_invalidados += 1
                        
                        # DISPARAR SIGNAL POR CADA TOKEN
                        token_invalidado.send(
                            sender=self.__class__,
                            token=str(token.token),
                            usuario=usuario
                        )
                        
                except Exception as e:
                    logger.warning(f"Error al invalidar token {token.id}: {str(e)}")
                    continue
            
            logger.info(f"Tokens invalidados para usuario {usuario.nombre_usuario}: {tokens_invalidados}")
            return tokens_invalidados
            
        except Exception as e:
            logger.error(f"Error crítico al invalidar tokens de {usuario.nombre_usuario}: {str(e)}")
            return 0

    # =======================
    # OPERACIONES CRUD 
    # =======================

    def create(self, request, *args, **kwargs):
        """Crear nuevo usuario"""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        usuario = serializer.save()
        
        # DISPARAR SIGNAL
        usuario_creado.send(
            sender=self.__class__,
            usuario_creado=usuario,
            usuario_ejecutor=request.user,
            ip=obtener_ip_cliente(request),
            datos_adicionales={
                'rol': usuario.id_rol.nombre if usuario.id_rol else 'Sin rol'
            }
        )
        
        return Response(
            {
                "id": usuario.id_usuario,
                "nombre_completo": usuario.nombre_completo,
                "nombre_usuario": usuario.nombre_usuario,
                "correo": usuario.correo,
                "telefono": usuario.telefono,
                "sexo": usuario.sexo,
                "fecha_registro": usuario.fecha_registro,
                "estado_usuario": usuario.estado_usuario,
                "rol": usuario.id_rol.nombre if usuario.id_rol else None,
                "message": Messages.USER_CREATED
            },
            status=status.HTTP_201_CREATED
        )

    def update(self, request, *args, **kwargs):
        """Actualizar usuario"""
        usuario = self.get_object()
        
        # Datos antes de la actualización
        datos_anteriores = {
            'nombre_completo': usuario.nombre_completo,
            'nombre_usuario': usuario.nombre_usuario,
            'correo': usuario.correo,
            'estado_usuario': usuario.estado_usuario,
            'rol': usuario.id_rol.nombre if usuario.id_rol else None
        }
        
        response = super().update(request, *args, **kwargs)
        
        # Obtener datos después de la actualización
        usuario.refresh_from_db()
        datos_nuevos = {
            'nombre_completo': usuario.nombre_completo,
            'nombre_usuario': usuario.nombre_usuario,
            'correo': usuario.correo,
            'estado_usuario': usuario.estado_usuario,
            'rol': usuario.id_rol.nombre if usuario.id_rol else None
        }
        
        # DISPARAR SIGNAL
        usuario_actualizado.send(
            sender=self.__class__,
            usuario_afectado=usuario,
            usuario_ejecutor=request.user,
            ip=obtener_ip_cliente(request),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )
        
        return response

    def destroy(self, request, *args, **kwargs):
        """Eliminar usuario (eliminación lógica)"""
        usuario = self.get_object()
        
        # Validaciones de seguridad
        if usuario.id_usuario == 1:
            return APIResponse.bad_request(
                message=Messages.CANNOT_DELETE_MAIN_ADMIN,
                errors={'code': 'cannot_delete_main_admin'}
            )
        
        if usuario.id_usuario == request.user.id_usuario:
            return APIResponse.bad_request(
                message=Messages.CANNOT_DELETE_SELF,
                errors={'code': 'cannot_delete_self'}
            )
        
        if self._tiene_ventas_activas(usuario):
            return APIResponse.error(
                message=Messages.USER_HAS_ACTIVE_SALES,
                status_code=409,
                code='user_has_active_sales',
                related_sales=self._contar_ventas_activas(usuario)
            )
        
        # Invalidar tokens antes de desactivar
        tokens_invalidados = 0
        if usuario.estado_usuario == UserStatus.ACTIVO:
            tokens_invalidados = self._invalidar_tokens_usuario(usuario)
        
        # Eliminación lógica
        usuario.estado_usuario = UserStatus.INACTIVO
        usuario.save()
        
        # DISPARAR SIGNAL
        usuario_eliminado.send(
            sender=self.__class__,
            usuario_afectado=usuario,
            usuario_ejecutor=request.user,
            ip=obtener_ip_cliente(request),
            motivo='Eliminación administrativa',
            tokens_invalidados=tokens_invalidados
        )
        
        return Response(status=status.HTTP_204_NO_CONTENT)
    

    # =======================
    # VERIFICACIONES EN TIEMPO REAL
    # =======================

    @action(detail=False, methods=['get'], url_path='verificar_username')
    def verificar_username(self, request):
        """Verificar disponibilidad de username"""
        username = request.GET.get('username')
        usuario_id = request.GET.get('usuario_id')
        
        if not username:
            return APIResponse.bad_request(
                message=Messages.FIELD_REQUIRED.format(field='username'),
                errors={'code': 'username_required'}
            )
        
        # Buscar si existe el username
        queryset = Usuario.objects.filter(nombre_usuario=username)
        
        # Si estamos editando un usuario, excluirlo de la verificación
        if usuario_id and usuario_id != 'undefined':
            try:
                queryset = queryset.exclude(id_usuario=int(usuario_id))
            except (ValueError, TypeError):
                pass
        
        existe = queryset.exists()
        
        return APIResponse.success(data={'disponible': not existe})

    @action(detail=False, methods=['get'], url_path='verificar_email')
    def verificar_email(self, request):
        """Verificar disponibilidad de email"""
        email = request.GET.get('email')
        usuario_id = request.GET.get('usuario_id')
        
        if not email:
            return APIResponse.bad_request(
                message=Messages.FIELD_REQUIRED.format(field='email'),
                errors={'code': 'email_required'}
            )
        
        # Buscar si existe el email
        queryset = Usuario.objects.filter(correo=email)
        
        # Si estamos editando un usuario, excluirlo de la verificación
        if usuario_id and usuario_id != 'undefined':
            try:
                queryset = queryset.exclude(id_usuario=int(usuario_id))
            except (ValueError, TypeError):
                pass
        
        existe = queryset.exists()
        
        return APIResponse.success(data={'disponible': not existe})

    # =======================
    # ACCIONES PERSONALIZADAS
    # =======================

    @action(detail=True, methods=['patch'])
    def cambiar_estado(self, request, pk=None):
        """Cambiar estado de usuario"""
        usuario = self.get_object()
        serializer = CambiarEstadoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        nuevo_estado = serializer.validated_data['estado_usuario']
        motivo = serializer.validated_data.get('motivo', 'Sin motivo especificado')
        estado_anterior = usuario.estado_usuario
        
        # Si cambia de ACTIVO a INACTIVO, invalidar tokens
        tokens_invalidados = 0
        if nuevo_estado == UserStatus.INACTIVO and usuario.estado_usuario == UserStatus.ACTIVO:
            tokens_invalidados = self._invalidar_tokens_usuario(usuario)
        
        usuario.estado_usuario = nuevo_estado
        usuario.save()
        
        # DISPARAR SIGNAL
        usuario_estado_cambiado.send(
            sender=self.__class__,
            usuario_afectado=usuario,
            usuario_ejecutor=request.user,
            ip=obtener_ip_cliente(request),
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            motivo=motivo
        )
        
        return APIResponse.success(
            data={
                "id": usuario.id_usuario,
                "estado_usuario": usuario.estado_usuario
            },
            message=Messages.USER_STATUS_CHANGED
        )

    @action(detail=True, methods=['post'])
    def cambiar_contrasena(self, request, pk=None):
        """Cambiar contraseña de usuario"""
        usuario = self.get_object()
        serializer = CambiarContraseñaSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        nueva_contrasena = serializer.validated_data['nueva_contrasena']
        usuario.set_password(nueva_contrasena)
        usuario.save()
        
        # DISPARAR SIGNAL
        usuario_password_cambiado.send(
            sender=self.__class__,
            usuario_afectado=usuario,
            usuario_ejecutor=request.user,
            ip=obtener_ip_cliente(request)
        )
        
        return APIResponse.success(message=Messages.PASSWORD_CHANGED)

    @action(detail=True, methods=['post'])
    def forzar_logout(self, request, pk=None):
        """Forzar logout en todos los dispositivos"""
        usuario = self.get_object()
        serializer = ForzarLogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        motivo = serializer.validated_data.get('motivo', 'Sin motivo especificado')
        
        if usuario.estado_usuario != UserStatus.ACTIVO:
            return APIResponse.bad_request(
                message=Messages.CANNOT_LOGOUT_INACTIVE_USER,
                errors={'code': 'user_inactive'}
            )
        
        tokens_invalidados = self._invalidar_tokens_usuario(usuario)
        
        # DISPARAR SIGNAL
        logout_forzado.send(
            sender=self.__class__,
            usuario_afectado=usuario,
            usuario_ejecutor=request.user,
            ip=obtener_ip_cliente(request),
            motivo=motivo,
            tokens_invalidados=tokens_invalidados
        )
        
        return APIResponse.success(
            data={
                "tokens_invalidados": tokens_invalidados,
                "usuario": usuario.nombre_usuario
            },
            message=Messages.LOGOUT_FORCED
        )

    # =======================
    # MÉTODOS DE VALIDACIÓN
    # =======================

    def _tiene_ventas_activas(self, usuario):
        """Verificar si el usuario tiene ventas activas"""
        try:
            # from apps.ventas.models import Venta
            # return Venta.objects.filter(
            #     id_vendedor=usuario, 
            #     estado__in=['PENDIENTE', 'PROCESANDO', 'ENVIADO']
            # ).exists()
            return False
        except Exception as e:
            logger.error(f"Error al verificar ventas activas: {str(e)}")
            return False

    def _contar_ventas_activas(self, usuario):
        """Contar ventas activas del usuario"""
        try:
            # from apps.ventas.models import Venta
            # return Venta.objects.filter(
            #     id_vendedor=usuario, 
            #     estado__in=['PENDIENTE', 'PROCESANDO', 'ENVIADO']
            # ).count()
            return 0
        except Exception as e:
            logger.error(f"Error al contar ventas activas: {str(e)}")
            return 0

    # =======================
    # ESTADÍSTICAS
    # =======================
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """Estadísticas de usuarios"""
        total_usuarios = Usuario.objects.count()
        
        por_rol = Usuario.objects.values('id_rol__nombre').annotate(
            count=Count('id_usuario')
        ).order_by('id_rol__nombre')
        
        por_rol_dict = {
            item['id_rol__nombre']: item['count'] 
            for item in por_rol 
            if item['id_rol__nombre']
        }
        
        por_estado = Usuario.objects.values('estado_usuario').annotate(
            count=Count('id_usuario')
        ).order_by('estado_usuario')
        
        por_estado_dict = {
            item['estado_usuario']: item['count'] 
            for item in por_estado
        }
        
        fecha_limite = timezone.now() - timedelta(days=30)
        nuevos_ultimos_30_dias = Usuario.objects.filter(
            fecha_registro__gte=fecha_limite
        ).count()
        
        hoy = timezone.now().date()
        usuarios_activos_hoy = Usuario.objects.filter(
            last_login__date=hoy
        ).count()
        
        return APIResponse.success(data={
            "total_usuarios": total_usuarios,
            "por_rol": por_rol_dict,
            "por_estado": por_estado_dict,
            "nuevos_ultimos_30_dias": nuevos_ultimos_30_dias,
            "usuarios_activos_hoy": usuarios_activos_hoy
        })
    
    #-----------------------------
    # GESTIÓN DE DIRECCIONES DE CLIENTES (ADMIN)
    #-----------------------------
    
    @action(detail=True, methods=['get', 'post'], url_path='direcciones')
    def gestionar_direcciones(self, request, pk=None):
        """
        GET /api/usuarios/admin/usuarios/{id}/direcciones/
        POST /api/usuarios/admin/usuarios/{id}/direcciones/
        
        Obtiene todas las direcciones de un cliente (GET) o crea una nueva (POST).
        Solo administradores pueden acceder.
        """
        usuario = self.get_object()
        
        # Verificar que sea un cliente
        if not usuario.id_rol or usuario.id_rol.nombre != 'CLIENTE':
            return APIResponse.bad_request(
                message=Messages.ONLY_CLIENTS_HAVE_ADDRESSES
            )
        
        # Obtener el cliente
        try:
            cliente = Cliente.objects.get(id_cliente=usuario)
        except Cliente.DoesNotExist:
            return APIResponse.not_found(
                message=Messages.CLIENT_NOT_FOUND
            )
        
        # ==================== GET: Listar direcciones ====================
        if request.method == 'GET':
            try:
                # Obtener todas las direcciones (incluso las no guardadas para el admin)
                mostrar_todas = request.query_params.get('todas', 'false').lower() == 'true'
                
                if mostrar_todas:
                    direcciones = DireccionCliente.objects.filter(id_cliente=cliente)
                else:
                    direcciones = DireccionCliente.objects.filter(id_cliente=cliente, guardada=True)
                
                direcciones = direcciones.order_by('-es_principal', '-fecha_creacion')
                
                serializer = DireccionClienteSerializer(direcciones, many=True)
                
                logger.info(
                    f"Admin {request.user.nombre_usuario} consultó direcciones "
                    f"del cliente {usuario.nombre_usuario}"
                )
                
                return APIResponse.success(
                    message=Messages.ADDRESSES_RETRIEVED,
                    data={
                        'total': direcciones.count(),
                        'cliente': {
                            'id_usuario': usuario.id_usuario,
                            'nombre_completo': usuario.nombre_completo,
                            'correo': usuario.correo
                        },
                        'direcciones': serializer.data
                    }
                )
                
            except Exception as e:
                logger.error(f"Error al obtener direcciones: {str(e)}")
                return APIResponse.server_error(
                    message=Messages.ERROR_FETCHING_ADDRESSES,
                    detail=str(e)
                )
        
        # ==================== POST: Crear dirección ====================
        elif request.method == 'POST':
            try:
                # Validar y crear la dirección
                serializer = DireccionClienteSerializer(data=request.data)
                
                if serializer.is_valid():
                    # Guardar con el cliente especificado
                    direccion = serializer.save(id_cliente=cliente)
                    
                    # Si es la primera dirección, marcarla como principal automáticamente
                    if not DireccionCliente.objects.filter(
                        id_cliente=cliente, es_principal=True
                    ).exclude(id_direccion=direccion.id_direccion).exists():
                        direccion.es_principal = True
                        direccion.save()
                    
                    # DISPARAR SIGNAL para auditoría
                    direccion_creada.send(
                        sender=self.__class__,
                        direccion=direccion,
                        usuario=request.user,
                        ip=obtener_ip_cliente(request),
                        es_admin=True
                    )
                    
                    logger.info(
                        f"Admin {request.user.nombre_usuario} creó dirección "
                        f"para cliente {usuario.nombre_usuario}"
                    )
                    
                    return APIResponse.created(
                        message=Messages.ADDRESS_CREATED,
                        data={'direccion': DireccionClienteSerializer(direccion).data}
                    )
                
                return APIResponse.bad_request(
                    message=Messages.INVALID_DATA,
                    errors=serializer.errors
                )
                
            except Exception as e:
                logger.error(f"Error al crear dirección: {str(e)}")
                return APIResponse.server_error(
                    message=Messages.ERROR_CREATING_ADDRESS,
                    detail=str(e)
                )

    @action(detail=True, methods=['patch', 'delete'], url_path='direcciones/(?P<dir_id>[^/.]+)')
    def gestionar_direccion_individual(self, request, pk=None, dir_id=None):
        """
        PATCH /api/usuarios/admin/usuarios/{id}/direcciones/{dir_id}/
        DELETE /api/usuarios/admin/usuarios/{id}/direcciones/{dir_id}/
        
        Edita o elimina una dirección específica de un cliente.
        Solo administradores pueden acceder.
        """
        usuario = self.get_object()
        
        # Verificar que sea un cliente
        if not usuario.id_rol or usuario.id_rol.nombre != 'CLIENTE':
            return APIResponse.bad_request(
                message=Messages.NOT_A_CLIENT
            )
        
        # Obtener el cliente
        try:
            cliente = Cliente.objects.get(id_cliente=usuario)
        except Cliente.DoesNotExist:
            return APIResponse.not_found(
                message=Messages.CLIENT_NOT_FOUND
            )
        
        # Obtener la dirección y verificar que pertenezca al cliente
        try:
            direccion = DireccionCliente.objects.get(
                id_direccion=dir_id,
                id_cliente=cliente
            )
        except DireccionCliente.DoesNotExist:
            return APIResponse.not_found(
                message=Messages.ADDRESS_NOT_BELONGS
            )
        
        # ==================== PATCH: Editar dirección ====================
        if request.method == 'PATCH':
            try:
                # Actualizar la dirección
                serializer = DireccionClienteSerializer(
                    direccion, 
                    data=request.data, 
                    partial=True
                )
                
                if serializer.is_valid():
                    # Guardar datos de cambios para auditoría
                    cambios = list(request.data.keys())
                    
                    direccion_actualizada = serializer.save()
                    
                    # DISPARAR SIGNAL para auditoría
                    direccion_actualizada.send(
                        sender=self.__class__,
                        direccion=direccion_actualizada,
                        usuario=request.user,
                        ip=obtener_ip_cliente(request),
                        cambios=cambios,
                        es_admin=True
                    )
                    
                    logger.info(
                        f"Admin {request.user.nombre_usuario} editó dirección {dir_id} "
                        f"del cliente {usuario.nombre_usuario}"
                    )
                    
                    return APIResponse.success(
                        message=Messages.ADDRESS_UPDATED,
                        data={'direccion': DireccionClienteSerializer(direccion_actualizada).data}
                    )
                
                return APIResponse.bad_request(
                    message=Messages.INVALID_DATA,
                    errors=serializer.errors
                )
                
            except Exception as e:
                logger.error(f"Error al editar dirección: {str(e)}")
                return APIResponse.server_error(
                    message=Messages.ERROR_UPDATING_ADDRESS,
                    detail=str(e)
                )
        
        # ==================== DELETE: Eliminar dirección ====================
        elif request.method == 'DELETE':
            try:
                # Soft delete: marcar como no guardada
                direccion.guardada = False
                direccion.save()
                
                # DISPARAR SIGNAL para auditoría
                direccion_eliminada.send(
                    sender=self.__class__,
                    direccion=direccion,
                    usuario=request.user,
                    ip=obtener_ip_cliente(request),
                    es_admin=True
                )
                
                logger.info(
                    f"Admin {request.user.nombre_usuario} eliminó dirección {dir_id} "
                    f"del cliente {usuario.nombre_usuario}"
                )
                
                return APIResponse.success(
                    message=Messages.ADDRESS_DELETED
                )
                
            except Exception as e:
                logger.error(f"Error al eliminar dirección: {str(e)}")
                return APIResponse.server_error(
                    message=Messages.ERROR_DELETING_ADDRESS,
                    detail=str(e)
                )
    
    @action(
        detail=True, 
        methods=['post'], 
        url_path='direcciones/(?P<dir_id>[^/.]+)/marcar-principal'
    )
    def marcar_direccion_principal(self, request, pk=None, dir_id=None):
        """
        POST /api/usuarios/admin/usuarios/{id}/direcciones/{dir_id}/marcar-principal/
        
        Marca una dirección como principal y desmarca las demás.
        Solo administradores pueden acceder.
        """
        try:
            usuario = self.get_object()
            
            # Verificar que sea un cliente
            if not usuario.id_rol or usuario.id_rol.nombre != 'CLIENTE':
                return APIResponse.bad_request(
                    message=Messages.NOT_A_CLIENT
                )
            
            # Obtener el cliente
            try:
                cliente = Cliente.objects.get(id_cliente=usuario)
            except Cliente.DoesNotExist:
                return APIResponse.not_found(
                    message=Messages.CLIENT_NOT_FOUND
                )
            
            # Obtener la dirección
            try:
                direccion = DireccionCliente.objects.get(
                    id_direccion=dir_id,
                    id_cliente=cliente
                )
            except DireccionCliente.DoesNotExist:
                return APIResponse.not_found(
                    message=Messages.ADDRESS_NOT_BELONGS
                )
            
            # Transaction atómica
            from django.db import transaction
            with transaction.atomic():
                # Desmarcar todas las direcciones del cliente
                DireccionCliente.objects.filter(
                    id_cliente=cliente,
                    es_principal=True
                ).update(es_principal=False)
                
                # Marcar esta como principal
                direccion.es_principal = True
                direccion.save()
            
            # DISPARAR SIGNAL para auditoría
            direccion_principal_cambiada.send(
                sender=self.__class__,
                direccion=direccion,
                usuario=request.user,
                ip=obtener_ip_cliente(request),
                es_admin=True
            )
            
            logger.info(
                f"Admin {request.user.nombre_usuario} marcó dirección {dir_id} como principal "
                f"para cliente {usuario.nombre_usuario}"
            )
            
            return APIResponse.success(
                message=Messages.ADDRESS_MARKED_PRINCIPAL,
                data={'direccion': DireccionClienteSerializer(direccion).data}
            )
            
        except Exception as e:
            logger.error(f"Error al marcar dirección como principal: {str(e)}")
            return APIResponse.server_error(
                message=Messages.ERROR_MARKING_PRINCIPAL,
                detail=str(e)
            )
        
    @action(detail=True, methods=['get'], url_path='compras')
    def listar_compras_cliente(self, request, pk=None):
        """
        GET /api/usuarios/admin/usuarios/{id}/compras/

        Lista todas las compras (ventas) asociadas a un cliente.
        """
        from apps.ventas.models import Venta
        from apps.ventas.serializers import VentaSerializer

        # Obtener el usuario
        usuario = self.get_object()

        # Validar que sea cliente
        if not usuario.id_rol or usuario.id_rol.nombre != 'CLIENTE':
            return APIResponse.bad_request(
                message="Solo los clientes tienen historial de compras."
            )

        # Obtener el objeto Cliente (tabla clientes)
        try:
            cliente = Cliente.objects.get(id_cliente=usuario.id_usuario)
        except Cliente.DoesNotExist:
            return APIResponse.not_found(
                message="El cliente no existe."
            )

        # Obtener ventas
        ventas = Venta.objects.filter(id_cliente=cliente).order_by('-id_venta')

        serializer = VentaSerializer(ventas, many=True)

        return APIResponse.success(
            message="Compras obtenidas correctamente.",
            data=serializer.data
        )
