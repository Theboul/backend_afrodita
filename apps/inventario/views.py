from rest_framework import viewsets, permissions
from .models import Inventario
from .serializers import InventarioSerializer


class InventarioViewSet(viewsets.ModelViewSet):
    """
    CRUD completo de Inventario.
    GET     /api/inventario/           → listar
    POST    /api/inventario/           → crear
    GET     /api/inventario/{id}/      → detalle
    PUT     /api/inventario/{id}/      → actualizar
    PATCH   /api/inventario/{id}/      → actualizar parcial
    DELETE  /api/inventario/{id}/      → eliminar
    """
    queryset = Inventario.objects.select_related("producto", "usuario_actualiza").all()
    serializer_class = InventarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        """
        Cuando se cree un inventario desde el frontend,
        registramos quién lo creó (usuario autenticado).
        """
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(usuario_actualiza=user)

    def perform_update(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(usuario_actualiza=user)
