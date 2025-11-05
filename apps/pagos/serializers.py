from rest_framework import serializers
from .models import MetodoPago

CATEGORIAS_VALIDAS = {"FISICO", "DIGITAL"}


class MetodoPagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = MetodoPago
        fields = [
            'id_metodo_pago', 'tipo', 'categoria', 'requiere_pasarela',
            'codigo_pasarela', 'descripcion', 'activo'
        ]
        read_only_fields = ['id_metodo_pago']

    def validate_tipo(self, value):
        tipo = value.strip().upper()
        if len(tipo) == 0:
            raise serializers.ValidationError('El tipo es obligatorio.')
        if len(tipo) > 30:
            raise serializers.ValidationError('El tipo no puede exceder 30 caracteres.')
        return tipo

    def validate_categoria(self, value):
        categoria = value.strip().upper()
        if categoria not in CATEGORIAS_VALIDAS:
            raise serializers.ValidationError('Categoría inválida. Use FISICO o DIGITAL.')
        return categoria

    def validate(self, attrs):
        requiere = attrs.get('requiere_pasarela', getattr(self.instance, 'requiere_pasarela', False))
        codigo = attrs.get('codigo_pasarela', getattr(self.instance, 'codigo_pasarela', None))
        if requiere and not (codigo and str(codigo).strip()):
            raise serializers.ValidationError({'codigo_pasarela': 'Requerido cuando requiere_pasarela es verdadero.'})
        return attrs