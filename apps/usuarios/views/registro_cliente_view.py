from rest_framework.views import APIView
from rest_framework import status, permissions
from django.db import IntegrityError
from django.db.utils import OperationalError
from ..serializers import RegistroStep1Serializer, RegistroStep2Serializer
from apps.seguridad.models import Rol  # 🔄 Importar desde seguridad
from core.constants import APIResponse, Messages

# =====================================================
# PASO 1 — CREAR CREDENCIALES DE CLIENTE
# =====================================================
class RegistroClienteStep1View(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegistroStep1Serializer(data=request.data)
        if serializer.is_valid():
            return APIResponse.success(
                data=serializer.validated_data,
                message='Datos del paso 1 validados correctamente.'
            )
        return APIResponse.bad_request(
            message=Messages.INVALID_DATA,
            errors=serializer.errors
        )


# =====================================================
# PASO 2 — COMPLETAR PERFIL DE CLIENTE Y CREAR USUARIO
# =====================================================
class RegistroClienteStep2View(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegistroStep2Serializer(data=request.data)

        # Validar datos recibidos
        if not serializer.is_valid():
            return APIResponse.bad_request(
                message=Messages.INVALID_DATA,
                errors=serializer.errors
            )

        try:
            # Guardar cliente
            cliente = serializer.save()

            return APIResponse.created(
                data={'cliente': serializer.to_representation(cliente)},
                message=Messages.USER_CREATED
            )

        except Rol.DoesNotExist:
            return APIResponse.server_error(
                message='El rol CLIENTE no existe en la base de datos.'
            )

        except IntegrityError as e:
            return APIResponse.bad_request(
                message='El correo o nombre de usuario ya está registrado.',
                errors={'detail': str(e)}
            )

        except OperationalError as e:
            return APIResponse.server_error(
                message='Error de conexión con la base de datos.',
                detail=str(e)
            )

        except Exception as e:
            return APIResponse.server_error(
                message='Ocurrió un error inesperado al registrar el cliente.',
                detail=str(e)
            )