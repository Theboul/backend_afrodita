from django.db import models

# ==========================================================
# TABLA: medida
# ==========================================================
class Medida(models.Model):
    id_medida = models.AutoField(primary_key=True)
    medida = models.DecimalField(max_digits=4, decimal_places=2)
    descripcion = models.CharField(max_length=50, null=True, blank=True)
    unidad = models.CharField(max_length=10, null=True, blank=True)

    class Meta:
        db_table = 'medida'
        managed = False

    def __str__(self):
        return f"{self.medida} {self.unidad or ''}".strip()


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
        db_column='id_medida'
    )

    class Meta:
        db_table = 'configuracion_lente'
        managed = False

    def __str__(self):
        return f"{self.color} ({self.diametro} mm)"


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
        db_column='id_configuracion'
    )
    id_categoria = models.ForeignKey(
        'categoria.Categoria',
        on_delete=models.CASCADE,
        db_column='id_categoria',
        related_name='productos'
    )

    class Meta:
        db_table = 'producto'
        managed = False
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


# ==========================================================
# TABLA: imagen_producto
# ==========================================================
class ImagenProducto(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    id_producto = models.ForeignKey(
        Producto,
        on_delete=models.CASCADE,
        db_column='id_producto'
    )
    url = models.CharField(max_length=255)
    public_id = models.CharField(max_length=150, null=True, blank=True)
    formato = models.CharField(max_length=10, null=True, blank=True)
    es_principal = models.BooleanField(default=False)
    orden = models.SmallIntegerField(default=1)
    estado_imagen = models.CharField(max_length=10, default='ACTIVA')
    subido_por = models.IntegerField(null=True, blank=True)
    fecha_subida = models.DateTimeField(null=True, blank=True)
    fecha_actualizacion = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'imagen_producto'
        managed = False

    def __str__(self):
        return f"Imagen de {self.id_producto_id} ({self.url})"
