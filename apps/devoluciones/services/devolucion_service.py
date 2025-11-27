from django.utils import timezone
from apps.devoluciones.models import DevolucionCompra


def aprobar_devolucion(devolucion: DevolucionCompra, observacion: str | None = None):
    devolucion.estado_devolucion = "APROBADA"
    # si quieres guardar observación, tendríamos que tener un campo extra, por ahora lo omito
    devolucion.fecha_devolucion = devolucion.fecha_devolucion or timezone.now().date()
    devolucion.save()
    return devolucion


def rechazar_devolucion(devolucion: DevolucionCompra, observacion: str | None = None):
    devolucion.estado_devolucion = "RECHAZADA"
    devolucion.fecha_devolucion = devolucion.fecha_devolucion or timezone.now().date()
    devolucion.save()
    return devolucion
