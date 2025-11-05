from django.db import models
from apps.productos.models import Producto
from apps.usuarios.models import Usuario


class Inventario(models.Model):
   
    id_inventario = models.AutoField(primary_key=True)
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        related_name="inventarios"
    )
    cantidad_actual = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=5)
    ubicacion = models.CharField(max_length=100, blank=True, null=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    usuario_actualiza = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="inventarios_actualizados"
    )

    class Meta:
        db_table = "inventario_inventario"   # 👈 para usar la tabla que ya existe
        verbose_name = "Inventario"
        verbose_name_plural = "Inventarios"
        ordering = ["-fecha_actualizacion"]

    def __str__(self):
        return f"{self.producto.nombre} ({self.cantidad_actual})"
