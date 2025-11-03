"""
Views para el módulo de soporte/tickets (CU25).

Gestiona la creación, respuesta y cierre de tickets de soporte,
manteniendo el historial completo de comunicación.
"""

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Count
from .models import Ticket, MensajeTicket
from .serializers import (
    TicketSerializer,
    TicketListSerializer,
    CrearTicketSerializer,
    MensajeTicketSerializer,
    ResponderTicketSerializer,
    CambiarEstadoSerializer
)
from core.constants import APIResponse, Messages, TicketStatus
from apps.bitacora.signals import (
    ticket_creado,
    ticket_respondido,
    ticket_cerrado,
    ticket_reabierto
)
from apps.bitacora.middleware import obtener_ip_cliente


# =====================================================
# VIEWSET DE TICKETS
# =====================================================

class TicketViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar tickets de soporte.
    
    Operaciones:
    - list: Listar tickets (clientes ven solo los suyos, admin/vendedor ven todos)
    - retrieve: Ver detalle de un ticket con todos sus mensajes
    - create: Crear nuevo ticket (solo clientes)
    - responder: Agente responde un ticket
    - mensaje_cliente: Cliente responde su ticket
    - cerrar: Agente cierra un ticket
    - reabrir: Reabrir un ticket cerrado
    """
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filtrar tickets según el rol del usuario"""
        user = self.request.user
        queryset = Ticket.objects.select_related(
            'id_cliente',
            'id_agente_asignado'
        ).prefetch_related('mensajes')
        
        # Cliente: solo ve sus tickets
        if user.id_rol and user.id_rol.nombre == 'CLIENTE':
            queryset = queryset.filter(id_cliente=user)
        
        # Admin/Vendedor puede filtrar por cliente específico
        # Soporta tanto 'cliente_id' como 'id_cliente'
        cliente_id = self.request.query_params.get('cliente_id') or self.request.query_params.get('id_cliente')
        if cliente_id and user.id_rol and user.id_rol.nombre in ['ADMINISTRADOR', 'VENDEDOR']:
            queryset = queryset.filter(id_cliente__id_usuario=cliente_id)
        
        # Filtros opcionales
        estado = self.request.query_params.get('estado', None)
        if estado and TicketStatus.is_valid(estado):
            queryset = queryset.filter(estado=estado)
        
        tipo = self.request.query_params.get('tipo', None)
        if tipo:
            queryset = queryset.filter(tipo_consulta=tipo)
        
        # Búsqueda
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(asunto__icontains=search) |
                Q(mensaje__icontains=search) |
                Q(id_ticket__icontains=search)
            )
        
        return queryset.order_by('-fecha_creacion')
    
    def get_serializer_class(self):
        """Usar serializer apropiado según la acción"""
        if self.action == 'create':
            return CrearTicketSerializer
        elif self.action == 'list':
            return TicketListSerializer
        return TicketSerializer
    
    def create(self, request, *args, **kwargs):
        """Crear nuevo ticket de soporte"""
        # Validar que sea cliente
        if not request.user.id_rol or request.user.id_rol.nombre != 'CLIENTE':
            return APIResponse.forbidden(
                message='Solo los clientes pueden crear tickets de soporte.'
            )
        
        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.bad_request(
                message=Messages.INVALID_DATA,
                errors=serializer.errors
            )
        
        # Crear ticket
        ticket = serializer.save(
            id_cliente=request.user,
            estado=TicketStatus.PENDIENTE
        )
        
        # Crear primer mensaje con el contenido del ticket
        MensajeTicket.objects.create(
            ticket=ticket,
            id_usuario=request.user,
            mensaje=ticket.mensaje,
            es_respuesta_agente=False
        )
        
        # Disparar señal de ticket creado
        ticket_creado.send(
            sender=Ticket,
            ticket=ticket,
            usuario=request.user,
            ip=obtener_ip_cliente(request)
        )
        
        return APIResponse.created(
            data=TicketSerializer(ticket).data,
            message=f'Ticket #{ticket.id_ticket} creado exitosamente.'
        )
    
    def retrieve(self, request, *args, **kwargs):
        """Obtener detalle de un ticket"""
        instance = self.get_object()
        
        # Validar permisos: cliente solo ve sus tickets
        if request.user.id_rol and request.user.id_rol.nombre == 'CLIENTE':
            if instance.id_cliente != request.user:
                return APIResponse.forbidden(
                    message='No tienes permiso para ver este ticket.'
                )
        
        serializer = self.get_serializer(instance)
        return APIResponse.success(
            data=serializer.data,
            message='Ticket obtenido exitosamente.'
        )
    
    @action(detail=False, methods=['get'], url_path='mis-tickets')
    def mis_tickets(self, request):
        """
        Endpoint personalizado para que el cliente vea SOLO sus tickets.
        GET /api/soporte/tickets/mis-tickets/
        
        Soporta filtros:
        - ?estado=PENDIENTE|EN_PROCESO|RESPONDIDO|CERRADO
        - ?tipo=RECLAMO|DUDA|PEDIDO|SUGERENCIA|OTRO
        - ?search=palabra_clave
        """
        # Validar que sea cliente
        if not request.user.id_rol or request.user.id_rol.nombre != 'CLIENTE':
            return APIResponse.forbidden(
                message='Este endpoint es solo para clientes.'
            )
        
        # Obtener solo tickets del cliente autenticado
        queryset = Ticket.objects.filter(
            id_cliente=request.user
        ).select_related(
            'id_agente_asignado'
        ).prefetch_related('mensajes')
        
        # Aplicar filtros opcionales
        estado = request.query_params.get('estado', None)
        if estado and TicketStatus.is_valid(estado):
            queryset = queryset.filter(estado=estado)
        
        tipo = request.query_params.get('tipo', None)
        if tipo:
            queryset = queryset.filter(tipo_consulta=tipo)
        
        search = request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(asunto__icontains=search) |
                Q(mensaje__icontains=search) |
                Q(id_ticket__icontains=search)
            )
        
        # Ordenar por fecha de creación
        queryset = queryset.order_by('-fecha_creacion')
        
        # Serializar con el serializer de lista
        serializer = TicketListSerializer(queryset, many=True)
        
        return APIResponse.success(
            data={
                'total': queryset.count(),
                'tickets': serializer.data
            },
            message=f'Se encontraron {queryset.count()} tickets.'
        )
    
    @action(detail=True, methods=['get'], url_path='mi-ticket')
    def mi_ticket(self, request, pk=None):
        """
        Endpoint para que el cliente vea el detalle completo de UNO de sus tickets.
        GET /api/soporte/tickets/{id}/mi-ticket/
        
        Incluye todos los mensajes y respuestas del ticket.
        """
        # Validar que sea cliente
        if not request.user.id_rol or request.user.id_rol.nombre != 'CLIENTE':
            return APIResponse.forbidden(
                message='Este endpoint es solo para clientes.'
            )
        
        ticket = self.get_object()
        
        # Validar que el ticket pertenezca al cliente autenticado
        if ticket.id_cliente != request.user:
            return APIResponse.forbidden(
                message='No tienes permiso para ver este ticket.'
            )
        
        # Serializar con todos los mensajes
        serializer = TicketSerializer(ticket)
        
        return APIResponse.success(
            data=serializer.data,
            message='Detalle del ticket obtenido exitosamente.'
        )
    
    @action(detail=True, methods=['post'], url_path='responder')
    def responder(self, request, pk=None):
        """Endpoint para que el agente responda un ticket"""
        ticket = self.get_object()
        
        # Validar que sea admin o vendedor
        if not request.user.id_rol or request.user.id_rol.nombre not in ['ADMINISTRADOR', 'VENDEDOR']:
            return APIResponse.forbidden(
                message='No tienes permisos para responder tickets.'
            )
        
        # Validar que no esté cerrado
        if ticket.estado == TicketStatus.CERRADO:
            return APIResponse.bad_request(
                message='No se puede responder un ticket cerrado.'
            )
        
        # Validar datos
        serializer = ResponderTicketSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.bad_request(
                message=Messages.INVALID_DATA,
                errors=serializer.errors
            )
        
        mensaje_texto = serializer.validated_data['mensaje']
        
        # Crear mensaje de respuesta
        mensaje = MensajeTicket.objects.create(
            ticket=ticket,
            id_usuario=request.user,
            mensaje=mensaje_texto,
            es_respuesta_agente=True
        )
        
        # Actualizar estado del ticket
        if ticket.estado == TicketStatus.PENDIENTE:
            ticket.estado = TicketStatus.EN_PROCESO
        elif ticket.estado == TicketStatus.EN_PROCESO:
            ticket.estado = TicketStatus.RESPONDIDO
        
        # Asignar agente si no está asignado
        if not ticket.id_agente_asignado:
            ticket.id_agente_asignado = request.user
        
        ticket.save()
        
        # Disparar señal de ticket respondido
        ticket_respondido.send(
            sender=MensajeTicket,
            ticket=ticket,
            mensaje=mensaje,
            usuario=request.user,
            ip=obtener_ip_cliente(request),
            es_agente=True
        )
        
        return APIResponse.created(
            data=MensajeTicketSerializer(mensaje).data,
            message='Respuesta enviada exitosamente.'
        )
    
    @action(detail=True, methods=['post'], url_path='mensaje-cliente')
    def mensaje_cliente(self, request, pk=None):
        """Endpoint para que el cliente responda"""
        ticket = self.get_object()
        
        # Verificar que el cliente sea dueño del ticket
        if ticket.id_cliente != request.user:
            return APIResponse.forbidden(
                message='No puedes responder este ticket.'
            )
        
        # Verificar que no esté cerrado
        if ticket.estado == TicketStatus.CERRADO:
            return APIResponse.bad_request(
                message='No puedes responder un ticket cerrado. Solicita su reapertura.'
            )
        
        # Validar datos
        serializer = ResponderTicketSerializer(data=request.data)
        if not serializer.is_valid():
            return APIResponse.bad_request(
                message=Messages.INVALID_DATA,
                errors=serializer.errors
            )
        
        mensaje_texto = serializer.validated_data['mensaje']
        
        # Crear mensaje
        mensaje = MensajeTicket.objects.create(
            ticket=ticket,
            id_usuario=request.user,
            mensaje=mensaje_texto,
            es_respuesta_agente=False
        )
        
        # Cambiar estado si estaba respondido
        if ticket.estado == TicketStatus.RESPONDIDO:
            ticket.estado = TicketStatus.EN_PROCESO
            ticket.save()
        
        # Disparar señal de ticket respondido
        ticket_respondido.send(
            sender=MensajeTicket,
            ticket=ticket,
            mensaje=mensaje,
            usuario=request.user,
            ip=obtener_ip_cliente(request),
            es_agente=False
        )
        
        return APIResponse.created(
            data=MensajeTicketSerializer(mensaje).data,
            message='Mensaje enviado exitosamente.'
        )
    
    @action(detail=True, methods=['post'], url_path='cerrar')
    def cerrar(self, request, pk=None):
        """Cerrar un ticket"""
        ticket = self.get_object()
        
        # Solo admin/vendedor puede cerrar
        if not request.user.id_rol or request.user.id_rol.nombre not in ['ADMINISTRADOR', 'VENDEDOR']:
            return APIResponse.forbidden(
                message='No tienes permisos para cerrar tickets.'
            )
        
        # Validar que no esté ya cerrado
        if ticket.estado == TicketStatus.CERRADO:
            return APIResponse.bad_request(
                message='El ticket ya está cerrado.'
            )
        
        ticket.estado = TicketStatus.CERRADO
        ticket.save()
        
        # Disparar señal de ticket cerrado
        ticket_cerrado.send(
            sender=Ticket,
            ticket=ticket,
            usuario=request.user,
            ip=obtener_ip_cliente(request)
        )
        
        return APIResponse.success(
            data={'id_ticket': ticket.id_ticket, 'estado': ticket.estado},
            message=f'Ticket #{ticket.id_ticket} cerrado exitosamente.'
        )
    
    @action(detail=True, methods=['post'], url_path='reabrir')
    def reabrir(self, request, pk=None):
        """Reabrir un ticket cerrado"""
        ticket = self.get_object()
        
        # Admin/vendedor puede reabrir
        es_admin = request.user.id_rol and request.user.id_rol.nombre in ['ADMINISTRADOR', 'VENDEDOR']
        
        # Cliente solo puede reabrir sus propios tickets
        es_dueno = ticket.id_cliente == request.user
        
        if not (es_admin or es_dueno):
            return APIResponse.forbidden(
                message='No tienes permisos para reabrir este ticket.'
            )
        
        # Validar que esté cerrado
        if ticket.estado != TicketStatus.CERRADO:
            return APIResponse.bad_request(
                message='Solo se pueden reabrir tickets cerrados.'
            )
        
        ticket.estado = TicketStatus.EN_PROCESO
        ticket.save()
        
        # Disparar señal de ticket reabierto
        ticket_reabierto.send(
            sender=Ticket,
            ticket=ticket,
            usuario=request.user,
            ip=obtener_ip_cliente(request)
        )
        
        return APIResponse.success(
            data={'id_ticket': ticket.id_ticket, 'estado': ticket.estado},
            message=f'Ticket #{ticket.id_ticket} reabierto exitosamente.'
        )
