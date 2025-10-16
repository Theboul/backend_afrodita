from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager


# =====================================================
# MANAGER PERSONALIZADO
# =====================================================
class UsuarioManager(BaseUserManager):
    """Gestor para crear usuarios y superusuarios de forma segura."""

    def create_user(self, nombre_usuario, correo, contraseña=None, **extra_fields):
        if not correo:
            raise ValueError("El correo electrónico es obligatorio.")
        correo = self.normalize_email(correo)
        user = self.model(nombre_usuario=nombre_usuario, correo=correo, **extra_fields)
        user.set_password(contraseña)
        user.save(using=self._db)
        return user

    def create_superuser(self, nombre_usuario, correo, contraseña=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("estado_usuario", "ACTIVO")
        return self.create_user(nombre_usuario, correo, contraseña, **extra_fields)


# =====================================================
# MODELO ROL
# =====================================================
class Rol(models.Model):
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(max_length=20, unique=True)
    descripcion = models.TextField(null=True, blank=True)

    class Meta:
        db_table = "rol"
        managed = False

    def __str__(self):
        return self.nombre

# =====================================================
# MODELO USUARIO
# =====================================================
class Usuario(AbstractBaseUser, PermissionsMixin):
    id_usuario = models.AutoField(primary_key=True)
    nombre_completo = models.CharField(max_length=90)
    nombre_usuario = models.CharField(max_length=35, unique=True)
    correo = models.EmailField(max_length=100, unique=True)
    password = models.CharField(max_length=255)
    telefono = models.CharField(max_length=20, null=True, blank=True)
    sexo = models.CharField(max_length=1)
    fecha_registro = models.DateTimeField(default=timezone.now)
    estado_usuario = models.CharField(max_length=10, default="ACTIVO")
    id_rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, db_column="id_rol",
        null=True,
        blank=True
    )
    last_login = models.DateTimeField(null=True, blank=True)

    # Campos de recuperación de contraseña
    token_recuperacion = models.CharField(max_length=100, null=True, blank=True)
    token_expira = models.DateTimeField(null=True, blank=True)

    # Requeridos por Django
    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    groups = models.ManyToManyField(
        'auth.Group',
        related_name='usuario_set',   # cambia el nombre del reverso
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='usuario_perm_set',  # nombre único también
        blank=True
    )

    USERNAME_FIELD = "nombre_usuario"
    REQUIRED_FIELDS = ["correo", "nombre_completo"]

    objects = UsuarioManager()

    class Meta:
        db_table = "usuario"
        managed = False

    def __str__(self):
        return f"{self.nombre_usuario} ({self.id_rol.nombre if self.id_rol else 'Sin rol'})"


class Cliente(models.Model):
    id_cliente = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, db_column="id_cliente", primary_key=True
    )

    class Meta:
        db_table = "cliente"
        managed = False


class Vendedor(models.Model):
    id_vendedor = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, db_column="id_vendedor", primary_key=True
    )
    fecha_contrato = models.DateField(default=timezone.now)
    tipo_vendedor = models.CharField(max_length=10)

    class Meta:
        db_table = "vendedor"
        managed = False


class Administrador(models.Model):
    id_administrador = models.OneToOneField(
        Usuario, on_delete=models.CASCADE, db_column="id_administrador", primary_key=True
    )
    fecha_contrato = models.DateField(default=timezone.now)

    class Meta:
        db_table = "administrador"
        managed = False