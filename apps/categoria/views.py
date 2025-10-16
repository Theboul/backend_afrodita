from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated, IsAdminUser
from .models import Categoria
from .serializers import CategoriaSerializer


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    
    def get_permissions(self):
        """
        Permisos granulares por acción:
        - GET (list, retrieve): Cualquiera puede ver categorías
        - POST, PUT, PATCH, DELETE: Solo administradores
        """
        if self.action in ['list', 'retrieve']:
            permission_classes = [AllowAny]  # Para dashboard de usuarios anónimos
        else:
            permission_classes = [IsAuthenticated, IsAdminUser]  # Solo admins pueden crear/editar/eliminar
        
        return [permission() for permission in permission_classes]

    def destroy(self, request, *args, **kwargs):
        categoria = self.get_object()
        if not categoria.can_delete():
            return Response(
                {"detail": "No se puede eliminar la categoría porque tiene subcategorías o productos activos."},
                status=status.HTTP_409_CONFLICT
            )
        return super().destroy(request, *args, **kwargs)
