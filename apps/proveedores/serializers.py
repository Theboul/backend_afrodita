from rest_framework import serializers
from .models import Proveedor
from core.constants import Messages


ESTADOS_VALIDOS = {'ACTIVO', 'INACTIVO', 'BLOQUEADO'}


class ProveedorListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = [
            'cod_proveedor', 'nombre', 'contacto', 'telefono', 'pais', 'estado_proveedor'
        ]


class ProveedorDetalleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = [
            'cod_proveedor', 'nombre', 'contacto', 'telefono', 'direccion', 'pais', 'estado_proveedor'
        ]


class CrearProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = [
            'cod_proveedor', 'nombre', 'contacto', 'telefono', 'direccion', 'pais', 'estado_proveedor'
        ]

    def validate_cod_proveedor(self, value):
        value = (value or '').strip().upper()
        if not value:
            raise serializers.ValidationError('El código de proveedor es requerido.')
        if len(value) > 6:
            raise serializers.ValidationError('El código de proveedor debe tener máximo 6 caracteres.')
        if Proveedor.objects.filter(cod_proveedor=value).exists():
            raise serializers.ValidationError('El código de proveedor ya existe.')
        return value

    def validate_estado_proveedor(self, value):
        val = (value or 'ACTIVO').upper()
        if val not in ESTADOS_VALIDOS:
            raise serializers.ValidationError('Estado de proveedor inválido.')
        return val

    def create(self, validated_data):
        # Normalizar código a mayúsculas
        validated_data['cod_proveedor'] = validated_data['cod_proveedor'].upper()
        return Proveedor.objects.create(**validated_data)


class ActualizarProveedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Proveedor
        fields = [
            'nombre', 'contacto', 'telefono', 'direccion', 'pais'
        ]

    def update(self, instance, validated_data):
        # Guardar cambios para auditoría (opcional)
        cambios = {}
        for field, new_value in validated_data.items():
            old_value = getattr(instance, field)
            if old_value != new_value:
                cambios[field] = {'anterior': old_value, 'nuevo': new_value}
            setattr(instance, field, new_value)
        instance.save()
        self.context['cambios'] = cambios
        return instance

