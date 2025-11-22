from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated

from .serializers import (
    RegistroVendedorSerializer,
    RegistroAdministradorSerializer,
)


# =====================================================
# VISTA BASE REUTILIZABLE
# =====================================================
class RegistroBaseView(APIView):
    """
    Clase base para registrar distintos tipos de usuarios (cliente, vendedor, admin).
    Cada subclase define su propio serializer_class.
    """
    permission_classes = [permissions.AllowAny]
    serializer_class = None  # se define en subclases

    def post(self, request):
        serializer = self.serializer_class(data=request.data)

        if serializer.is_valid():
            usuario = serializer.save()
            return Response(
                {
                    "message": f"{usuario.id_rol.nombre} registrado correctamente.",
                    "usuario": {
                        "id_usuario": usuario.id_usuario,
                        "nombre_usuario": usuario.nombre_usuario,
                        "correo": usuario.correo,
                        "rol": usuario.id_rol.nombre if usuario.id_rol else None,
                        "fecha_registro": usuario.fecha_registro,
                    },
                },
                status=status.HTTP_201_CREATED,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    


# =====================================================
# VISTAS ESPECÍFICAS
# =====================================================

class RegistroVendedorView(RegistroBaseView):
    """Endpoint: /api/auth/register/vendedor/"""
    serializer_class = RegistroVendedorSerializer


class RegistroAdministradorView(RegistroBaseView):
    """Endpoint: /api/auth/register/admin/"""
    serializer_class = RegistroAdministradorSerializer


