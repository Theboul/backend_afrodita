from rest_framework import serializers
from ..models import Usuario, Rol
from utils.validators import validate_phone, validate_sex


class RolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Rol
        fields = ["id_rol", "nombre", "descripcion"]


class UsuarioDetailSerializer(serializers.ModelSerializer):
    rol = RolSerializer(source="id_rol", read_only=True)  # mostrará el nombre del rol

    class Meta:
        model = Usuario
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


# =====================================================
# SERIALIZER ACTUALIZACIÓN USUARIO
# =====================================================
class UsuarioUpdateSerializer(serializers.ModelSerializer):
    id_rol = serializers.PrimaryKeyRelatedField(
        queryset=Rol.objects.all(),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Usuario
        fields = [
            "nombre_completo",
            "nombre_usuario",
            "correo",
            "telefono",
            "sexo",
            "id_rol",
            "estado_usuario",
        ]
        extra_kwargs = {field: {"required": False} for field in fields}

    def validate_telefono(self, value):
        if value:
            return validate_phone(value)
        return value

    def validate_sexo(self, value):
        return validate_sex(value)
