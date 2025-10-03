from django.db import models

# Create your models here.
from django.db import models

class Categoria(models.Model):
    id_categoria = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=40, unique=True)

    # Relación autorreferenciada (categoría padre)
    categoria_padre = models.ForeignKey(
        "self",
        db_column="id_catpadre",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="subcategorias"
    )

    def __str__(self):
        return self.nombre

    @property
    def codigo(self):
        return f"CAT-{self.id_categoria:03d}"

    def can_delete(self) -> bool:
        """
        Regla de negocio: 
        - No borrar si tiene subcategorías
        - No borrar si tiene productos asociados
        """
        if self.subcategorias.exists():
            return False
        if hasattr(self, "productos") and self.productos.filter(activo=True).exists():
            return False
        return True
    
    class Meta:
        managed = False         
        db_table = 'categoria' 