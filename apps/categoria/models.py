from django.db import models

class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    id_catpadre = models.ForeignKey(
        'self',
        on_delete=models.DO_NOTHING,
        null=True,
        blank=True,
        db_column='id_catpadre',
        related_name='subcategorias'
    )
    estado_categoria = models.CharField(max_length=10, default='ACTIVA')


    class Meta:
        db_table = 'categoria'
        managed = False
        unique_together = ('nombre', 'id_catpadre')
        ordering = ['nombre']

    def __str__(self):
        return self.nombre
