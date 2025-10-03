from django.shortcuts import render

# Create your views here.

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from .models import Producto
from .serializers import ProductoSerializer

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer
    permission_classes = [AllowAny]  # cambia a [AllowAny] si quieres abrirlo

    def perform_create(self, serializer):

        id_producto = serializer.validated_data.get("id_producto")
        if Producto.objects.filter(id_producto=id_producto).exists():
            raise serializer.ValidationError({"detail": "El ID del producto ya existe."})
        nombre = serializer.validated_data.get("nombre")
        if Producto.objects.filter(nombre__iexact=nombre).exists():
            raise serializer.ValidationError({"detail": "Ya existe un producto con ese nombre."})
        serializer.save()

    def destroy(self, request, *args, **kwargs):
        producto = self.get_object()
        # Ejemplo: en vez de borrar, cambiar estado
        if producto.estado_producto.lower() == "activo":
            producto.estado_producto = "inactivo"
            producto.save(update_fields=["estado_producto"])
            return Response(
                {"detail": "El producto tenía registros activos, se marcó como inactivo."},
                status=status.HTTP_409_CONFLICT
            )
        return super().destroy(request, *args, **kwargs)
