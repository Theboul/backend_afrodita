import logging
from django.shortcuts import render

from django.contrib.auth import login as django_login, logout as django_logout
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.contrib.auth.hashers import check_password

from apps.clientes.models import Usuarios, Cliente
from apps.usuarios.models import Vendedor, Administrador
from apps.bitacora.utils import log_activity

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name="dispatch")
class LoginView(APIView):
    permission_classes = []  # público

    def post(self, request):
        try:
            login_id = (request.data.get("login") or "").strip()
            password = request.data.get("password")

            if not login_id or not password:
                # no intentar log_activity que a veces falla por esquema DB
                try:
                    log_activity('LOGIN_FAIL', descripcion='Login sin credenciales completas', request=request, user_id=None)
                except Exception:
                    logger.exception("log_activity fallo al registrar LOGIN_FAIL (incompleto).")
                return Response({"error": "Debe ingresar usuario/correo y contraseña."},
                                status=status.HTTP_400_BAD_REQUEST)

            # 1. Buscar por correo o username (case-insensitive)
            usuario = Usuarios.objects.filter(correo__iexact=login_id).first()
            if not usuario:
                usuario = Usuarios.objects.filter(nombre_usuario__iexact=login_id).first()
            if not usuario:
                try:
                    log_activity('LOGIN_FAIL', descripcion=f'Intento fallido - usuario no encontrado: {login_id}', request=request, user_id=None)
                except Exception:
                    logger.exception("log_activity fallo al registrar LOGIN_FAIL (usuario no encontrado).")
                return Response({"error": "Credenciales incorrectas."}, status=status.HTTP_401_UNAUTHORIZED)

            # 2. Verificar contraseña
            if not check_password(password, usuario.password):
                try:
                    log_activity('LOGIN_FAIL', descripcion=f'Intento fallido - credenciales incorrectas para: {login_id}', request=request, user_id=None)
                except Exception:
                    logger.exception("log_activity fallo al registrar LOGIN_FAIL (credenciales incorrectas).")
                return Response({"error": "Credenciales incorrectas."}, status=status.HTTP_401_UNAUTHORIZED)

            # 3. Verificar estado
            if usuario.estado_usuario == "BLOQUEADO":
                try:
                    log_activity('LOGIN_FAIL', descripcion=f'Intento bloqueo - cuenta bloqueada: {usuario.nombre_usuario}', request=request, user_id=usuario.id_usuario)
                except Exception:
                    logger.exception("log_activity fallo al registrar LOGIN_FAIL (bloqueado).")
                return Response({"error": "La cuenta está bloqueada"}, status=status.HTTP_403_FORBIDDEN)

            # 4. Crear sesión Django (cookie sessionid)
            if not hasattr(usuario, "backend"):
                usuario.backend = "django.contrib.auth.backends.ModelBackend"
            try:
                django_login(request, usuario)
            except ValueError as e:
                # fallback si algo intenta escribir campos inexistentes (protección adicional)
                logger.exception("ValueError en django_login (posible last_login faltante): %s", e)
                # aun así continuamos; la cookie sessionid normalmente ya se estableció
            except Exception as e:
                logger.exception("Error al ejecutar django_login: %s", e)
                try:
                    log_activity('LOGIN_ERROR', descripcion=f'Error al iniciar sesión: {str(e)}', request=request, user_id=usuario.id_usuario)
                except Exception:
                    logger.exception("log_activity fallo al registrar LOGIN_ERROR.")
                return Response({"error": "Error al iniciar sesión."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            # 5. Datos extra según rol (igual que antes)
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

            # 6. Registrar login en bitácora (si falla, no rompemos el login)
            try:
                log_activity('LOGIN', descripcion=f'Login exitoso: {usuario.nombre_usuario}', request=request, user_id=usuario.id_usuario)
            except Exception:
                logger.exception("log_activity fallo al registrar LOGIN (no crítico).")

            # 7. Respuesta
            return Response({
                "mensaje": "Inicio de sesión exitoso",
                "usuario": {
                    "id": usuario.id_usuario,
                    "nombre": usuario.nombre_completo,
                    "rol": usuario.rol
                },
                "extra": extra
            }, status=status.HTTP_200_OK)

        except Exception as exc:
            # registramos la traza completa en consola / logs
            logger.exception("Error inesperado en LoginView.post")
            # opcional: intentar registrar en bitacora que hubo un error de login
            try:
                log_activity('LOGIN_ERROR', descripcion=f'Error inesperado login: {str(exc)}', request=request, user_id=None)
            except Exception:
                logger.exception("log_activity fallo al registrar LOGIN_ERROR (no crítico).")
            return Response({"error": "Error interno al procesar login."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
