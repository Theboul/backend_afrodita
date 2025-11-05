from django.db import transaction
from apps.carrito.models import Carrito, DetalleCarrito
from apps.productos.models import Producto
from .stock_service import verificar_stock


def eliminar_producto_de_carrito(cliente, id_producto):
    try:
        carrito = Carrito.objects.get(id_cliente=cliente, estado_carrito='activo')
        detalle = carrito.detalles.get(id_producto_id=id_producto)
        detalle.delete()
        return carrito
    except Carrito.DoesNotExist:
        raise ValueError("No existe un carrito activo.")
    except DetalleCarrito.DoesNotExist:
        raise ValueError("El producto no está en el carrito.")


@transaction.atomic
def agregar_producto_a_carrito(cliente, id_producto, cantidad):
    carrito, _ = Carrito.objects.get_or_create(
        id_cliente=cliente,
        estado_carrito='activo',
        defaults={'fecha_creacion': timezone.now()}
    )

    detalle, created = DetalleCarrito.objects.get_or_create(
        id_carrito=carrito,
        id_producto_id=id_producto,
        defaults={'cantidad': 0, 'precio_total': 0}
    )

    nueva_cantidad = detalle.cantidad + cantidad
    verificar_stock(id_producto, nueva_cantidad)

    producto = Producto.objects.get(id_producto=id_producto)
    detalle.cantidad = nueva_cantidad
    detalle.precio_total = nueva_cantidad * producto.precio
    detalle.save()

    return carrito
