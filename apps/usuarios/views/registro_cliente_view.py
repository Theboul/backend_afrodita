from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from ..serializers import RegistroStep1Serializer, RegistroStep2Serializer


# =====================================================
# PASO 1 — CREAR CREDENCIALES DE CLIENTE
# =====================================================
class RegistroClienteStep1View(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegistroStep1Serializer(data=request.data)
        if serializer.is_valid():
            return Response(
                {
                    "message": "Datos del paso 1 validados correctamente.",
                    "data": serializer.validated_data,
                },
                status=status.HTTP_200_OK,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =====================================================
# PASO 2 — COMPLETAR PERFIL DE CLIENTE Y CREAR USUARIO
# =====================================================
class RegistroClienteStep2View(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegistroStep2Serializer(data=request.data)
        if serializer.is_valid():
            cliente = serializer.save()
            return Response(
                {
                    "message": "CLIENTE registrado correctamente.",
                    "cliente": serializer.to_representation(cliente),
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
