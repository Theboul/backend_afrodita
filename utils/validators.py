import re
from rest_framework import serializers
from apps.clientes.models import Usuarios


def validate_password_strength(password: str) -> str:
    """
    Valida que la contraseña cumpla con requisitos de seguridad.
    """
    if len(password) < 8:
        raise serializers.ValidationError("La contraseña debe tener al menos 8 caracteres.")
    if not re.search(r"[A-Z]", password):
        raise serializers.ValidationError("Debe contener al menos una letra mayúscula.")
    if not re.search(r"[a-z]", password):
        raise serializers.ValidationError("Debe contener al menos una letra minúscula.")
    if not re.search(r"[0-9]", password):
        raise serializers.ValidationError("Debe contener al menos un número.")
    if not re.search(r"[\W_]", password):
        raise serializers.ValidationError("Debe contener al menos un símbolo.")
    return password


def validate_unique_email(correo: str) -> str:
    """
    Verifica que el correo no exista ya en la base de datos.
    """
    correo = correo.lower().strip()
    if Usuarios.objects.filter(correo=correo).exists():
        raise serializers.ValidationError("El correo ya está registrado.")
    return correo


def validate_unique_username(nombre_usuario: str) -> str:
    """
    Verifica que el nombre de usuario no exista ya en la base de datos.
    """
    nombre_usuario = nombre_usuario.strip()
    if len(nombre_usuario) < 4:
        raise serializers.ValidationError("El nombre de usuario debe tener al menos 4 caracteres.")
    if Usuarios.objects.filter(nombre_usuario=nombre_usuario).exists():
        raise serializers.ValidationError("El nombre de usuario ya está en uso.")
    return nombre_usuario


def validate_phone(telefono: str) -> str:
    """
    Verifica que el teléfono contenga solo dígitos y tenga longitud válida.
    """
    if telefono and not re.match(r"^\d{8,15}$", telefono):
        raise serializers.ValidationError("El teléfono debe contener solo números (8-15 dígitos).")
    return telefono


def validate_sex(sexo: str) -> str:
    """
    Valida el campo sexo, permitiendo solo M, F o N.
    """
    value = sexo.upper().strip()
    if value not in ["M", "F", "N"]:
        raise serializers.ValidationError("Sexo debe ser 'M', 'F' o 'N'.")
    return value