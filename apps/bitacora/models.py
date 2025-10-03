from django.db import models

# Create your models here.

from django.db import models

class Bitacora(models.Model):
    id_bitacora = models.BigAutoField(primary_key=True)
    fecha_hora = models.DateTimeField()
    accion = models.CharField(max_length=50)
    descripcion = models.TextField(null=True, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    id_usuario = models.IntegerField(null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'bitacora'