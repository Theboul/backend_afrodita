from rest_framework import serializers
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from ..models import Usuario, Vendedor, Administrador, Cliente
from apps.seguridad.models import Rol  # 🔄 Importar desde seguridad
from utils.validators import (
    validate_password_strength,
    validate_unique_email,
    validate_unique_username,
    validate_phone,
    validate_sex,
)

# Importar constantes
from core.constants.estados import UserStatus

# =====================================================
# SERIALIZERS PARA GESTIÓN ADMINISTRATIVA
# =====================================================

class UsuarioAdminListSerializer(serializers.ModelSerializer):
    """Serializer para listar usuarios en panel admin"""
    rol = serializers.CharField(source='id_rol.nombre', read_only=True)
    ultimo_login = serializers.DateTimeField(source='last_login', read_only=True)

    class Meta:
        model = Usuario
        fields = [
            'id_usuario', 'nombre_completo', 'nombre_usuario', 'correo',
            'telefono', 'sexo', 'fecha_registro', 'estado_usuario', 'rol',
            'ultimo_login'
        ]

class UsuarioAdminDetailSerializer(serializers.ModelSerializer):
    """Serializer para detalles completos en panel admin"""
    rol = serializers.CharField(source='id_rol.nombre', read_only=True)
    ultimo_login = serializers.DateTimeField(source='last_login', read_only=True)
    datos_adicionales = serializers.SerializerMethodField()

    class Meta:
        model = Usuario
        fields = [
            'id_usuario', 'nombre_completo', 'nombre_usuario', 'correo',
            'telefono', 'sexo', 'fecha_registro', 'estado_usuario', 'rol',
            'ultimo_login', 'datos_adicionales'
        ]

    def get_datos_adicionales(self, obj):
        try:
            if obj.id_rol and obj.id_rol.nombre == 'VENDEDOR':
                vendedor = Vendedor.objects.get(id_vendedor=obj)
                return {
                    'vendedor': {
                        'fecha_contrato': vendedor.fecha_contrato,
                        'tipo_vendedor': vendedor.tipo_vendedor
                    }
                }
            elif obj.id_rol and obj.id_rol.nombre == 'ADMINISTRADOR':
                administrador = Administrador.objects.get(id_administrador=obj)
                return {
                    'administrador': {
                        'fecha_contrato': administrador.fecha_contrato,
                    }
                }
            elif obj.id_rol and obj.id_rol.nombre == 'CLIENTE':
                cliente = Cliente.objects.get(id_cliente=obj)
                return {
                    'cliente': {
                        'fecha_registro': obj.fecha_registro.date(),
                    }
                }
        except (Vendedor.DoesNotExist, Administrador.DoesNotExist, Cliente.DoesNotExist):
            pass
        return {}

class UsuarioAdminCreateSerializer(serializers.ModelSerializer):
    """Serializer para crear usuarios como administrador"""
    contraseña = serializers.CharField(write_only=True, max_length=255)
    rol = serializers.CharField(write_only=True)
    datos_rol = serializers.JSONField(required=False)

    class Meta:
        model = Usuario
        fields = [
            'nombre_completo', 'nombre_usuario', 'correo', 'contraseña',
            'telefono', 'sexo', 'rol', 'datos_rol'
        ]

    def validate_nombre_usuario(self, value):
        return validate_unique_username(value)

    def validate_correo(self, value):
        return validate_unique_email(value)

    def validate_contraseña(self, value):
        return validate_password_strength(value)

    def validate_telefono(self, value):
        if value:
            return validate_phone(value)
        return value

    def validate_sexo(self, value):
        return validate_sex(value)

    def validate_rol(self, value):
        roles_permitidos = ['CLIENTE', 'VENDEDOR', 'ADMINISTRADOR']
        if value.upper() not in roles_permitidos:
            raise serializers.ValidationError(
                f"Rol debe ser uno de: {', '.join(roles_permitidos)}"
            )
        return value.upper()

    def create(self, validated_data):
        rol_nombre = validated_data.pop('rol')
        contraseña = validated_data.pop('contraseña')
        datos_rol = validated_data.pop('datos_rol', {})
        
        rol_obj = Rol.objects.get(nombre=rol_nombre)
        
        # Crear usuario base
        usuario = Usuario.objects.create(
            nombre_completo=validated_data['nombre_completo'].strip(),
            nombre_usuario=validated_data['nombre_usuario'].strip(),
            correo=validated_data['correo'].lower().strip(),
            password=make_password(contraseña),
            telefono=validated_data.get('telefono'),
            sexo=validated_data['sexo'].upper(),
            estado_usuario=UserStatus.ACTIVO,
            id_rol=rol_obj,
            fecha_registro=timezone.now(),
        )

        # Configurar permisos de staff/superuser para administradores
        if rol_nombre == 'ADMINISTRADOR':
            usuario.is_staff = True
            usuario.is_superuser = True
            usuario.save()

        # Crear registro específico según el rol
        if rol_nombre == 'VENDEDOR':
            Vendedor.objects.create(
                id_vendedor=usuario,
                fecha_contrato=datos_rol.get('fecha_contrato', timezone.now().date()),
                tipo_vendedor=datos_rol.get('tipo_vendedor', 'INTERNO')
            )
        elif rol_nombre == 'ADMINISTRADOR':
            Administrador.objects.create(
                id_administrador=usuario,
                fecha_contrato=datos_rol.get('fecha_contrato', timezone.now().date()),
            )
        elif rol_nombre == 'CLIENTE':
            Cliente.objects.create(id_cliente=usuario)

        return usuario

class UsuarioAdminUpdateSerializer(serializers.ModelSerializer):
    """Serializer para actualizar usuarios como administrador"""
    class Meta:
        model = Usuario
        fields = [
            'nombre_completo', 'nombre_usuario', 'correo', 'telefono', 
            'sexo', 'estado_usuario', 'id_rol'
        ]
        extra_kwargs = {
            'nombre_usuario': {'required': False},
            'correo': {'required': False},
        }

    def validate_nombre_usuario(self, value):
        if self.instance and value != self.instance.nombre_usuario:
            return validate_unique_username(value)
        return value

    def validate_correo(self, value):
        if self.instance and value != self.instance.correo:
            return validate_unique_email(value)
        return value

    def validate_telefono(self, value):
        if value:
            return validate_phone(value)
        return value

    def validate_sexo(self, value):
        return validate_sex(value)

# =====================================================
# SERIALIZERS PARA ACCIONES ESPECÍFICAS
# =====================================================

class CambiarContraseñaSerializer(serializers.Serializer):
    nueva_contrasena = serializers.CharField(write_only=True, max_length=255)
    confirmar_contrasena = serializers.CharField(write_only=True, max_length=255)

    def validate(self, data):
        if data['nueva_contrasena'] != data['confirmar_contrasena']:
            raise serializers.ValidationError({
                'confirmar_contrasena': 'Las contraseñas no coinciden'
            })
        validate_password_strength(data['nueva_contrasena'])
        return data

class CambiarEstadoSerializer(serializers.Serializer):
    estado_usuario = serializers.ChoiceField(choices=UserStatus.choices())
    motivo = serializers.CharField(
        required=False, 
        allow_blank=True, 
        max_length=255,
        help_text="Motivo del cambio de estado (opcional)"
    )

# =====================================================
# SERIALIZER PARA FORZAR LOGOUT
# =====================================================
class ForzarLogoutSerializer(serializers.Serializer):
    motivo = serializers.CharField(
        required=False, 
        allow_blank=True, 
        max_length=255,
        help_text="Motivo del logout forzado (opcional)"
    )
    
    def validate_motivo(self, value):
        if value and len(value.strip()) < 5:
            raise serializers.ValidationError("El motivo debe tener al menos 5 caracteres")
        return value