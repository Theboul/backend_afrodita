from rest_framework import serializers
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from ..models import Usuario
from apps.seguridad.models import Rol
from utils.validators import (
    validate_password_strength,
    validate_unique_email,
    validate_unique_username,
    validate_phone,
    validate_sex,
)


class UsuarioBaseSerializer(serializers.ModelSerializer):
    contraseña = serializers.CharField(write_only=True)

    class Meta:
        model = Usuario
        fields = [
            "nombre_completo",
            "nombre_usuario",
            "correo",
            "telefono",
            "sexo",
            "contraseña",
        ]

    # =======================
    # VALIDACIONES
    # =======================
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

    # =======================
    # CREACIÓN BASE
    # =======================
    def create_usuario_base(self, validated_data, rol_obj):
        """Crea el usuario base en la tabla `usuarios`"""
        usuario = Usuario.objects.create(
            nombre_completo=validated_data["nombre_completo"].strip(),
            nombre_usuario=validated_data["nombre_usuario"].strip(),
            correo=validated_data["correo"].lower().strip(),
            password=make_password(validated_data["contraseña"]),
            telefono=validated_data.get("telefono"),
            sexo=validated_data["sexo"].upper(),
            estado_usuario="ACTIVO",
            id_rol=rol_obj,
            fecha_registro=timezone.now(),
        )

        # Si es administrador, marcar los permisos
        if rol_obj.nombre.upper() == "ADMINISTRADOR":
            usuario.is_staff = True
            usuario.is_superuser = True
            usuario.save()

        return usuario
