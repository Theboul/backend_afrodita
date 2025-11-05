from rest_framework import serializers
from ..models import DireccionCliente, Cliente

# =====================================================
# SERIALIZER PARA CRUD DE DIRECCIONES
# =====================================================
class DireccionClienteSerializer(serializers.ModelSerializer):
    """Para CRUD completo de direcciones del cliente"""
    
    class Meta:
        model = DireccionCliente
        fields = [
            'id_direccion', 'etiqueta', 'direccion', 'ciudad',
            'departamento', 'pais', 'referencia', 'es_principal',
            'guardada', 'fecha_creacion'
        ]
        read_only_fields = ['id_direccion', 'fecha_creacion']
    
    def validate_direccion(self, value):
        """Validar que la dirección no esté vacía"""
        if not value or not value.strip():
            raise serializers.ValidationError(
                "La dirección es obligatoria y no puede estar vacía."
            )
        return value.strip()
    
    def validate_etiqueta(self, value):
        """Validar etiqueta (opcional)"""
        if value:
            return value.strip()
        return value


# =====================================================
# SERIALIZER PARA LISTAR DIRECCIONES (más liviano)
# =====================================================
class DireccionClienteListSerializer(serializers.ModelSerializer):
    """Versión simplificada para listar direcciones"""
    cliente_nombre = serializers.SerializerMethodField()
    cliente_id = serializers.SerializerMethodField()
    
    class Meta:
        model = DireccionCliente
        fields = [
            'id_direccion', 'etiqueta', 'direccion', 'ciudad',
            'es_principal', 'guardada', 'cliente_id', 'cliente_nombre'
        ]
    
    def get_cliente_nombre(self, obj):
        """Obtener nombre del cliente de forma segura"""
        try:
            return obj.id_cliente.id_cliente.nombre_completo
        except AttributeError:
            return "N/A"
    
    def get_cliente_id(self, obj):
        """Obtener ID del cliente de forma segura"""
        try:
            return obj.id_cliente.id_cliente.id_usuario
        except AttributeError:
            return None
