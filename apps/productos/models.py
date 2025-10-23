from django.db import models

# ==========================================================
# TABLA: medida
# ==========================================================
class Medida(models.Model):
    id_medida = models.AutoField(primary_key=True)
    medida = models.DecimalField(max_digits=4, decimal_places=2)
    descripcion = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        db_table = 'medida'
        managed = False

    def __str__(self):
        return f"{self.medida}"


# ==========================================================
# TABLA: configuracion_lente
# ==========================================================
class ConfiguracionLente(models.Model):
    id_configuracion = models.CharField(primary_key=True, max_length=5)
    color = models.CharField(max_length=20)
    curva = models.DecimalField(max_digits=4, decimal_places=2)
    diametro = models.DecimalField(max_digits=4, decimal_places=2)
    duracion_meses = models.SmallIntegerField()
    material = models.CharField(max_length=15)
    id_medida = models.ForeignKey(
        Medida,
        on_delete=models.CASCADE,
        db_column='id_medida',
        related_name='configuraciones'
    )

    class Meta:
        db_table = 'configuracion_lente'
        managed = False

    def __str__(self):
        return f"{self.color} - Curva {self.curva} - Diámetro {self.diametro} - Medida {self.id_medida.medida}"


# ==========================================================
# TABLA: producto
# ==========================================================
class Producto(models.Model):
    id_producto = models.CharField(primary_key=True, max_length=5)
    nombre = models.CharField(max_length=50)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField()
    descripcion = models.CharField(max_length=100)
    estado_producto = models.CharField(max_length=10)
    id_configuracion = models.ForeignKey(
        ConfiguracionLente,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='id_configuracion',
        related_name='productos'
    )
    id_categoria = models.ForeignKey(
        'categoria.Categoria',
        on_delete=models.CASCADE,
        db_column='id_categoria',
        related_name='productos'
    )
    fecha_creacion = models.DateTimeField(null=True, blank=True)
    ultima_actualizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'producto'
        managed = False
        ordering = ['nombre']

    def __str__(self):
        return f"{self.id_producto} - {self.nombre}"

    @property
    def tiene_stock(self):
        """Verifica si el producto tiene stock disponible"""
        return self.stock > 0
    
    @property
    def stock_bajo(self):
        """Considera stock bajo si es menor a 10 unidades"""
        return 0 < self.stock < 10
    
    @property
    def esta_activo(self):
        """Verifica si el producto está activo"""
        return self.estado_producto == 'ACTIVO'
