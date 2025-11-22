from django.db import models


class MetodoPago(models.Model):
    id_metodo_pago = models.IntegerField(primary_key=True)
    tipo = models.CharField(max_length=30)
    categoria = models.CharField(max_length=20, default='FISICO')
    requiere_pasarela = models.BooleanField(default=False)
    codigo_pasarela = models.CharField(max_length=30, null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = 'metodo_pago'
        managed = False
        ordering = ['id_metodo_pago']

    def __str__(self):
        return f"{self.id_metodo_pago} - {self.tipo}"


class PaymentState:
    PENDIENTE = 'PENDIENTE'
    COMPLETADO = 'COMPLETADO'
    FALLIDO = 'FALLIDO'
    CANCELADO = 'CANCELADO'


class PaymentTransaction(models.Model):
    id_transaccion = models.AutoField(primary_key=True)
    id_venta = models.IntegerField()
    id_metodo_pago = models.IntegerField()
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha_transaccion = models.DateTimeField()
    estado_transaccion = models.CharField(max_length=20, default=PaymentState.PENDIENTE)
    referencia_externa = models.CharField(max_length=100, null=True, blank=True)
    descripcion = models.TextField(null=True, blank=True)
    codigo_error = models.CharField(max_length=50, null=True, blank=True)
    procesado_por = models.IntegerField(null=True, blank=True)
    observacion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'transaccion_pago'
        managed = False
        ordering = ['-fecha_transaccion']

    def __str__(self):
        return f"{self.id_transaccion} - {self.referencia_externa or ''} [{self.estado_transaccion}] {self.monto}"


class Venta(models.Model):
    id_venta = models.AutoField(primary_key=True)
    fecha = models.DateField()
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    estado = models.CharField(max_length=15)

    id_metodo_pago = models.ForeignKey(
        'pagos.MetodoPago',
        db_column='id_metodo_pago',
        on_delete=models.CASCADE
    )

    cod_envio = models.ForeignKey(
        'envio.Envio',
        db_column='cod_envio',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    id_promocion = models.ForeignKey(
        'promocion.Promocion',
        db_column='id_promocion',
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    id_cliente = models.ForeignKey(
        'usuarios.Cliente',
        db_column='id_cliente',
        on_delete=models.CASCADE
    )

    id_vendedor = models.ForeignKey(
        'usuarios.Vendedor',
        db_column='id_vendedor',
        on_delete=models.CASCADE
    )

    class Meta:
        db_table = 'venta'
        managed = False

    def __str__(self):
        return f"Venta #{self.id_venta}"

class DetalleVenta(models.Model):
    id_detalle_venta = models.AutoField(primary_key=True)

    id_producto = models.ForeignKey(
        'productos.Producto',
        to_field='id_producto',
        db_column='id_producto',
        on_delete=models.CASCADE
    )
    id_venta = models.ForeignKey(
        Venta,
        db_column='id_venta',
        on_delete=models.CASCADE,
        related_name='detalles'
    )
    cantidad = models.IntegerField()
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    sub_total = models.DecimalField(max_digits=10, decimal_places=2)

    id_lote = models.ForeignKey(
        'lotes.Lote',
        db_column='id_lote',
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'detalle_venta'
        managed = False

    def __str__(self):
        return f"Detalle #{self.id_detalle_venta}"