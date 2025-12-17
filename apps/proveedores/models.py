from django.db import models


class Proveedor(models.Model):
    """
    Mapeo a la tabla existente `proveedor`.
    No se generan migraciones (managed=False).
    """
    cod_proveedor = models.CharField(primary_key=True, max_length=6)
    nombre = models.CharField(max_length=60)
    contacto = models.CharField(max_length=50)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    direccion = models.CharField(max_length=100, null=True, blank=True)
    pais = models.CharField(max_length=30, null=True, blank=True)
    tipo = models.CharField(max_length=30, null=True, blank=True)
    estado_proveedor = models.CharField(max_length=10, default='ACTIVO')

    class Meta:
        db_table = 'proveedor'
        managed = False
        ordering = ['nombre']

    def __str__(self):
        return f"{self.cod_proveedor} - {self.nombre}"

