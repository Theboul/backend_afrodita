from django.db import models
from apps.usuarios.models import Cliente
from apps.productos.models import Producto  

class Carrito(models.Model):
    id_carrito = models.AutoField(primary_key=True, db_column='id_carrito')
    fecha_creacion = models.DateTimeField(auto_now_add=True, db_column='fecha_creacion')
    estado_carrito = models.CharField(max_length=10, db_column='estado_carrito')
    id_cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        db_column='id_cliente'
    )

    class Meta:
        db_table = 'carrito'
        managed = False

  
    def __str__(self):
        return f"Carrito #{self.id_carrito} - Cliente {self.id_cliente_id}"


class DetalleCarrito(models.Model):

    
    id_detalle = models.AutoField(primary_key=True, db_column='id_detalle')
    

    id_carrito = models.ForeignKey(
        Carrito,
        related_name='detalles', 
        on_delete=models.CASCADE,
        db_column='id_carrito'
    )
    id_producto = models.ForeignKey(
        Producto,
        to_field='id_producto',
        db_column='id_producto',
        on_delete=models.CASCADE
    )
    cantidad = models.PositiveIntegerField(db_column='cantidad')
    precio_total = models.DecimalField(max_digits=10, decimal_places=2, db_column='precio_total')

    class Meta:
        db_table = 'detalle_carrito'
        managed = False
        unique_together = ('id_carrito', 'id_producto')

    def __str__(self):
        return f"{self.id_producto_id} x{self.cantidad}"