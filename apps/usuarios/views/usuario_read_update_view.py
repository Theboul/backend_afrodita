from rest_framework import generics, permissions
from ..models import Usuario
from ..serializers import UsuarioDetailSerializer, UsuarioUpdateSerializer


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
