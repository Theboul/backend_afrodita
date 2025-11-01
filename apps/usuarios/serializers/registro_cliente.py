from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from ..models import Usuario, Cliente
from apps.seguridad.models import Rol  # 🔄 Importar desde seguridad
from utils.validators import (
    validate_password_strength,
    validate_unique_email,
    validate_unique_username,
    validate_phone,
    validate_sex,
)


# =====================================================
# PASO 1: CREACIÓN DE CREDENCIALES
# =====================================================
class RegistroStep1Serializer(serializers.Serializer):
    nombre_usuario = serializers.CharField(min_length=4, max_length=50)
    correo = serializers.EmailField(max_length=100)
    contraseña = serializers.CharField(write_only=True, max_length=255)
    confirmar_contraseña = serializers.CharField(write_only=True, max_length=255)
    

    def validate_nombre_usuario(self, value):
        return validate_unique_username(value)

    def validate_correo(self, value):
        return validate_unique_email(value)

    def validate_contraseña(self, value):
        return validate_password_strength(value)

    def validate(self, data):
        if data["contraseña"] != data["confirmar_contraseña"]:
            raise serializers.ValidationError(
                {"confirmar_contraseña": "Las contraseñas no coinciden."}
            )
        return data


# =====================================================
# PASO 2: DATOS PERSONALES + CREACIÓN FINAL
# =====================================================
class RegistroStep2Serializer(serializers.Serializer):
    # Datos personales
    nombre_completo = serializers.CharField(max_length=90)
    telefono = serializers.CharField(max_length=20, allow_blank=True, required=False)
    sexo = serializers.CharField(max_length=1)

    # Datos previos del paso 1
    nombre_usuario = serializers.CharField(max_length=50)
    correo = serializers.EmailField(max_length=100)
    contraseña = serializers.CharField(write_only=True, max_length=255)

    def validate_telefono(self, value):
        return validate_phone(value)

    def validate_sexo(self, value):
        return validate_sex(value)


    def create(self, validated_data):

        rol_cliente = Rol.objects.get(nombre="CLIENTE")
        # Crear usuario base
        usuario = Usuario(
            nombre_completo=validated_data["nombre_completo"].strip(),
            nombre_usuario=validated_data["nombre_usuario"].strip(),
            correo=validated_data["correo"].lower().strip(),
            telefono=validated_data.get("telefono"),
            sexo=validated_data["sexo"].upper(),
            fecha_registro=timezone.now(),
            estado_usuario="ACTIVO",
            id_rol=rol_cliente,
        )

        usuario.set_password(validated_data["contraseña"])
        usuario.save()

        # Crear cliente asociado
        cliente = Cliente.objects.create(id_cliente=usuario)
        return cliente

    def to_representation(self, instance):
        """Define cómo se responde después del registro"""
        return {
            "id_usuario": instance.id_cliente.id_usuario,
            "nombre_completo": instance.id_cliente.nombre_completo,
            "nombre_usuario": instance.id_cliente.nombre_usuario,
            "correo": instance.id_cliente.correo,
            "telefono": instance.id_cliente.telefono,
            "sexo": instance.id_cliente.sexo,
            "rol": instance.id_cliente.id_rol.nombre if instance.id_cliente.id_rol else None,
        }
