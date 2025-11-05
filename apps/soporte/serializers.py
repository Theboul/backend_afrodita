"""
Serializers para el módulo de soporte (CU25).
"""

from rest_framework import serializers
from django.utils import timezone
from .models import Ticket, MensajeTicket
from core.constants import TicketStatus, TicketType


# =====================================================
# SERIALIZER DE MENSAJES
# =====================================================

class MensajeTicketSerializer(serializers.ModelSerializer):
    """Serializer para mensajes de tickets"""
    usuario_nombre = serializers.CharField(source='id_usuario.nombre_completo', read_only=True)
    tipo_mensaje = serializers.SerializerMethodField()
    
    class Meta:
        model = MensajeTicket
        fields = [
            'id_mensaje',
            'ticket',
            'id_usuario',
            'usuario_nombre',
            'mensaje',
            'fecha_envio',
            'es_respuesta_agente',
            'tipo_mensaje'
        ]
        read_only_fields = ['id_mensaje', 'fecha_envio', 'id_usuario']
    
    def get_tipo_mensaje(self, obj):
        """Retorna el tipo de mensaje"""
        return "AGENTE" if obj.es_respuesta_agente else "CLIENTE"
    
    def validate_mensaje(self, value):
        """Validar que el mensaje no esté vacío"""
        if not value or value.strip() == '':
            raise serializers.ValidationError("El mensaje no puede estar vacío.")
        if len(value) < 10:
            raise serializers.ValidationError("El mensaje debe tener al menos 10 caracteres.")
        return value


# =====================================================
# SERIALIZER DE TICKETS
# =====================================================

class TicketSerializer(serializers.ModelSerializer):
    """Serializer completo para tickets con mensajes"""
    mensajes = MensajeTicketSerializer(many=True, read_only=True)
    cliente_nombre = serializers.CharField(source='id_cliente.nombre_completo', read_only=True)
    agente_nombre = serializers.CharField(
        source='id_agente_asignado.nombre_completo',
        read_only=True,
        allow_null=True
    )
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    tipo_display = serializers.CharField(source='get_tipo_consulta_display', read_only=True)
    puede_responder = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = [
            'id_ticket',
            'asunto',
            'tipo_consulta',
            'tipo_display',
            'mensaje',
            'estado',
            'estado_display',
            'fecha_creacion',
            'fecha_modificacion',
            'id_cliente',
            'cliente_nombre',
            'id_agente_asignado',
            'agente_nombre',
            'puede_responder',
            'mensajes'
        ]
        read_only_fields = [
            'id_ticket',
            'fecha_creacion',
            'fecha_modificacion',
            'id_cliente'
        ]
    
    def get_puede_responder(self, obj):
        """Indica si el ticket permite nuevas respuestas"""
        return obj.puede_responder()


class TicketListSerializer(serializers.ModelSerializer):
    """Serializer simplificado para listados"""
    cliente_nombre = serializers.CharField(source='id_cliente.nombre_completo', read_only=True)
    agente_nombre = serializers.CharField(
        source='id_agente_asignado.nombre_completo',
        read_only=True,
        allow_null=True
    )
    estado_display = serializers.CharField(source='get_estado_display', read_only=True)
    cantidad_mensajes = serializers.SerializerMethodField()
    
    class Meta:
        model = Ticket
        fields = [
            'id_ticket',
            'asunto',
            'tipo_consulta',
            'estado',
            'estado_display',
            'fecha_creacion',
            'cliente_nombre',
            'agente_nombre',
            'cantidad_mensajes'
        ]
    
    def get_cantidad_mensajes(self, obj):
        """Retorna la cantidad de mensajes en el ticket"""
        return obj.mensajes.count()


class CrearTicketSerializer(serializers.ModelSerializer):
    """Serializer para crear tickets"""
    
    class Meta:
        model = Ticket
        fields = ['asunto', 'tipo_consulta', 'mensaje']
    
    def validate_asunto(self, value):
        """Validar asunto"""
        if not value or value.strip() == '':
            raise serializers.ValidationError("El asunto es obligatorio.")
        if len(value) < 5:
            raise serializers.ValidationError("El asunto debe tener al menos 5 caracteres.")
        if len(value) > 200:
            raise serializers.ValidationError("El asunto no puede exceder 200 caracteres.")
        return value.strip()
    
    def validate_mensaje(self, value):
        """Validar mensaje inicial"""
        if not value or value.strip() == '':
            raise serializers.ValidationError("El mensaje es obligatorio.")
        if len(value) < 20:
            raise serializers.ValidationError("El mensaje debe tener al menos 20 caracteres.")
        return value.strip()
    
    def validate_tipo_consulta(self, value):
        """Validar tipo de consulta"""
        if not TicketType.is_valid(value):
            raise serializers.ValidationError("Tipo de consulta inválido.")
        return value


class ResponderTicketSerializer(serializers.Serializer):
    """Serializer para responder tickets"""
    mensaje = serializers.CharField(
        required=True,
        min_length=10,
        max_length=5000,
        error_messages={
            'required': 'El mensaje es obligatorio.',
            'min_length': 'El mensaje debe tener al menos 10 caracteres.',
            'max_length': 'El mensaje no puede exceder 5000 caracteres.'
        }
    )
    
    def validate_mensaje(self, value):
        """Validar que el mensaje no esté vacío"""
        if not value or value.strip() == '':
            raise serializers.ValidationError("El mensaje no puede estar vacío.")
        return value.strip()


class CambiarEstadoSerializer(serializers.Serializer):
    """Serializer para cambiar estado de ticket"""
    estado = serializers.ChoiceField(
        choices=TicketStatus.choices(),
        required=True,
        error_messages={'required': 'El estado es obligatorio.'}
    )
    
    def validate_estado(self, value):
        """Validar que el estado sea válido"""
        if not TicketStatus.is_valid(value):
            raise serializers.ValidationError("Estado inválido.")
        return value
