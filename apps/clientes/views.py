from rest_framework.views import APIView
from rest_framework import status, viewsets
from rest_framework.response import Response
from .models import Cliente
from .serializers import RegistroStep1Serializer, RegistroStep2Serializer, ClienteSerializer

class RegistroStep1View(APIView):
    def post(self, request):
        serializer = RegistroStep1Serializer(data=request.data)
        if serializer.is_valid():
            return Response({"mensaje": "Credenciales válidas"}, status=status.HTTP_200_OK)
        return Response({"errores": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class RegistroStep2View(APIView):
    def post(self, request):
        serializer = RegistroStep2Serializer(data=request.data)
        if serializer.is_valid():
            cliente = serializer.save()
            return Response(
                {
                    "mensaje": f"¡Registro completado! Bienvenido {cliente.id_cliente.nombre_completo}",
                    "cliente": serializer.to_representation(cliente),
                },
                status=status.HTTP_201_CREATED,
            )
        return Response({"errores": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



class ClienteViewSet(viewsets.ModelViewSet):
    """
    CRUD automático de clientes:
    - GET /api/clientes/ → lista clientes
    - GET /api/clientes/{id}/ → detalle cliente
    - POST /api/clientes/ → crear cliente (solo Cliente, no hace registro de usuario)
    - PUT /api/clientes/{id}/ → actualizar cliente
    - DELETE /api/clientes/{id}/ → eliminar cliente
    """
    queryset = Cliente.objects.all()
    serializer_class = ClienteSerializer

