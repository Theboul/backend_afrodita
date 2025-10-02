from django.db import models


class Usuarios(models.Model):
    id_usuario = models.AutoField(primary_key=True)
    nombre_completo = models.CharField(max_length=90)
    nombre_usuario = models.CharField(max_length=50)
    password = models.CharField(db_column="contraseña", unique=True, max_length=255)
    correo = models.CharField(unique=True, max_length=100)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    sexo = models.CharField(max_length=1)
    fecha_registro = models.DateTimeField()
    estado_usuario = models.CharField(max_length=10)
    rol = models.CharField(max_length=20)

    class Meta:
        managed = False
        db_table = "usuarios"


class Cliente(models.Model):
    id_cliente = models.OneToOneField(
        Usuarios,
        on_delete=models.DO_NOTHING,
        db_column="id_cliente",
        primary_key=True,
    )
    direccion = models.CharField(max_length=100)

    class Meta:
        managed = False
        db_table = "cliente"
