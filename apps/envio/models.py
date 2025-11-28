from django.db import models
from apps.usuarios.models import DireccionCliente


class TipoEnvio(models.Model):
    cod_tipo_envio = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=20)

    class Meta:
        db_table = "tipo_envio"
        managed = False

    def __str__(self):
        return self.tipo


class Envio(models.Model):
    ESTADOS = [
        ("EN_PREPARACION", "En preparación"),
        ("EN_CAMINO", "En camino"),
        ("ENTREGADO", "Entregado"),
        ("CANCELADO", "Cancelado"),
    ]

    cod_envio = models.AutoField(primary_key=True)
    fecha_envio = models.DateField()
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    estado_envio = models.CharField(max_length=20, choices=ESTADOS)

    cod_tipo_envio = models.ForeignKey(
        TipoEnvio,
        on_delete=models.CASCADE,
        db_column="cod_tipo_envio"
    )

    id_direccion = models.ForeignKey(
        DireccionCliente,
        on_delete=models.CASCADE,
        db_column="id_direccion"
    )

    class Meta:
        db_table = "envio"
        managed = False

    def __str__(self):
        return f"Envio #{self.cod_envio}"
