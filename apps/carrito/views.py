# apps/carrito/views.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.core.exceptions import ObjectDoesNotExist # <--- 1. IMPORTAR
from apps.productos.models import Producto
from .models import Carrito, DetalleCarrito
from .serializers import CarritoSerializer
# Asumo que la ruta de tu APIResponse es esta
from core.constants.responses import APIResponse 


# ==============================
# VER CARRITO ACTIVO DEL CLIENTE
# ==============================
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def carrito_ver(request):
    try:
        # 2. VALIDAR QUE EL USUARIO ES UN CLIENTE
        cliente = request.user.cliente
    except ObjectDoesNotExist:
        return APIResponse.forbidden("El usuario autenticado no tiene un perfil de cliente asociado.")

    carrito, _ = Carrito.objects.prefetch_related('detalles').get_or_create(
        id_cliente=cliente,
        estado_carrito='ACTIVO'
        # 3. prefetch_related('detalles') OPTIMIZA el serializer
    )
    data = CarritoSerializer(carrito).data
    return APIResponse.success("Carrito obtenido correctamente", data)


# ==============================
# AGREGAR PRODUCTO AL CARRITO
# ==============================
@api_view(['POST'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def carrito_agregar(request):
    try:
       
        cliente = request.user.cliente
    except ObjectDoesNotExist:
        return APIResponse.forbidden("El usuario autenticado no tiene un perfil de cliente asociado.")

    id_producto = request.data.get('id_producto')
    
   
    try:
        cantidad = int(request.data.get('cantidad', 1))
        if cantidad <= 0:
             return APIResponse.bad_request("La cantidad debe ser un número positivo.")
    except (ValueError, TypeError):
        return APIResponse.bad_request("La cantidad enviada no es un número entero válido.")

    if not id_producto:
        return APIResponse.bad_request("Debe indicar un 'id_producto'")

    producto = get_object_or_404(Producto, pk=id_producto)

   
    if producto.stock is None or producto.stock < cantidad:
        return APIResponse.bad_request(f"No hay suficiente stock disponible para '{producto.nombre}' (Stock: {producto.stock or 0})")

    carrito, _ = Carrito.objects.prefetch_related('detalles').get_or_create(
        id_cliente=cliente,
        estado_carrito='ACTIVO'
     
    )

    detalle, creado = DetalleCarrito.objects.get_or_create(
        id_carrito=carrito,
        id_producto=producto,
        defaults={'cantidad': cantidad, 'precio_total': producto.precio * cantidad}
    )

    if not creado:
        nueva_cantidad = detalle.cantidad + cantidad
        if producto.stock < nueva_cantidad:
            return APIResponse.bad_request(f"Stock insuficiente para '{producto.nombre}' al sumar al carrito (Stock: {producto.stock})")
        
        detalle.cantidad = nueva_cantidad
        detalle.precio_total = detalle.cantidad * producto.precio
        detalle.save()

    data = CarritoSerializer(carrito).data
    return APIResponse.created("Producto agregado al carrito", data)


# ==============================
# ACTUALIZAR CANTIDAD O ELIMINAR PRODUCTO
# ==============================
@api_view(['PUT'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def carrito_actualizar(request):
    try:
      
        cliente = request.user.cliente
    except ObjectDoesNotExist:
        return APIResponse.forbidden("El usuario autenticado no tiene un perfil de cliente asociado.")

    id_producto = request.data.get('id_producto')
    
    try:
        cantidad = int(request.data.get('cantidad', 0))
        if cantidad < 0:
             return APIResponse.bad_request("La cantidad no puede ser negativa.")
    except (ValueError, TypeError):
        return APIResponse.bad_request("La cantidad enviada no es un número entero válido.")

    if not id_producto:
        return APIResponse.bad_request("Debe indicar un 'id_producto'")

    producto = get_object_or_404(Producto, pk=id_producto)
    carrito = get_object_or_404(
        Carrito.objects.prefetch_related('detalles'), # 3. OPTIMIZAR
        id_cliente=cliente, 
        estado_carrito='ACTIVO'
    )

    try:
        detalle = DetalleCarrito.objects.get(id_carrito=carrito, id_producto=producto)
    except DetalleCarrito.DoesNotExist:
        return APIResponse.not_found("El producto no está en el carrito")

    if cantidad <= 0:
        detalle.delete()
        data = CarritoSerializer(carrito).data # Devolver el carrito actualizado
        return APIResponse.success("Producto eliminado del carrito", data)

    if producto.stock is None or cantidad > producto.stock:
        return APIResponse.bad_request(f"No hay suficiente stock disponible (Stock: {producto.stock or 0})")

    detalle.cantidad = cantidad
    detalle.precio_total = cantidad * producto.precio
    detalle.save()

    data = CarritoSerializer(carrito).data
    return APIResponse.success("Carrito actualizado correctamente", data)


# ==============================
# VACIAR CARRITO
# ==============================
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
@transaction.atomic
def carrito_vaciar(request):
    try:
      
        cliente = request.user.cliente
    except ObjectDoesNotExist:
        return APIResponse.forbidden("El usuario autenticado no tiene un perfil de cliente asociado.")

    carrito = get_object_or_404(
        Carrito.objects.prefetch_related('detalles'), 
        id_cliente=cliente, 
        estado_carrito='ACTIVO'
    )
    DetalleCarrito.objects.filter(id_carrito=carrito).delete()

    data = CarritoSerializer(carrito).data 
    return APIResponse.success("Carrito vaciado correctamente", data)