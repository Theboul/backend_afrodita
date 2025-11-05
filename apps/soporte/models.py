"""
Modelos para el sistema de soporte y tickets (CU25).

Este módulo gestiona:
- Tickets de soporte/contacto de clientes
- Mensajes de conversación en tickets
- Historial completo de comunicación
"""

from django.db import models
from django.conf import settings
from core.constants import TicketStatus, TicketType


class Ticket(models.Model):
    """
    Ticket de soporte creado por clientes.
    
    Permite registrar consultas, reclamos, dudas o sugerencias
    y gestionar su seguimiento hasta el cierre.
    """
    id_ticket = models.AutoField(primary_key=True)
    asunto = models.CharField(
        max_length=200,
        help_text="Asunto o título del ticket"
    )
    tipo_consulta = models.CharField(
        max_length=20,
        choices=TicketType.choices(),
        help_text="Tipo de consulta (reclamo, duda, sugerencia, etc.)"
    )
    mensaje = models.TextField(
        help_text="Mensaje inicial del ticket"
    )
    estado = models.CharField(
        max_length=20,
        choices=TicketStatus.choices(),
        default=TicketStatus.PENDIENTE,
        help_text="Estado actual del ticket"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    # Relaciones
    id_cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='id_cliente',
        related_name='tickets_creados',
        help_text="Cliente que creó el ticket"
    )
    id_agente_asignado = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column='id_agente_asignado',
        null=True,
        blank=True,
        related_name='tickets_asignados',
        help_text="Agente de soporte asignado al ticket"
    )
    
    # Nota: id_venta está en la BD pero Venta aún no está implementada en Django
    # Se dejará comentado hasta que se implemente el módulo de ventas
    # id_venta = models.ForeignKey(
    #     'ventas.Venta',
    #     on_delete=models.SET_NULL,
    #     null=True,
    #     blank=True,
    #     help_text="Venta relacionada con el ticket (opcional)"
    # )
    
    class Meta:
        db_table = 'ticket'
        verbose_name = 'Ticket de Soporte'
        verbose_name_plural = 'Tickets de Soporte'
        ordering = ['-fecha_creacion']
        indexes = [
            models.Index(fields=['estado', '-fecha_creacion']),
            models.Index(fields=['id_cliente', '-fecha_creacion']),
        ]
    
    def __str__(self):
        return f"Ticket #{self.id_ticket} - {self.asunto}"
    
    def puede_responder(self):
        """Verifica si el ticket permite nuevas respuestas"""
        return self.estado != TicketStatus.CERRADO


class MensajeTicket(models.Model):
    """
    Mensaje dentro de un ticket de soporte.
    
    Permite mantener el historial completo de conversación
    entre cliente y agente de soporte.
    """
    id_mensaje = models.AutoField(primary_key=True)
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='mensajes',
        help_text="Ticket al que pertenece el mensaje"
    )
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_column='id_usuario',
        related_name='mensajes_tickets',
        help_text="Usuario que envió el mensaje"
    )
    mensaje = models.TextField(
        help_text="Contenido del mensaje"
    )
    fecha_envio = models.DateTimeField(auto_now_add=True)
    es_respuesta_agente = models.BooleanField(
        default=False,
        help_text="True si el mensaje fue enviado por un agente de soporte"
    )
    
    class Meta:
        db_table = 'mensaje_ticket'
        verbose_name = 'Mensaje de Ticket'
        verbose_name_plural = 'Mensajes de Tickets'
        ordering = ['fecha_envio']
        indexes = [
            models.Index(fields=['ticket', 'fecha_envio']),
        ]
    
    def __str__(self):
        tipo = "Agente" if self.es_respuesta_agente else "Cliente"
        return f"[{tipo}] {self.usuario.nombre_completo} en Ticket #{self.ticket.id_ticket}"
