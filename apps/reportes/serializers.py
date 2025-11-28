from rest_framework import serializers

from .services import Frequency, ReportType


class ReporteFiltroSerializer(serializers.Serializer):
    """
    Filtros genéricos para generación de reportes.

    Algunos campos solo aplican a ciertos tipos de reporte
    (por ejemplo, frecuencia para ventas, top para productos, etc.).
    """

    tipo_reporte = serializers.ChoiceField(choices=ReportType.choices())
    fecha_desde = serializers.DateField(required=False)
    fecha_hasta = serializers.DateField(required=False)

    # Ventas
    frecuencia = serializers.ChoiceField(
        choices=Frequency.choices(), required=False
    )

    # Productos más vendidos
    top = serializers.IntegerField(required=False, min_value=1, max_value=100)

    # Envíos
    estado_envio = serializers.CharField(required=False, allow_blank=True)

    # Inventario
    solo_stock_bajo = serializers.BooleanField(required=False)

    # Promociones
    estado_promocion = serializers.ChoiceField(
        choices=[("ACTIVAS", "Activas"), ("EXPIRADAS", "Expiradas"), ("TODAS", "Todas")],
        required=False,
    )

    # Ventas - filtros adicionales
    cliente = serializers.CharField(required=False, allow_blank=True)

    # Bitácora
    accion = serializers.CharField(required=False, allow_blank=True)
    usuario_id = serializers.IntegerField(required=False)

    # Formato de salida (por ahora solo JSON, pero se deja listo para exportación)
    formato = serializers.ChoiceField(
        choices=[("JSON", "JSON"), ("EXCEL", "Excel"), ("PDF", "PDF")],
        default="JSON",
    )

    def validate(self, attrs):
        fecha_desde = attrs.get("fecha_desde")
        fecha_hasta = attrs.get("fecha_hasta")

        if fecha_desde and fecha_hasta and fecha_desde > fecha_hasta:
            raise serializers.ValidationError(
                "La fecha_desde no puede ser mayor que fecha_hasta."
            )

        if attrs.get("tipo_reporte") == ReportType.VENTAS and not attrs.get(
            "frecuencia"
        ):
            attrs["frecuencia"] = Frequency.MENSUAL

        cliente = attrs.get("cliente")
        if isinstance(cliente, str):
            attrs["cliente"] = cliente.strip()

        return attrs


class TipoReporteSerializer(serializers.Serializer):
    codigo = serializers.CharField()
    nombre = serializers.CharField()
    descripcion = serializers.CharField()
    soporta_exportacion = serializers.BooleanField()
