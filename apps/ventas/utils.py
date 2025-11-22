from apps.usuarios.models import Cliente
from apps.lotes.models import Lote
from django.db.models import Q


def buscar_cliente_por_texto(texto: str):
    if not texto:
        return None

    texto = texto.strip().lower()

    return Cliente.objects.filter(
        Q(nombre_completo__icontains=texto) |
        Q(correo__icontains=texto) |
        Q(telefono__icontains=texto)
    ).first()


def obtener_lote_fifo(id_producto, cantidad_requerida):
    """
    Devuelve los lotes necesarios para cubrir la venta,
    respetando FEFO/FIFO (orden por vencimiento primero).
    """
    lotes = (
        Lote.objects.filter(id_producto=id_producto, stock__gt=0)
        .order_by("fecha_vencimiento", "id_lote")
    )

    seleccionados = []
    cantidad_faltante = cantidad_requerida

    for lote in lotes:
        if cantidad_faltante <= 0:
            break

        usar = min(lote.stock, cantidad_faltante)  # elegir solo lo necesario
        seleccionados.append((lote, usar))
        cantidad_faltante -= usar

    if cantidad_faltante > 0:
        return None  # No alcanza el stock entre todos los lotes

    return seleccionados
