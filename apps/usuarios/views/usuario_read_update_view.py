from rest_framework import generics, permissions
from ..models import Usuario
from ..serializers import UsuarioDetailSerializer, UsuarioUpdateSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q
from apps.usuarios.models import Cliente


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def buscar_clientes(request):
    search = request.GET.get("search", "").strip()

    if not search:
        return Response({"data": []})

    clientes = Cliente.objects.filter(
        Q(id_cliente__nombre_completo__icontains=search) |
        Q(id_cliente__correo__icontains=search) |
        Q(id_cliente__telefono__icontains=search)
    ).values(
        "id_cliente",
        "id_cliente__nombre_completo",
        "id_cliente__correo",
        "id_cliente__telefono",
    )[:10]

    # Formatear para que el frontend reciba el formato esperado
    data = [
        {
            "id_cliente": c["id_cliente"],
            "nombre_completo": c["id_cliente__nombre_completo"],
            "correo": c["id_cliente__correo"],
            "telefono": c["id_cliente__telefono"],
        }
        for c in clientes
    ]

    return Response({"data": data})

# =====================================================
# LISTAR Y VER DETALLES DE USUARIOS
# =====================================================
class UsuarioListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Usuario.objects.all()
    serializer_class = UsuarioDetailSerializer


class UsuarioDetailView(generics.RetrieveAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Usuario.objects.all()
    serializer_class = UsuarioDetailSerializer
    lookup_field = "id_usuario"


# =====================================================
# ACTUALIZAR DATOS DE USUARIO
# =====================================================
class UsuarioUpdateView(generics.UpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    queryset = Usuario.objects.all()
    serializer_class = UsuarioUpdateSerializer
    lookup_field = "id_usuario"
