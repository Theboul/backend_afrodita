from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import BasePermission
from apps.clientes.models import Usuarios
from .serializers import (
    UsuarioCreateSerializer,
    UsuarioDetailSerializer,
    UsuarioUpdateSerializer
)

class IsAdministrador(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and getattr(request.user, "rol", "").upper() == "ADMINISTRADOR")

class UsuarioViewSet(viewsets.ModelViewSet):
    queryset = Usuarios.objects.all()

    permission_classes = []  # publico
    #permission_classes = [IsAuthenticated, IsAdministrador]  # solo usuarios logueados y que sean administradores

    def get_serializer_class(self):
        if self.action in ["list", "retrieve"]:
            return UsuarioDetailSerializer
        elif self.action in ["update", "partial_update"]:
            return UsuarioUpdateSerializer
        return UsuarioCreateSerializer
    
      # Crear usuario (bloquea clientes desde aquí)
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        rol = serializer.validated_data.get("rol", "").upper()
        if rol == "CLIENTE":
            return Response(
                {"error": "Los clientes deben registrarse desde el módulo de clientes."},
                status=status.HTTP_400_BAD_REQUEST
            )

        usuario = serializer.save()
        return Response(
            {"mensaje": f"Usuario {usuario.nombre_usuario} creado correctamente."},
            status=status.HTTP_201_CREATED
        )

    def destroy(self, request, *args, **kwargs):
        usuario = self.get_object()
        if usuario.rol == "ADMINISTRADOR" and usuario.id_usuario == 28:
            return Response(
                {"error": "No se puede eliminar el administrador principal."},
                status=status.HTTP_400_BAD_REQUEST
            )
        return super().destroy(request, *args, **kwargs)

    # Bloquear o desbloquear usuario
    def partial_update(self, request, *args, **kwargs):
        usuario = self.get_object()
        # ejemplo: bloquear/desbloquear
        estado = request.data.get("estado_usuario")
        if estado:
            usuario.estado_usuario = estado.upper()
            usuario.save()
            return Response({"mensaje": f"Usuario {usuario.nombre_usuario} actualizado correctamente. Estado: {usuario.estado_usuario}"})
        return super().partial_update(request, *args, **kwargs)

    