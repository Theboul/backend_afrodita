from django.utils import timezone
from rest_framework import serializers
from ..models import Vendedor, Administrador
from apps.seguridad.models import Rol  # 🔄 Importar desde seguridad
from .usuario_base import UsuarioBaseSerializer

# =====================================================
# REGISTRO DE VENDEDORES
# =====================================================
class RegistroVendedorSerializer(UsuarioBaseSerializer):
    tipo_vendedor = serializers.CharField(max_length=10, default="INTERNO")

    class Meta(UsuarioBaseSerializer.Meta):
        fields = UsuarioBaseSerializer.Meta.fields + ["tipo_vendedor"]

    def create(self, validated_data):
        tipo_vendedor = validated_data.pop("tipo_vendedor")

        rol_vendedor = Rol.objects.get(nombre="VENDEDOR")

        usuario = self.create_usuario_base(validated_data, rol_vendedor)
        Vendedor.objects.create(
            id_vendedor=usuario,
            fecha_contrato=timezone.now().date(),
            tipo_vendedor=tipo_vendedor,
        )
        return usuario

# =====================================================
# REGISTRO DE ADMINISTRADORES
# =====================================================
class RegistroAdministradorSerializer(UsuarioBaseSerializer):
    def create(self, validated_data):

        rol_admin = Rol.objects.get(nombre="ADMINISTRADOR")
        
        usuario = self.create_usuario_base(validated_data, rol_admin)
        Administrador.objects.create(
            id_administrador=usuario,
            fecha_contrato=timezone.now().date(),
        )
        return usuario
