from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.views import APIView
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.db.models import Q

from core.constants import APIResponse, BitacoraActions
from apps.bitacora.services.logger import AuditoriaLogger
from apps.usuarios.models import Usuario

from .serializers import ReporteFiltroSerializer
from .services import NoDataForReport, ReportType, ReportesService


class ReportTypesView(APIView):
    """
    Devuelve el catálogo de tipos de reporte disponibles en el sistema.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, request):
        tipos = [
            {
                "codigo": codigo,
                "nombre": nombre,
                "descripcion": nombre,
                "soporta_exportacion": True,
            }
            for codigo, nombre in ReportType.choices()
        ]

        return APIResponse.success(
            message="Tipos de reporte disponibles.",
            data={"tipos": tipos},
        )


class GenerarReporteView(APIView):
    """
    Genera un reporte según el tipo y filtros proporcionados.
    Solo accesible para administradores.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request):
        serializer = ReporteFiltroSerializer(data=request.data)

        if not serializer.is_valid():
            return APIResponse.bad_request(
                message="Parámetros inválidos para generar el reporte.",
                errors=serializer.errors,
            )

        filtros = serializer.validated_data
        tipo_reporte = filtros.get("tipo_reporte")

        try:
            reporte = ReportesService.generar_reporte(tipo_reporte, filtros)
        except NoDataForReport as exc:
            return APIResponse.error(
                message=str(exc),
                status_code=404,
            )
        except ValueError as exc:
            return APIResponse.bad_request(message=str(exc))
        except Exception as exc:
            return APIResponse.server_error(
                message="Error al generar el reporte.",
                detail=exc,
            )

        # Registro opcional en bitácora
        try:
            AuditoriaLogger.registrar_evento(
                accion=BitacoraActions.VIEW_ACCESS,
                descripcion=f"Generación de reporte: {tipo_reporte}",
                ip=request.META.get("REMOTE_ADDR"),
                usuario=request.user if request.user.is_authenticated else None,
            )
        except Exception:
            # La bitácora no debe romper el flujo principal
            pass

        return APIResponse.success(
            message="Reporte generado correctamente.",
            data=reporte,
        )


class BitacoraActionsView(APIView):
    """
    Devuelve la lista completa de acciones de bit��cora disponibles
    para usar como filtro en el reporte de bit��cora.
    """

    permission_classes = [IsAuthenticated, IsAdminUser]

    def get(self, _request):
        acciones = [
            {"codigo": codigo, "descripcion": descripcion}
            for codigo, descripcion in BitacoraActions.choices()
        ]
        return APIResponse.success(
            message="Acciones de bit��cora disponibles.",
            data={"acciones": acciones},
        )


@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdminUser])
def buscar_usuarios(request):
    """
    Autocompletado de usuarios por nombre de usuario.

    Par��metros:
        - q: texto a buscar (icontains sobre nombre_usuario)
        - limit: m��ximo de resultados (opcional, por defecto 10)
    """
    termino = (request.query_params.get("q") or "").strip()
    limite = int(request.query_params.get("limit") or 10)
    limite = max(1, min(limite, 50))

    if not termino:
        return Response({"results": []})

    usuarios = (
        Usuario.objects.filter(
            Q(nombre_usuario__icontains=termino)
            | Q(nombre_completo__icontains=termino)
        )
        .order_by("nombre_usuario")[:limite]
    )

    data = [
        {
            "id_usuario": u.id_usuario,
            "nombre_usuario": u.nombre_usuario,
            "nombre_completo": u.nombre_completo,
            "correo": u.correo,
        }
        for u in usuarios
    ]

    return Response({"results": data})
