from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.db import IntegrityError
from django.db.utils import OperationalError
from ..serializers import RegistroStep1Serializer, RegistroStep2Serializer
from apps.usuarios.models import Rol

# =====================================================
# PASO 1 — CREAR CREDENCIALES DE CLIENTE
# =====================================================
class RegistroClienteStep1View(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegistroStep1Serializer(data=request.data)
        if serializer.is_valid():
            return Response(
                {
                    "message": "Datos del paso 1 validados correctamente.",
                    "data": serializer.validated_data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# PASO 2 — COMPLETAR PERFIL DE CLIENTE Y CREAR USUARIO
# =====================================================
class RegistroClienteStep2View(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegistroStep2Serializer(data=request.data)

        # Validar datos recibidos
        if not serializer.is_valid():
            return Response(
                {
                    "success": False,
                    "message": "Errores en los datos enviados.",
                    "errors": serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            # Guardar cliente
            cliente = serializer.save()

            return Response(
                {
                    "success": True,
                    "message": "Cliente registrado correctamente.",
                    "cliente": serializer.to_representation(cliente),
                },
                status=status.HTTP_201_CREATED,
            )

        except Rol.DoesNotExist:
            return Response(
                {
                    "success": False,
                    "message": "El rol CLIENTE no existe en la base de datos.",
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except IntegrityError as e:
            # Maneja errores de duplicidad (correo o username únicos)
            return Response(
                {
                    "success": False,
                    "message": "El correo o nombre de usuario ya está registrado.",
                    "detail": str(e),
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        except OperationalError as e:
            # Error de conexión a la base de datos
            return Response(
                {
                    "success": False,
                    "message": "Error de conexión con la base de datos.",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        except Exception as e:
            # Cualquier otro error inesperado
            return Response(
                {
                    "success": False,
                    "message": "Ocurrió un error inesperado al registrar el cliente.",
                    "detail": str(e),
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )