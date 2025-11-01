from rest_framework import serializers
from ..models import Usuario, Cliente, DireccionCliente
from utils.validators import (
    validate_password_strength,
    validate_phone,
)

# =====================================================
# SERIALIZER PARA VER PERFIL COMPLETO
# =====================================================
class PerfilClienteSerializer(serializers.ModelSerializer):
    """Para mostrar el perfil completo del cliente"""
    rol = serializers.CharField(source='id_rol.nombre', read_only=True)
    direccion_principal = serializers.SerializerMethodField()
    total_direcciones = serializers.SerializerMethodField()
    
    class Meta:
        model = Usuario
        fields = [
            'id_usuario', 'nombre_completo', 'nombre_usuario', 'correo',
            'telefono', 'sexo', 'fecha_registro', 'rol', 
            'direccion_principal', 'total_direcciones'
        ]
        read_only_fields = [
            'id_usuario', 'nombre_usuario', 'fecha_registro', 'rol'
        ]
    
    def get_direccion_principal(self, obj):
        """Incluir dirección principal en el perfil"""
        try:
            cliente = Cliente.objects.get(id_cliente=obj)
            direccion = DireccionCliente.objects.filter(
                id_cliente=cliente, es_principal=True
            ).first()
            if direccion:
                return {
                    'id_direccion': direccion.id_direccion,
                    'etiqueta': direccion.etiqueta,
                    'direccion': direccion.direccion,
                    'ciudad': direccion.ciudad,
                    'departamento': direccion.departamento,
                    'pais': direccion.pais,
                }
        except Cliente.DoesNotExist:
            pass
        return None
    
    def get_total_direcciones(self, obj):
        """Contar direcciones guardadas del cliente"""
        try:
            cliente = Cliente.objects.get(id_cliente=obj)
            return DireccionCliente.objects.filter(
                id_cliente=cliente, guardada=True
            ).count()
        except Cliente.DoesNotExist:
            return 0


# =====================================================
# SERIALIZER PARA ACTUALIZAR PERFIL
# =====================================================
class PerfilClienteUpdateSerializer(serializers.ModelSerializer):
    """Solo campos que el cliente puede editar"""
    
    class Meta:
        model = Usuario
        fields = ['nombre_completo', 'telefono', 'correo', 'sexo']
        extra_kwargs = {
            'nombre_completo': {'required': False},
            'telefono': {'required': False},
            'correo': {'required': False},
            'sexo': {'required': False},
        }
    
    def validate_correo(self, value):
        """Validar que el email no exista (excepto el mío)"""
        usuario = self.instance
        if Usuario.objects.filter(correo=value).exclude(
            id_usuario=usuario.id_usuario
        ).exists():
            raise serializers.ValidationError("Este correo ya está registrado.")
        return value.lower().strip()
    
    def validate_telefono(self, value):
        """Validar formato de teléfono"""
        if value:
            return validate_phone(value)
        return value
    
    def validate_sexo(self, value):
        """Validar sexo"""
        if value:
            value = value.upper()
            if value not in ['M', 'F']:
                raise serializers.ValidationError(
                    "El sexo debe ser 'M' (Masculino) o 'F' (Femenino)."
                )
        return value


# =====================================================
# SERIALIZER PARA CAMBIAR CONTRASEÑA
# =====================================================
class CambiarPasswordClienteSerializer(serializers.Serializer):
    """Para cambio de contraseña del cliente"""
    contraseña_actual = serializers.CharField(write_only=True, required=True)
    contraseña_nueva = serializers.CharField(write_only=True, required=True)
    confirmar_contraseña = serializers.CharField(write_only=True, required=True)
    
    def validate(self, data):
        """Validar que las contraseñas coincidan"""
        if data['contraseña_nueva'] != data['confirmar_contraseña']:
            raise serializers.ValidationError(
                {"confirmar_contraseña": "Las contraseñas no coinciden."}
            )
        
        # Validar fortaleza de la contraseña
        validate_password_strength(data['contraseña_nueva'])
        
        return data
