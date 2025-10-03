from django.db import models

# Create your models here.

from apps.categoria.models import Categoria

class Medida(models.Model):
    id_medida = models.AutoField(primary_key=True)
    medida = models.DecimalField(max_digits=4, decimal_places=2)

    class Meta:
        managed = False
        db_table = "medida"

    def __str__(self):
        return str(self.medida)


class ConfiguracionLente(models.Model):
    id_configuracion = models.CharField(primary_key=True, max_length=5)
    color = models.CharField(max_length=20)
    curva = models.DecimalField(max_digits=4, decimal_places=2)
    diametro = models.DecimalField(max_digits=4, decimal_places=2)
    duracion_meses = models.SmallIntegerField()
    material = models.CharField(max_length=15)

    medida = models.ForeignKey(
        "Medida",
        db_column="id_medida",
        on_delete=models.CASCADE,
        related_name="configuraciones"
    )

    class Meta:
        managed = False
        db_table = "configuracion_lente"

    def __str__(self):
        return f"{self.id_configuracion} - {self.color} ({self.diametro} mm)"


class Producto(models.Model):
    id_producto = models.CharField(primary_key=True, max_length=5)
    nombre = models.CharField(max_length=50)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    descripcion = models.CharField(max_length=100)
    estado_producto = models.CharField(max_length=10)

    configuracion = models.ForeignKey(
        ConfiguracionLente,
        db_column="id_configuracion",
        on_delete=models.CASCADE,
        related_name="productos"
    )
    categoria = models.ForeignKey(
        Categoria,
        db_column="id_categoria",
        on_delete=models.CASCADE,
        related_name="productos"
    )

    class Meta:
        managed = False
        db_table = "producto"

    def __str__(self):
        return f"{self.nombre} ({self.id_producto})"
