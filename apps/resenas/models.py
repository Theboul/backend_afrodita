from django.db import models

from core.constants import ReviewStatus


class Resena(models.Model):
    id_resena = models.AutoField(primary_key=True, db_column='id_reseña')
    id_producto = models.ForeignKey(
        'productos.Producto',
        to_field='id_producto',
        db_column='id_producto',
        on_delete=models.CASCADE,
        related_name='resenas'
    )
    id_cliente = models.ForeignKey(
        'usuarios.Cliente',
        db_column='id_cliente',
        on_delete=models.CASCADE,
        related_name='resenas'
    )
    calificacion = models.PositiveSmallIntegerField()
    comentario = models.TextField()
    estado = models.CharField(max_length=15, default=ReviewStatus.PENDIENTE)
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column='fecha_reseña')
    fecha_actualizacion = models.DateTimeField(auto_now=True, db_column='fecha_actualizacion')

    class Meta:
        db_table = 'reseña'
        managed = False  # apunta a tabla existente
        ordering = ['-fecha_creacion']

    def __str__(self):
        return f"Resena #{self.id_resena} - {self.id_producto_id}"

    @property
    def es_publica(self):
        return self.estado in ReviewStatus.visibles_publico()
