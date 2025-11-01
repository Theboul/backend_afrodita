from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from django.db import transaction
import logging

from ..models import DireccionCliente, Cliente
from ..serializers.direccion_cliente import (
    DireccionClienteSerializer,
    DireccionClienteListSerializer,
)
from ..permissions import EsCliente
from core.constants import APIResponse, Messages
from apps.autenticacion.utils.helpers import obtener_ip_cliente

# Importar signals para auditoría
from apps.bitacora.signals import (
    direccion_creada,
    direccion_actualizada,
    direccion_eliminada,
    direccion_principal_cambiada
)

logger = logging.getLogger(__name__)

# =====================================================
# VIEWSET PARA DIRECCIONES DEL CLIENTE
# =====================================================
class DireccionClienteViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar las direcciones del cliente autenticado.
    
    Endpoints:
    - GET /api/usuarios/perfil/direcciones/ - Listar mis direcciones
    - POST /api/usuarios/perfil/direcciones/ - Crear nueva dirección
    - GET /api/usuarios/perfil/direcciones/{id}/ - Ver una dirección
    - PATCH /api/usuarios/perfil/direcciones/{id}/ - Editar dirección
    - DELETE /api/usuarios/perfil/direcciones/{id}/ - Eliminar dirección
    - POST /api/usuarios/perfil/direcciones/{id}/marcar-principal/ - Marcar como principal
    """
    permission_classes = [permissions.IsAuthenticated, EsCliente]
    
    def get_queryset(self):
        """
        Filtrar solo las direcciones del cliente autenticado.
        Automáticamente previene acceso a direcciones de otros clientes.
        """
        try:
            cliente = Cliente.objects.get(id_cliente=self.request.user)
            return DireccionCliente.objects.filter(id_cliente=cliente)
        except Cliente.DoesNotExist:
            return DireccionCliente.objects.none()
    
    def get_serializer_class(self):
        """Usar serializer simplificado para listar"""
        if self.action == 'list':
            return DireccionClienteListSerializer
        return DireccionClienteSerializer
    
    def list(self, request, *args, **kwargs):
        """
        GET /api/usuarios/perfil/direcciones/
        Lista todas las direcciones guardadas del cliente.
        """
        try:
            queryset = self.get_queryset().filter(guardada=True)
            serializer = self.get_serializer(queryset, many=True)
            
            return APIResponse.success(
                data={
                    'total': queryset.count(),
                    'direcciones': serializer.data
                },
                message=Messages.ADDRESSES_RETRIEVED
            )
            
        except Exception as e:
            logger.error(f"Error al listar direcciones: {str(e)}")
            return APIResponse.server_error(
                message=Messages.ERROR_FETCHING_ADDRESSES,
                detail=str(e)
            )
    
    def create(self, request, *args, **kwargs):
        """
        POST /api/usuarios/perfil/direcciones/
        Crea una nueva dirección para el cliente autenticado.
        """
        try:
            cliente = Cliente.objects.get(id_cliente=request.user)
            serializer = self.get_serializer(data=request.data)
            
            if serializer.is_valid():
                # Guardar con el cliente autenticado
                direccion = serializer.save(id_cliente=cliente)
                
                # Si es la primera dirección, marcarla como principal
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
                    es_admin=False
                )
                
                logger.info(
                    f"Dirección creada para cliente {cliente.id_cliente.nombre_usuario}"
                )
                
                return APIResponse.created(
                    data={'direccion': DireccionClienteSerializer(direccion).data},
                    message=Messages.ADDRESS_CREATED
                )
            
            return APIResponse.bad_request(
                message=Messages.INVALID_DATA,
                errors=serializer.errors
            )
            
        except Cliente.DoesNotExist:
            return APIResponse.not_found(message=Messages.CLIENT_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al crear dirección: {str(e)}")
            return APIResponse.server_error(
                message=Messages.ERROR_CREATING_ADDRESS,
                detail=str(e)
            )
    
    def retrieve(self, request, *args, **kwargs):
        """
        GET /api/usuarios/perfil/direcciones/{id}/
        Obtiene los detalles de una dirección específica.
        """
        try:
            direccion = self.get_object()
            serializer = self.get_serializer(direccion)
            
            return APIResponse.success(data={'direccion': serializer.data})
            
        except DireccionCliente.DoesNotExist:
            return APIResponse.not_found(message=Messages.ADDRESS_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al obtener dirección: {str(e)}")
            return APIResponse.server_error(
                message=Messages.SERVER_ERROR,
                detail=str(e)
            )
    
    def update(self, request, *args, **kwargs):
        """
        PUT/PATCH /api/usuarios/perfil/direcciones/{id}/
        Actualiza una dirección existente.
        """
        try:
            direccion = self.get_object()
            serializer = self.get_serializer(
                direccion, 
                data=request.data, 
                partial=kwargs.get('partial', False)
            )
            
            if serializer.is_valid():
                # Guardar datos anteriores para auditoría
                cambios = list(request.data.keys())
                
                direccion_actualizada = serializer.save()
                
                # DISPARAR SIGNAL para auditoría
                direccion_actualizada.send(
                    sender=self.__class__,
                    direccion=direccion_actualizada,
                    usuario=request.user,
                    ip=obtener_ip_cliente(request),
                    cambios=cambios,
                    es_admin=False
                )
                
                logger.info(f"Dirección {direccion.id_direccion} actualizada")
                
                return APIResponse.success(
                    data={'direccion': DireccionClienteSerializer(direccion_actualizada).data},
                    message=Messages.ADDRESS_UPDATED
                )
            
            return APIResponse.bad_request(
                message=Messages.INVALID_DATA,
                errors=serializer.errors
            )
            
        except DireccionCliente.DoesNotExist:
            return APIResponse.not_found(message=Messages.ADDRESS_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al actualizar dirección: {str(e)}")
            return APIResponse.server_error(
                message=Messages.ERROR_UPDATING_ADDRESS,
                detail=str(e)
            )
    
    def destroy(self, request, *args, **kwargs):
        """
        DELETE /api/usuarios/perfil/direcciones/{id}/
        Elimina (marca como no guardada) una dirección.
        """
        try:
            direccion = self.get_object()
            
            # Soft delete: marcar como no guardada en lugar de eliminar
            direccion.guardada = False
            direccion.save()
            
            # DISPARAR SIGNAL para auditoría
            direccion_eliminada.send(
                sender=self.__class__,
                direccion=direccion,
                usuario=request.user,
                ip=obtener_ip_cliente(request),
                es_admin=False
            )
            
            logger.info(f"Dirección {direccion.id_direccion} marcada como no guardada")
            
            return APIResponse.success(message=Messages.ADDRESS_DELETED)
            
        except DireccionCliente.DoesNotExist:
            return APIResponse.not_found(message=Messages.ADDRESS_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al eliminar dirección: {str(e)}")
            return APIResponse.server_error(
                message=Messages.ERROR_DELETING_ADDRESS,
                detail=str(e)
            )
    
    @action(detail=True, methods=['post'], url_path='marcar-principal')
    def marcar_principal(self, request, pk=None):
        """
        POST /api/usuarios/perfil/direcciones/{id}/marcar-principal/
        
        Marca una dirección como principal y desmarca las demás.
        Solo puede haber una dirección principal por cliente.
        """
        try:
            direccion = self.get_object()
            cliente = Cliente.objects.get(id_cliente=request.user)
            
            # Transaction atómica para evitar inconsistencias
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
                es_admin=False
            )
            
            logger.info(
                f"Dirección {direccion.id_direccion} marcada como principal "
                f"para cliente {cliente.id_cliente.nombre_usuario}"
            )
            
            return APIResponse.success(
                data={'direccion': DireccionClienteSerializer(direccion).data},
                message=Messages.ADDRESS_MARKED_PRINCIPAL
            )
            
        except DireccionCliente.DoesNotExist:
            return APIResponse.not_found(message=Messages.ADDRESS_NOT_FOUND)
        except Cliente.DoesNotExist:
            return APIResponse.not_found(message=Messages.CLIENT_NOT_FOUND)
        except Exception as e:
            logger.error(f"Error al marcar dirección como principal: {str(e)}")
            return APIResponse.server_error(
                message=Messages.ERROR_MARKING_PRINCIPAL,
                detail=str(e)
            )
