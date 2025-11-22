from django.db import models

class TipoEnvio(models.Model):
    cod_tipo_envio = models.AutoField(primary_key=True)
    tipo = models.CharField(max_length=20)

    class Meta:
        db_table = 'tipo_envio'
        managed = False

    def __str__(self):
        return self.tipo


class Envio(models.Model):
    cod_envio = models.AutoField(primary_key=True)
    fecha_envio = models.DateField()
    costo = models.DecimalField(max_digits=10, decimal_places=2)
    estado_envio = models.CharField(max_length=15)

    cod_tipo_envio = models.ForeignKey(
        TipoEnvio,
        db_column='cod_tipo_envio',
        on_delete=models.CASCADE
    )

    id_direccion = models.ForeignKey(
        'usuarios.DireccionCliente',
        db_column='id_direccion',
        on_delete=models.CASCADE
    )

    class Meta:
        db_table = 'envio'
        managed = False

    def __str__(self):
        return f"Envío #{self.cod_envio}"