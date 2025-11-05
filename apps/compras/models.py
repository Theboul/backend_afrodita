from django.db import models


class Compra(models.Model):
    id_compra = models.AutoField(primary_key=True)
    fecha = models.DateField()
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    estado_compra = models.CharField(max_length=15)
    cod_proveedor = models.ForeignKey(
        'proveedores.Proveedor',
        to_field='cod_proveedor',
        db_column='cod_proveedor',
        on_delete=models.DO_NOTHING,
        related_name='compras'
    )

    class Meta:
        db_table = 'compra'
        managed = False
        ordering = ['-fecha', '-id_compra']

    def __str__(self):
        return f"OC #{self.id_compra} - {self.cod_proveedor_id}"

class DetalleCompra(models.Model):
    id_compra = models.ForeignKey(
        'Compra',
        db_column='id_compra',
        on_delete=models.CASCADE,
        related_name='items'
    )
    id_producto = models.ForeignKey(
        'productos.Producto',
        to_field='id_producto',
        db_column='id_producto',
        on_delete=models.CASCADE,
        related_name='detalles_compra'
    )
    cantidad = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    sub_total = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = 'detalle_compra'
        managed = False
        unique_together = (('id_compra', 'id_producto'),)

    def __str__(self):
        return f"OC {self.id_compra_id} - {self.id_producto_id} x{self.cantidad}"


class DevolucionCompra(models.Model):
    id_devolucion_compra = models.AutoField(primary_key=True)
    id_compra = models.ForeignKey(
        'Compra',
        db_column='id_compra',
        on_delete=models.CASCADE,
        related_name='devoluciones'
    )
    fecha_devolucion = models.DateField()
    motivo_general = models.TextField(null=True, blank=True)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    estado_devolucion = models.CharField(max_length=15, default='PENDIENTE')
    procesado_por = models.ForeignKey(
        'usuarios.Usuario',
        db_column='procesado_por',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='devoluciones_compra_procesadas'
    )

    class Meta:
        db_table = 'devolucion_compra'
        managed = False
        ordering = ['-id_devolucion_compra']

    def __str__(self):
        return f"DEV-C #{self.id_devolucion_compra} (OC {self.id_compra_id})"


class DetalleDevolucionCompra(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    id_devolucion_compra = models.ForeignKey(
        'DevolucionCompra',
        db_column='id_devolucion_compra',
        on_delete=models.CASCADE,
        related_name='items'
    )
    id_producto = models.ForeignKey(
        'productos.Producto',
        to_field='id_producto',
        db_column='id_producto',
        on_delete=models.CASCADE,
        related_name='items_devolucion_compra'
    )
    cantidad = models.IntegerField()
    precio_unit = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sub_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'detalle_devolucion_compra'
        managed = False
        ordering = ['id_detalle']

    def __str__(self):
        return f"DEV-C ITEM #{self.id_detalle} - {self.id_producto_id} x{self.cantidad}"
