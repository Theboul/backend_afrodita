# apps/carrito/services/stock_service.py
from apps.productos.models import Producto

def verificar_stock(producto_id: int, cantidad: int) -> bool:
    try:
        producto = Producto.objects.get(pk=producto_id)
        return producto.stock >= cantidad
    except Producto.DoesNotExist:
        return False
