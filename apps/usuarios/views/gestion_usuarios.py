from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta

# Importar para JWT
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

# Importar signals
from apps.bitacora.signals import (
    usuario_creado, usuario_actualizado, usuario_eliminado,
    usuario_estado_cambiado, usuario_password_cambiado, logout_forzado,
    token_invalidado
)
import logging

from ..models import Usuario, Vendedor, Administrador, Cliente
from ..serializers.gestion_usuarios import (
    UsuarioAdminListSerializer,
    UsuarioAdminDetailSerializer,
    UsuarioAdminCreateSerializer,
    UsuarioAdminUpdateSerializer,
    CambiarContraseñaSerializer,
    CambiarEstadoSerializer,
    ForzarLogoutSerializer,
)

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

    def _obtener_ip_request(self, request):
        """Obtiene la IP real del cliente"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip

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
            ip=self._obtener_ip_request(request),
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
                "message": "Usuario creado exitosamente"
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
            ip=self._obtener_ip_request(request),
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos
        )
        
        return response

    def destroy(self, request, *args, **kwargs):
        """Eliminar usuario (eliminación lógica)"""
        usuario = self.get_object()
        
        # Validaciones de seguridad
        if usuario.id_usuario == 1:
            return Response(
                {"detail": "No se puede eliminar al administrador principal", "code": "cannot_delete_main_admin"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if usuario.id_usuario == request.user.id_usuario:
            return Response(
                {"detail": "No puede eliminar su propio usuario", "code": "cannot_delete_self"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if self._tiene_ventas_activas(usuario):
            return Response(
                {
                    "detail": "No se puede eliminar usuario con ventas activas",
                    "code": "user_has_active_sales",
                    "related_sales": self._contar_ventas_activas(usuario)
                },
                status=status.HTTP_409_CONFLICT
            )
        
        # Invalidar tokens antes de desactivar
        tokens_invalidados = 0
        if usuario.estado_usuario == 'ACTIVO':
            tokens_invalidados = self._invalidar_tokens_usuario(usuario)
        
        # Eliminación lógica
        usuario.estado_usuario = 'INACTIVO'
        usuario.save()
        
        # DISPARAR SIGNAL
        usuario_eliminado.send(
            sender=self.__class__,
            usuario_afectado=usuario,
            usuario_ejecutor=request.user,
            ip=self._obtener_ip_request(request),
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
            return Response({'error': 'Username parameter required'}, status=400)
        
        # Buscar si existe el username
        queryset = Usuario.objects.filter(nombre_usuario=username)
        
        # Si estamos editando un usuario, excluirlo de la verificación
        if usuario_id and usuario_id != 'undefined':
            try:
                queryset = queryset.exclude(id_usuario=int(usuario_id))
            except (ValueError, TypeError):
                pass
        
        existe = queryset.exists()
        
        return Response({'disponible': not existe})

    @action(detail=False, methods=['get'], url_path='verificar_email')
    def verificar_email(self, request):
        """Verificar disponibilidad de email"""
        email = request.GET.get('email')
        usuario_id = request.GET.get('usuario_id')
        
        if not email:
            return Response({'error': 'Email parameter required'}, status=400)
        
        # Buscar si existe el email
        queryset = Usuario.objects.filter(correo=email)
        
        # Si estamos editando un usuario, excluirlo de la verificación
        if usuario_id and usuario_id != 'undefined':
            try:
                queryset = queryset.exclude(id_usuario=int(usuario_id))
            except (ValueError, TypeError):
                pass
        
        existe = queryset.exists()
        
        return Response({'disponible': not existe})

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
        if nuevo_estado == 'INACTIVO' and usuario.estado_usuario == 'ACTIVO':
            tokens_invalidados = self._invalidar_tokens_usuario(usuario)
        
        usuario.estado_usuario = nuevo_estado
        usuario.save()
        
        # DISPARAR SIGNAL
        usuario_estado_cambiado.send(
            sender=self.__class__,
            usuario_afectado=usuario,
            usuario_ejecutor=request.user,
            ip=self._obtener_ip_request(request),
            estado_anterior=estado_anterior,
            estado_nuevo=nuevo_estado,
            motivo=motivo
        )
        
        return Response({
            "id": usuario.id_usuario,
            "estado_usuario": usuario.estado_usuario,
            "message": "Estado actualizado correctamente"
        })

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
            ip=self._obtener_ip_request(request)
        )
        
        return Response({
            "message": "Contraseña actualizada exitosamente"
        })

    @action(detail=True, methods=['post'])
    def forzar_logout(self, request, pk=None):
        """Forzar logout en todos los dispositivos"""
        usuario = self.get_object()
        serializer = ForzarLogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        motivo = serializer.validated_data.get('motivo', 'Sin motivo especificado')
        
        if usuario.estado_usuario != 'ACTIVO':
            return Response({
                "detail": "No se puede forzar logout de usuario inactivo",
                "code": "user_inactive"
            }, status=status.HTTP_400_BAD_REQUEST)
        
        tokens_invalidados = self._invalidar_tokens_usuario(usuario)
        
        # DISPARAR SIGNAL
        logout_forzado.send(
            sender=self.__class__,
            usuario_afectado=usuario,
            usuario_ejecutor=request.user,
            ip=self._obtener_ip_request(request),
            motivo=motivo,
            tokens_invalidados=tokens_invalidados
        )
        
        return Response({
            "message": f"Logout forzado exitosamente",
            "tokens_invalidados": tokens_invalidados,
            "usuario": usuario.nombre_usuario
        })

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
        
        return Response({
            "total_usuarios": total_usuarios,
            "por_rol": por_rol_dict,
            "por_estado": por_estado_dict,
            "nuevos_ultimos_30_dias": nuevos_ultimos_30_dias,
            "usuarios_activos_hoy": usuarios_activos_hoy
        })