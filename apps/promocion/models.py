from django.db import models

from django.db import models

class Promocion(models.Model):
    id_promocion = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(null=True, blank=True)
    codigo_descuento = models.CharField(max_length=20, unique=True)
    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(max_length=15, default='ACTIVA')

    class Meta:
        db_table = 'promocion'
        managed = False

    def __str__(self):
        return self.nombre
