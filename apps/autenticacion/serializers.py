from rest_framework import serializers
from django.contrib.auth.hashers import check_password
from apps.clientes.models import Usuarios   # usamos tu modelo Usuarios

class LoginSerializer(serializers.Serializer):
    login = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        login = data.get("login").strip().lower()
        password = data.get("password")

        # Buscar por correo o username
        usuario = Usuarios.objects.filter(correo=login).first() \
        or Usuarios.objects.filter(nombre_usuario=login).first()

        if not usuario:
            raise serializers.ValidationError("Credenciales incorrectas.")

        if not check_password(password, usuario.password):
            raise serializers.ValidationError("Credenciales incorrectas.")

        if usuario.estado_usuario != "ACTIVO":
            raise serializers.ValidationError("La cuenta NO está activa.")

        data["usuario"] = usuario
        return data
    