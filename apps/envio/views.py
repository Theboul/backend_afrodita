from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework.decorators import api_view

from apps.envio.models import Envio, TipoEnvio
from apps.envio.serializers import EnvioSerializer, TipoEnvioSerializer

from apps.usuarios.models import DireccionCliente
from apps.ventas.models import Venta


class TipoEnvioViewSet(viewsets.ModelViewSet):
    queryset = TipoEnvio.objects.all()
    serializer_class = TipoEnvioSerializer


class EnvioViewSet(viewsets.ModelViewSet):
    queryset = Envio.objects.all()
    serializer_class = EnvioSerializer


@api_view(["GET"])
def listar_envios_detallados(request):

    envios = Envio.objects.all().order_by("-cod_envio")
    data = []

    for envio in envios:

        # Obtener dirección asociada al envío
        direccion = DireccionCliente.objects.filter(
            id_direccion=envio.id_direccion_id
        ).select_related("id_cliente__id_cliente").first()

        # Obtener datos del cliente (Usuario)
        usuario = direccion.id_cliente.id_cliente if direccion else None

        # Ventas del cliente usando id_usuario
        ventas_cliente = (
            Venta.objects.filter(id_cliente=usuario.id_usuario)
            if usuario else []
        )

        data.append({
            "cod_envio": envio.cod_envio,
            "fecha_envio": envio.fecha_envio,
            "estado_envio": envio.estado_envio,
            "tipo_envio": envio.cod_tipo_envio.tipo,

            "direccion": {
                "etiqueta": getattr(direccion, "etiqueta", None),
                "direccion": getattr(direccion, "direccion", None),
                "ciudad": getattr(direccion, "ciudad", None),
                "departamento": getattr(direccion, "departamento", None),
                "referencia": getattr(direccion, "referencia", None),
                "cliente_id": getattr(usuario, "id_usuario", None),
                "cliente_nombre": getattr(usuario, "nombre_completo", None),
                "cliente_correo": getattr(usuario, "correo", None),
                "cliente_telefono": getattr(usuario, "telefono", None),
            },

            "ventas": [
                {
                    "id_venta": v.id_venta,
                    "fecha": v.fecha,
                    "monto_total": v.monto_total,
                    "estado": v.estado,
                }
                for v in ventas_cliente
            ]
        })

    return Response({"success": True, "envios": data})
