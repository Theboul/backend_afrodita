from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import DevolucionCompra
from .serializers import DevolucionCompraSerializer
from .services.devolucion_service import aprobar_devolucion, rechazar_devolucion


class CrearDevolucionView(generics.CreateAPIView):
    queryset = DevolucionCompra.objects.all()
    serializer_class = DevolucionCompraSerializer
    permission_classes = [IsAuthenticated]


class MisDevolucionesView(generics.ListAPIView):
    serializer_class = DevolucionCompraSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return DevolucionCompra.objects.filter(compra__usuario=self.request.user)


class TodasDevolucionesView(generics.ListAPIView):
    queryset = DevolucionCompra.objects.all()
    serializer_class = DevolucionCompraSerializer
    permission_classes = [IsAuthenticated]


class AprobarDevolucionView(generics.UpdateAPIView):
    queryset = DevolucionCompra.objects.all()
    serializer_class = DevolucionCompraSerializer
    

    def patch(self, request, pk):
        devolucion = self.get_object()
        devolver = aprobar_devolucion(devolucion)
        return Response(DevolucionCompraSerializer(devolver).data)


class RechazarDevolucionView(generics.UpdateAPIView):
    queryset = DevolucionCompra.objects.all()
    serializer_class = DevolucionCompraSerializer

    def patch(self, request, pk):
        devolucion = self.get_object()
        devolver = rechazar_devolucion(devolucion)
        return Response(DevolucionCompraSerializer(devolver).data)
