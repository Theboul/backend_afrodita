from django.db import models
from apps.productos.models import Producto  # importa si ya tienes el modelo Producto

class Lote(models.Model):
    id_lote = models.CharField(max_length=5, primary_key=True)
    cantidad = models.IntegerField()
    fecha_vencimiento = models.DateField()
    # Nota: si Producto.pk es 'id_producto' (CharField)
    producto = models.ForeignKey(
        Producto,
        to_field='id_producto',
        db_column='id_producto',
        on_delete=models.PROTECT,
        related_name='lotes'
    )

    class Meta:
        db_table = 'lote'
        ordering = ['fecha_vencimiento']
        managed = False
    def __str__(self):
        return f"{self.id_lote} - {self.producto_id}"
