from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from .models import Categoria
from .serializers import CategoriaSerializer


class CategoriaViewSet(viewsets.ModelViewSet):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer
    permission_classes = []

    def destroy(self, request, *args, **kwargs):
        categoria = self.get_object()
        if not categoria.can_delete():
            return Response(
                {"detail": "No se puede eliminar la categoría porque tiene subcategorías o productos activos."},
                status=status.HTTP_409_CONFLICT
            )
        return super().destroy(request, *args, **kwargs)
