from rest_framework import serializers
from django.utils import timezone
from .models import Cliente, Usuarios
from django.contrib.auth.hashers import make_password
from utils.validators import (
    validate_password_strength, validate_unique_email, validate_unique_username,
    validate_phone, validate_sex
)


class RegistroStep1Serializer(serializers.Serializer):
    nombre_usuario = serializers.CharField(min_length=4, max_length=50)
    correo = serializers.EmailField(max_length=100)
    password = serializers.CharField(write_only=True, max_length=255)
    confirm_password = serializers.CharField(write_only=True, max_length=255)

    def validate_nombre_usuario(self, value):
        return validate_unique_username(value)

    def validate_correo(self, value):
        return validate_unique_email(value)

    def validate_password(self, value):
        return validate_password_strength(value)

    def validate(self, data):
        if data["password"] != data["confirm_password"]:
            raise serializers.ValidationError({"confirm_password": "Las contraseñas no coinciden."})
        return data


class RegistroStep2Serializer(serializers.Serializer):
    nombre_completo = serializers.CharField(max_length=90)
    telefono = serializers.CharField(max_length=20, allow_blank=True, required=False)
    sexo = serializers.CharField(max_length=1)
    # Campos de Cliente
    direccion = serializers.CharField(max_length=100)

    # Además recibimos del paso 1
    nombre_usuario = serializers.CharField(max_length=50)
    correo = serializers.EmailField(max_length=100)
    password = serializers.CharField(write_only=True, max_length=255)

    def validate_telefono(self, value):
        return validate_phone(value)

    def validate_sexo(self, value):
        return validate_sex(value)
    

    def create(self, validated_data):
        # Crear usuario
        usuario = Usuarios.objects.create(
            nombre_completo=validated_data["nombre_completo"].strip(),
            nombre_usuario=validated_data["nombre_usuario"].strip(),
            password=make_password(validated_data["password"]),
            correo=validated_data["correo"].lower().strip(),
            telefono=validated_data.get("telefono"),
            sexo=validated_data["sexo"],
            fecha_registro=timezone.now(),
            estado_usuario="ACTIVO",
            rol="CLIENTE",
        )

        # Crear cliente vinculado
        cliente = Cliente.objects.create(
            id_cliente=usuario,
            direccion=validated_data["direccion"].strip(),
        )
        return cliente
    
    def to_representation(self, instance):
        """Define cómo se responde después del POST"""
        return {
            "id_usuario": instance.id_cliente.id_usuario,
            "nombre_completo": instance.id_cliente.nombre_completo,
            "nombre_usuario": instance.id_cliente.nombre_usuario,
            "correo": instance.id_cliente.correo,
            "telefono": instance.id_cliente.telefono,
            "sexo": instance.id_cliente.sexo,
            "direccion": instance.direccion,
            "rol": instance.id_cliente.rol,
        }


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuarios
        fields = ["id_usuario", "nombre_completo", "nombre_usuario", "correo", "telefono", "sexo", "rol"]

class ClienteSerializer(serializers.ModelSerializer):
    usuario = UsuarioSerializer(source="id_cliente", read_only=True)

    class Meta:
        model = Cliente
        fields = ["id_cliente", "direccion", "usuario"]
