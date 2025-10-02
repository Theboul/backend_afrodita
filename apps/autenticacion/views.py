from django.shortcuts import render

# Create your views here.

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.hashers import check_password
from rest_framework_simplejwt.tokens import RefreshToken
from apps.clientes.models import Usuarios, Cliente
from apps.usuarios.models import Vendedor, Administrador


class LoginView(APIView):
    permission_classes = []  # público

    def post(self, request):
        login_id = request.data.get("login")  # puede ser correo o username
        password = request.data.get("password")

        if not login_id or not password:
            return Response({"error": "Debe ingresar usuario/correo y contraseña."},
                            status=status.HTTP_400_BAD_REQUEST)

        # 1. Buscar por correo o username
        try:
            usuario = Usuarios.objects.filter(correo=login_id.lower().strip()).first()
            if not usuario:
                usuario = Usuarios.objects.filter(nombre_usuario=login_id.strip()).first()
            if not usuario:
                return Response({"error": "Usuario no encontrado."}, status=status.HTTP_404_NOT_FOUND)
        except Exception:
            return Response({"error": "Error al consultar el usuario."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 2. Verificar contraseña
        if not check_password(password, usuario.password):
            return Response({"error": "Credenciales incorrectas."}, status=status.HTTP_401_UNAUTHORIZED)

        # 3. Verificar estado
        if usuario.estado_usuario == "BLOQUEADO":
            return Response({"error": "La cuenta está bloqueada"}, status=status.HTTP_403_FORBIDDEN)

        # 4. Generar JWT
        refresh = RefreshToken.for_user(usuario)

        # 5. Datos extra según rol
        extra = {}
        if usuario.rol == "CLIENTE":
            cliente = getattr(usuario, "cliente", None)
            if cliente:
                extra["direccion"] = cliente.direccion

        elif usuario.rol == "VENDEDOR":
            vendedor = getattr(usuario, "vendedor", None)
            if vendedor:
                extra["fecha_contrato"] = vendedor.fecha_contrato
                extra["tipo_vendedor"] = vendedor.tipo_vendedor

        elif usuario.rol == "ADMINISTRADOR":
            admin = getattr(usuario, "administrador", None)
            if admin:
                extra["fecha_contrato"] = admin.fecha_contrato

        # 6. Respuesta
        return Response({
            "mensaje": "Inicio de sesión exitoso",
            "usuario": {
                "id": usuario.id_usuario,
                "nombre": usuario.nombre_completo,
                "rol": usuario.rol
            },
            "token": {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
