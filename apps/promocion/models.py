from django.db import models

from core.constants.promocion import PromotionStatus, PromotionType


class Promocion(models.Model):
    """
    Entidad de promoción. Gestiona descuentos y combos asociados a productos.
    """

    id_promocion = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=50)
    descripcion = models.TextField(null=True, blank=True)
    codigo_descuento = models.CharField(max_length=20, unique=True)

    tipo = models.CharField(
        max_length=20,
        choices=PromotionType.choices(),
        default=PromotionType.PORCENTAJE,
    )
    valor_descuento = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Porcentaje o monto según el tipo de promoción",
    )

    fecha_inicio = models.DateField(null=True, blank=True)
    fecha_fin = models.DateField(null=True, blank=True)
    estado = models.CharField(
        max_length=15,
        choices=PromotionStatus.choices(),
        default=PromotionStatus.ACTIVA,
    )

    productos = models.ManyToManyField(
        'productos.Producto',
        through='PromocionProducto',
        related_name='promociones',
        blank=True,
    )

    class Meta:
        db_table = 'promocion'
        managed = True
        ordering = ['-fecha_inicio', 'nombre']

    def __str__(self):
        return self.nombre


class PromocionProducto(models.Model):
    """
    Tabla intermedia para relacionar promociones con productos.
    Permite saber qué productos participan de cada promoción.
    """

    id = models.AutoField(primary_key=True)
    promocion = models.ForeignKey(
        Promocion,
        on_delete=models.CASCADE,
        db_column='id_promocion',
        related_name='promociones_productos',
    )
    producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.CASCADE,
        db_column='id_producto',
        related_name='productos_promocion',
    )

    class Meta:
        db_table = 'promocion_producto'
        managed = True
        unique_together = ('promocion', 'producto')

    def __str__(self):
        return f"{self.promocion} -> {self.producto}"
