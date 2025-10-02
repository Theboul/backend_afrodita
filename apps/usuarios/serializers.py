from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from apps.clientes.models import Usuarios
from apps.usuarios.models import Vendedor, Administrador
from utils.validators import (
    validate_password_strength, validate_unique_email, validate_unique_username,
    validate_phone, validate_sex
)

# CREACIÓN DE USUARIOS
class UsuarioCreateSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = Usuarios
        fields = [
            "nombre_completo", "nombre_usuario", "correo",
            "telefono", "sexo", "rol", "password"
        ]

    def validate_nombre_usuario(self, value):
        return validate_unique_username(value)

    def validate_correo(self, value):
        return validate_unique_email(value)

    def validate_password(self, value):
        return validate_password_strength(value)

    def validate_telefono(self, value):
        return validate_phone(value)

    def validate_sexo(self, value):
        return validate_sex(value)

    def create(self, validated_data):
        rol = validated_data["rol"].upper()

        usuario = Usuarios.objects.create(
            nombre_completo=validated_data["nombre_completo"].strip(),
            nombre_usuario=validated_data["nombre_usuario"].strip(),
            correo=validated_data["correo"].lower().strip(),
            password=make_password(validated_data["password"]),
            telefono=validated_data.get("telefono"),
            sexo=validated_data["sexo"].upper(),
            estado_usuario="ACTIVO",
            rol=rol,
            fecha_registro=timezone.now(),
        )


        if rol == "VENDEDOR":
            Vendedor.objects.create(
                id_vendedor=usuario,
                fecha_contrato=timezone.now().date(),
                tipo_vendedor="INTERNO"  # podrías permitir elegir este campo
            )
        elif rol == "ADMINISTRADOR":
            Administrador.objects.create(
                id_administrador=usuario,
                fecha_contrato=timezone.now().date()
            )

        if rol == "CLIENTE":
            raise serializers.ValidationError("Los clientes deben registrarse desde su módulo.")
        
        return usuario
    

# SOLO LECTURA (para listar y ver detalle)
class UsuarioDetailSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuarios
        fields = [
            "id_usuario",
            "nombre_completo",
            "nombre_usuario",
            "correo",
            "telefono",
            "sexo",
            "rol",
            "estado_usuario",
        ]


# ACTUALIZACIÓN (sin incluir password)
class UsuarioUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuarios
        fields = [
            "nombre_completo",
            "nombre_usuario",
            "correo",
            "telefono",
            "sexo",
            "rol",
            "estado_usuario",
        ]
        extra_kwargs = {
            "correo": {"required": False},
            "nombre_usuario": {"required": False},
            "telefono": {"required": False},
            "sexo": {"required": False},
            "rol": {"required": False},
            "estado_usuario": {"required": False},
        }

    def validate_telefono(self, value):
        return validate_phone(value)

    def validate_sexo(self, value):
        return validate_sex(value)