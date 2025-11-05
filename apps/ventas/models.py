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
    id_venta = models.IntegerField(primary_key=True)
    monto_total = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    estado = models.CharField(max_length=20, null=True, blank=True)

    class Meta:
        db_table = 'venta'
        managed = False

    def __str__(self):
        return f"Venta {self.id_venta}"
