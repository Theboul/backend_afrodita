from rest_framework import serializers
from .models import Bitacora

class BitacoraSerializer(serializers.ModelSerializer):
    usuario = serializers.SerializerMethodField()

    class Meta:
        model = Bitacora
        fields = ["id_bitacora", "fecha_hora", "accion", "descripcion", "ip", "usuario"]

    def get_usuario(self, obj):
        return obj.id_usuario.nombre_usuario if obj.id_usuario else "Sistema"
