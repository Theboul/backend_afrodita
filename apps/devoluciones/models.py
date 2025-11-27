from django.db import models
from apps.compras.models import Compra   # AJUSTA si se llama diferente
from apps.productos.models import Producto
from apps.usuarios.models import Usuario


class DevolucionCompra(models.Model):
    ESTADO_CHOICES = (
        ("PENDIENTE", "Pendiente"),
        ("APROBADA", "Aprobada"),
        ("RECHAZADA", "Rechazada"),
    )

    id_devolucion_compra = models.AutoField(primary_key=True)
    compra = models.ForeignKey(
        Compra,
        on_delete=models.CASCADE,
        db_column="id_compra",
        related_name="devoluciones_compra",
    )
    fecha_devolucion = models.DateField()
    motivo_general = models.TextField()
    monto_total = models.DecimalField(max_digits=10, decimal_places=2)
    estado_devolucion = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="PENDIENTE"
    )
    procesado_por = models.ForeignKey(
        Usuario,
        on_delete=models.SET_NULL,
        null=True,
        db_column="procesado_por"
    )

    class Meta:
        db_table = "devolucion_compra"
        managed = False  # Ya existe en Neon

    def __str__(self):
        return f"Devolución #{self.id_devolucion_compra}"




class DetalleDevolucionCompra(models.Model):
    id_detalle = models.AutoField(primary_key=True)
    devolucion = models.ForeignKey(
        DevolucionCompra,
        on_delete=models.CASCADE,
        db_column="id_devolucion_compra",
        related_name="detalles"
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        db_column="id_producto"
    )
    cantidad = models.IntegerField()
    precio_unit = models.DecimalField(max_digits=10, decimal_places=2)
    sub_total = models.DecimalField(max_digits=10, decimal_places=2)
    observacion = models.TextField()

    class Meta:
        db_table = "detalle_devolucion_compra"
        managed = False

    def __str__(self):
        return f"Detalle #{self.id_detalle}"
