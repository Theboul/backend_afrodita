from django.db import models

# Create your models here.

from django.db import models
from apps.clientes.models import Usuarios


class Vendedor(models.Model):
    id_vendedor = models.OneToOneField(
        Usuarios,
        on_delete=models.CASCADE,
        db_column="id_vendedor",
        primary_key=True
    )
    fecha_contrato = models.DateField()
    tipo_vendedor = models.CharField(max_length=8)

    class Meta:
        managed = False  # porque ya tienes la tabla creada
        db_table = "vendedor"


class Administrador(models.Model):
    id_administrador = models.OneToOneField(
        Usuarios,
        on_delete=models.CASCADE,
        db_column="id_administrador",
        primary_key=True
    )
    fecha_contrato = models.DateField()

    class Meta:
        managed = False
        db_table = "administrador"