from django.db import models


class MetodoPago(models.Model):
    id_metodo_pago = models.AutoField(primary_key=True)
    # Tabla real: columnas disponibles
    tipo = models.CharField(max_length=30)
    categoria = models.CharField(max_length=20)
    requiere_pasarela = models.BooleanField(db_column='requiere_pasarela', default=False)
    codigo_pasarela = models.CharField(max_length=30, null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'metodo_pago'
        managed = False
        ordering = ['tipo']

    def __str__(self):
        return f"{self.tipo} [{self.categoria}]"
   