from rest_framework import status, viewsets
from rest_framework.response import Response
from rest_framework.decorators import action
from django.shortcuts import get_object_or_404
from django.db import transaction
from .models import Carrito, DetalleCarrito
from apps.productos.models import Producto
from .serializers import CarritoSerializer
from rest_framework.permissions import AllowAny

class CarritoViewSet(viewsets.ViewSet):
    """
    Controla el carrito del cliente: obtener, agregar, actualizar y eliminar.
    """
    permission_classes = [AllowAny]  # <-- permite pruebas sin login

    def get_carrito_cliente(self, cliente):
        carrito, _ = Carrito.objects.get_or_create(
            id_cliente=cliente,
            estado_carrito='ACTIVO'
        )
        return carrito

    def list(self, request):
        cliente = request.user.cliente if request.user.is_authenticated else None
        carrito = self.get_carrito_cliente(cliente)
        serializer = CarritoSerializer(carrito)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    @transaction.atomic
    def agregar(self, request):
        cliente = request.user.cliente if request.user.is_authenticated else None
        id_producto = request.data.get('id_producto')
        cantidad = int(request.data.get('cantidad', 1))

        producto = get_object_or_404(Producto, pk=id_producto)

        if producto.stock < cantidad:
            return Response(
                {'error': 'No hay suficiente stock disponible'},
                status=status.HTTP_400_BAD_REQUEST
            )

        carrito = self.get_carrito_cliente(cliente)
        detalle, creado = DetalleCarrito.objects.get_or_create(
            id_carrito=carrito,
            id_producto=producto,
            defaults={'cantidad': cantidad, 'precio_total': producto.precio * cantidad}
        )

        if not creado:
            nueva_cantidad = detalle.cantidad + cantidad
            if nueva_cantidad > producto.stock:
                return Response({'error': 'Stock insuficiente'}, status=status.HTTP_400_BAD_REQUEST)
            detalle.cantidad = nueva_cantidad
            detalle.precio_total = detalle.cantidad * producto.precio
            detalle.save()

        return Response(CarritoSerializer(carrito).data, status=status.HTTP_201_CREATED)
