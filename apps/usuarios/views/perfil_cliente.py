from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from django.db import transaction
import logging

from ..models import Usuario, Cliente
from ..serializers.perfil_cliente import (
    PerfilClienteSerializer,
    PerfilClienteUpdateSerializer,
    CambiarPasswordClienteSerializer,
)
from ..permissions import EsCliente
from core.constants import APIResponse, Messages
from apps.autenticacion.utils.helpers import obtener_ip_cliente

# Importar signals para auditoría
from apps.bitacora.signals import usuario_actualizado, usuario_password_cambiado

logger = logging.getLogger(__name__)

# =====================================================
# VIEWSET PARA PERFIL DEL CLIENTE
# =====================================================
class PerfilClienteViewSet(viewsets.ViewSet):
    """
    ViewSet para que el cliente gestione su propio perfil.
    
    Endpoints:
    - GET /api/usuarios/perfil/me/ - Ver mi perfil
    - PATCH /api/usuarios/perfil/actualizar/ - Actualizar mi perfil
    - POST /api/usuarios/perfil/cambiar-password/ - Cambiar mi contraseña
    """
    permission_classes = [permissions.IsAuthenticated, EsCliente]
    
    @action(detail=False, methods=['get'], url_path='me')
    def obtener_perfil(self, request):
        """
        GET /api/usuarios/perfil/me/
        
        Obtiene el perfil completo del cliente autenticado.
        Incluye: datos personales, dirección principal, estadísticas.
        """
        try:
            usuario = request.user
            serializer = PerfilClienteSerializer(usuario)
            
            return APIResponse.success(
                data={'perfil': serializer.data},
                message=Messages.PROFILE_RETRIEVED
            )
            
        except Exception as e:
            logger.error(f"Error al obtener perfil: {str(e)}")
            return APIResponse.server_error(
                message=Messages.SERVER_ERROR,
                detail=str(e)
            )
    
    @action(detail=False, methods=['patch'])
    def actualizar(self, request):
        """
        PATCH /api/usuarios/perfil/actualizar/
        
        Actualiza los datos del perfil del cliente.
        Campos permitidos: nombre_completo, telefono, correo, sexo
        """
        try:
            usuario = request.user
            serializer = PerfilClienteUpdateSerializer(
                usuario, 
                data=request.data, 
                partial=True
            )
            
            if serializer.is_valid():
                # Guardar cambios
                usuario_actualizado_obj = serializer.save()
                
                # Registrar en bitácora
                usuario_actualizado.send(
                    sender=self.__class__,
                    usuario=usuario_actualizado_obj,
                    campos_modificados=list(request.data.keys()),
                    modificado_por=usuario,
                    ip=obtener_ip_cliente(request)
                )
                
                logger.info(f"Perfil actualizado: {usuario.nombre_usuario}")
                
                return APIResponse.success(
                    data={'perfil': PerfilClienteSerializer(usuario_actualizado_obj).data},
                    message=Messages.PROFILE_UPDATED
                )
            
            return APIResponse.bad_request(
                message=Messages.INVALID_DATA,
                errors=serializer.errors
            )
            
        except Exception as e:
            logger.error(f"Error al actualizar perfil: {str(e)}")
            return APIResponse.server_error(
                message=Messages.SERVER_ERROR,
                detail=str(e)
            )
    
    @action(detail=False, methods=['post'], url_path='cambiar-password')
    def cambiar_password(self, request):
        """
        POST /api/usuarios/perfil/cambiar-password/
        
        Cambia la contraseña del cliente.
        Requiere: contraseña_actual, contraseña_nueva, confirmar_contraseña
        """
        try:
            serializer = CambiarPasswordClienteSerializer(data=request.data)
            
            if serializer.is_valid():
                usuario = request.user
                
                # Verificar contraseña actual
                if not usuario.check_password(
                    serializer.validated_data['contraseña_actual']
                ):
                    return APIResponse.bad_request(
                        message='La contraseña actual es incorrecta.',
                        errors={'contraseña_actual': 'Contraseña incorrecta'}
                    )
                
                # Cambiar contraseña
                with transaction.atomic():
                    usuario.set_password(
                        serializer.validated_data['contraseña_nueva']
                    )
                    usuario.save()
                    
                    # Registrar en bitácora
                    usuario_password_cambiado.send(
                        sender=self.__class__,
                        usuario=usuario,
                        cambiado_por=usuario,
                        ip=obtener_ip_cliente(request)
                    )
                
                logger.info(f"Contraseña cambiada: {usuario.nombre_usuario}")
                
                return APIResponse.success(message=Messages.PASSWORD_CHANGED)
            
            return APIResponse.bad_request(
                message=Messages.INVALID_DATA,
                errors=serializer.errors
            )
            
        except Exception as e:
            logger.error(f"Error al cambiar contraseña: {str(e)}")
            return APIResponse.server_error(
                message=Messages.SERVER_ERROR,
                detail=str(e)
            )
    
    @action(detail=False, methods=['get'])
    def estadisticas(self, request):
        """
        GET /api/usuarios/perfil/estadisticas/
        
        Obtiene estadísticas del cliente (para dashboard).
        Incluye: total compras, total gastado, direcciones, etc.
        """
        try:
            usuario = request.user
            cliente = Cliente.objects.get(id_cliente=usuario)
            
            # Por ahora estadísticas básicas
            # Cuando implementes ventas, agregar más datos
            estadisticas = {
                'total_direcciones': cliente.direcciones.filter(guardada=True).count(),
                'tiene_direccion_principal': cliente.direcciones.filter(
                    es_principal=True
                ).exists(),
                'fecha_registro': usuario.fecha_registro,
                'ultimo_login': usuario.last_login,
                # TODO: Agregar cuando exista modelo Venta
                # 'total_compras': Venta.objects.filter(id_cliente=cliente).count(),
                # 'total_gastado': ...
            }
            
            return APIResponse.success(
                data={'estadisticas': estadisticas},
                message=Messages.STATISTICS_RETRIEVED
            )
            
        except Cliente.DoesNotExist:
            return APIResponse.not_found(message=Messages.CLIENT_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al obtener estadísticas: {str(e)}")
            return APIResponse.server_error(
                message=Messages.SERVER_ERROR,
                detail=str(e)
            )
