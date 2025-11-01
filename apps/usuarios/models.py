from django.db import models
from django.utils import timezone
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager

from core.constants import UserStatus


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
        extra_fields.setdefault("estado_usuario", UserStatus.ACTIVO)
        return self.create_user(nombre_usuario, correo, contraseña, **extra_fields)


# =====================================================
# NOTA: El modelo Rol se movió a apps.seguridad.models
# Importar desde allí: from apps.seguridad.models import Rol
# =====================================================

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
    estado_usuario = models.CharField(max_length=10, default=UserStatus.ACTIVO)
    id_rol = models.ForeignKey(
        'seguridad.Rol',
        on_delete=models.SET_NULL, 
        db_column="id_rol",
        related_name='usuarios',
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
    
    # =====================================================
    # MÉTODOS DE GESTIÓN DE PERMISOS
    # =====================================================
    def obtener_todos_permisos(self):
        """
        Retorna TODOS los permisos del usuario.
        = Permisos del Rol + Permisos Individuales Concedidos - Permisos Revocados
        """
        from apps.seguridad.models import Permiso, UsuarioPermiso
        from django.db.models import Q
        
        permisos_finales = set()
        
        # 1. Permisos del rol (si tiene)
        if self.id_rol:
            permisos_rol = self.id_rol.obtener_permisos()
            permisos_finales.update(permisos_rol.values_list('codigo', flat=True))
        
        # 2. Permisos individuales vigentes
        permisos_individuales = UsuarioPermiso.objects.filter(
            usuario=self,
            activo=True
        ).filter(
            Q(fecha_expiracion__isnull=True) | 
            Q(fecha_expiracion__gt=timezone.now())
        ).select_related('permiso')
        
        # 3. Aplicar concesiones y revocaciones
        for up in permisos_individuales:
            if up.concedido:
                # Agregar permiso concedido
                permisos_finales.add(up.permiso.codigo)
            else:
                # Quitar permiso revocado
                permisos_finales.discard(up.permiso.codigo)
        
        return list(permisos_finales)
    
    def tiene_permiso(self, codigo_permiso):
        """Verifica si el usuario tiene un permiso específico"""
        return codigo_permiso in self.obtener_todos_permisos()
    
    def tiene_cualquier_permiso(self, *codigos_permisos):
        """Verifica si el usuario tiene AL MENOS uno de los permisos"""
        permisos_usuario = set(self.obtener_todos_permisos())
        return bool(permisos_usuario.intersection(codigos_permisos))
    
    def tiene_todos_permisos(self, *codigos_permisos):
        """Verifica si el usuario tiene TODOS los permisos especificados"""
        permisos_usuario = set(self.obtener_todos_permisos())
        return set(codigos_permisos).issubset(permisos_usuario)


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

# Direcciones de clientes 
class DireccionCliente(models.Model):
    id_direccion = models.AutoField(primary_key=True)
    id_cliente = models.ForeignKey(
        Cliente, 
        on_delete=models.CASCADE, 
        db_column="id_cliente",
        related_name='direcciones'  # <- Cliente.direcciones.all()
    )
    etiqueta = models.CharField(max_length=30, null=True, blank=True)
    direccion = models.CharField(max_length=100)
    ciudad = models.CharField(max_length=50, null=True, blank=True)
    departamento = models.CharField(max_length=50, null=True, blank=True)
    pais = models.CharField(max_length=50, null=True, blank=True)
    referencia = models.TextField(null=True, blank=True)
    es_principal = models.BooleanField(default=False)
    guardada = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'direccion_cliente'
        managed = False
        ordering = ['-es_principal', '-fecha_creacion']
        
    def __str__(self):
        return f"{self.etiqueta or 'Sin etiqueta'} - {self.direccion}"