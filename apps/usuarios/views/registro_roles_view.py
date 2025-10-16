from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from ..serializers import (
    RegistroVendedorSerializer,
    RegistroAdministradorSerializer,
)


# =====================================================
# VISTA BASE GENÉRICA (REUTILIZABLE)
# =====================================================
class RegistroBaseView(APIView):
    """Clase base para crear usuarios según rol."""
    permission_classes = [permissions.AllowAny]
    serializer_class = None

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            usuario = serializer.save()
            rol_nombre = getattr(usuario.id_rol, "nombre", "Sin rol")
            return Response(
                {
                    "message": f"{usuario.id_rol.nombre if usuario.id_rol else 'Rol no asignado'} registrado correctamente.",
                    "usuario": {
                        "id_usuario": usuario.id_usuario,
                        "nombre_usuario": usuario.nombre_usuario,
                        "correo": usuario.correo,
                        "rol": rol_nombre,
                        "fecha_registro": usuario.fecha_registro,
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# REGISTRO DE VENDEDORES
# =====================================================
class RegistroVendedorView(RegistroBaseView):
    serializer_class = RegistroVendedorSerializer


# =====================================================
# REGISTRO DE ADMINISTRADORES
# =====================================================
class RegistroAdministradorView(RegistroBaseView):
    serializer_class = RegistroAdministradorSerializer
