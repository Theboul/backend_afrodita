from rest_framework import serializers
from django.db.models import Q
from django.contrib.auth.hashers import check_password
from apps.usuarios.models import Usuario


class LoginSerializer(serializers.Serializer):
    """
    Serializer encargado de validar las credenciales de un usuario
    con mensajes genéricos para prevenir enumeración de usuarios.
    Acepta tanto 'contraseña' (español) como 'password' (inglés) para compatibilidad.
    """
    credencial = serializers.CharField(
        max_length=100,
        help_text="Nombre de usuario o correo electrónico"
    )
    contraseña = serializers.CharField(
        required=False,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Contraseña en español"
    )
    password = serializers.CharField(
        required=False,
        write_only=True,
        style={'input_type': 'password'},
        help_text="Password en inglés (alias de contraseña)"
    )

    def validate(self, data):
        credencial = data.get("credencial", "").strip()
        # Aceptar tanto 'contraseña' como 'password'
        contraseña = data.get("contraseña") or data.get("password", "")

        # Validación básica
        if not credencial or not contraseña:
            raise serializers.ValidationError(
                "Credenciales inválidas. Verifica tu usuario y contraseña."
            )

        # Buscar usuario por nombre de usuario o correo (una sola consulta)
        usuario = Usuario.objects.filter(
            Q(nombre_usuario=credencial) | Q(correo=credencial)
        ).first()

        # Mensaje genérico para evitar enumeración de usuarios
        if not usuario or not check_password(contraseña, usuario.password):
            raise serializers.ValidationError(
                "Credenciales inválidas. Verifica tu usuario y contraseña."
            )

        # Validar si el usuario está activo
        if usuario.estado_usuario != "ACTIVO":
            raise serializers.ValidationError(
                "Tu cuenta no está disponible. Contacta al soporte técnico."
            )

        # Si todo está correcto, devolver el usuario validado
        data["usuario"] = usuario
        return data


class RefreshTokenSerializer(serializers.Serializer):
    """
    Serializer para validar y refrescar tokens.
    """
    refresh = serializers.CharField(required=False)

    def validate(self, data):
        refresh = data.get('refresh') or self.context.get('refresh_token')
        
        if not refresh:
            raise serializers.ValidationError(
                "No se proporcionó un refresh token."
            )
        
        data['refresh'] = refresh
        return data