"""
Modelos para el sistema de roles y permisos.

Este módulo gestiona:
- Roles del sistema (ADMIN, VENDEDOR, CLIENTE)
- Permisos granulares por módulo
- Relación Rol-Permiso (permisos base del rol)
- Relación Usuario-Permiso (permisos individuales)
"""

from django.db import models
from django.utils import timezone


# =====================================================
# MODELO PERMISO
# =====================================================
class Permiso(models.Model):
    """
    Permisos granulares del sistema.
    
    Ejemplos:
    - productos.crear
    - productos.editar
    - usuarios.eliminar
    - reportes.ver_avanzados
    """
    id_permiso = models.AutoField(primary_key=True)
    nombre = models.CharField(
        max_length=100, 
        unique=True,
        help_text="Nombre único del permiso (ej: productos.crear)"
    )
    codigo = models.CharField(
        max_length=50,
        unique=True,
        help_text="Código interno del permiso (ej: PRODUCT_CREATE)"
    )
    descripcion = models.TextField(
        null=True, 
        blank=True,
        help_text="Descripción del permiso y su alcance"
    )
    modulo = models.CharField(
        max_length=50,
        help_text="Módulo al que pertenece (ej: productos, usuarios, ventas)"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Si está inactivo, el permiso no se puede asignar"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'permisos'
        managed = False
        verbose_name = 'Permiso'
        verbose_name_plural = 'Permisos'
        ordering = ['modulo', 'nombre']
        indexes = [
            models.Index(fields=['modulo']),
            models.Index(fields=['codigo']),
        ]
    
    def __str__(self):
        return f"{self.modulo} - {self.nombre}"


# =====================================================
# MODELO ROL (migrado desde usuarios)
# =====================================================
class Rol(models.Model):
    """
    Roles del sistema con sus permisos base.
    
    Roles predefinidos:
    - ADMINISTRADOR: Acceso completo
    - VENDEDOR: Gestión de ventas y productos
    - CLIENTE: Acceso a compras y perfil
    """
    id_rol = models.AutoField(primary_key=True)
    nombre = models.CharField(
        max_length=20, 
        unique=True,
        help_text="Nombre único del rol (ej: ADMINISTRADOR)"
    )
    descripcion = models.TextField(
        null=True, 
        blank=True,
        help_text="Descripción del rol y sus responsabilidades"
    )
    permisos = models.ManyToManyField(
        'Permiso',
        through='RolPermiso',
        related_name='roles',
        help_text="Permisos base que tiene este rol"
    )
    es_sistema = models.BooleanField(
        default=False,
        help_text="Roles del sistema no se pueden eliminar"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Si está inactivo, no se puede asignar a usuarios"
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_modificacion = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'rol'
        managed = False
        verbose_name = 'Rol'
        verbose_name_plural = 'Roles'
        ordering = ['nombre']
    
    def __str__(self):
        return self.nombre
    
    def obtener_permisos(self):
        """Retorna QuerySet de todos los permisos del rol"""
        return self.permisos.filter(activo=True)
    
    def tiene_permiso(self, codigo_permiso):
        """Verifica si el rol tiene un permiso específico"""
        return self.permisos.filter(
            codigo=codigo_permiso, 
            activo=True
        ).exists()


# =====================================================
# MODELO ROL-PERMISO (Relación Many-to-Many)
# =====================================================
class RolPermiso(models.Model):
    """
    Tabla intermedia para la relación Rol-Permiso.
    Define qué permisos tiene cada rol por defecto.
    """
    rol = models.ForeignKey(
        Rol, 
        on_delete=models.CASCADE,
        db_column='id_rol',
        related_name='asignaciones_permisos'
    )
    permiso = models.ForeignKey(
        'Permiso', 
        on_delete=models.CASCADE,
        db_column='id_permiso',
        related_name='asignaciones_roles'
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    asignado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='asignaciones_rol_permiso'
    )
    
    class Meta:
        db_table = 'rol_permiso'
        managed = False
        verbose_name = 'Rol-Permiso'
        verbose_name_plural = 'Roles-Permisos'
        unique_together = [['rol', 'permiso']]
        indexes = [
            models.Index(fields=['rol', 'permiso']),
        ]
    
    def __str__(self):
        return f"{self.rol.nombre} → {self.permiso.nombre}"


# =====================================================
# MODELO USUARIO-PERMISO (Permisos Individuales)
# =====================================================
class UsuarioPermiso(models.Model):
    """
    Permisos individuales asignados a usuarios específicos.
    
    Permite:
    - Conceder permisos adicionales a un usuario (concedido=True)
    - Revocar permisos del rol a un usuario (concedido=False)
    
    Ejemplos:
    - Vendedor con permiso extra de "editar_precios"
    - Admin temporal sin permiso de "eliminar_usuarios"
    """
    id_usuario_permiso = models.AutoField(primary_key=True)
    usuario = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.CASCADE,
        related_name='permisos_individuales'
    )
    permiso = models.ForeignKey(
        'Permiso',
        on_delete=models.CASCADE,
        related_name='asignaciones_usuarios'
    )
    concedido = models.BooleanField(
        default=True,
        help_text=(
            "True: Conceder permiso adicional | "
            "False: Revocar permiso del rol"
        )
    )
    fecha_asignacion = models.DateTimeField(auto_now_add=True)
    fecha_expiracion = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Fecha opcional de expiración del permiso"
    )
    asignado_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='permisos_asignados_a_otros'
    )
    motivo = models.TextField(
        null=True,
        blank=True,
        help_text="Razón por la cual se asignó/revocó el permiso"
    )
    activo = models.BooleanField(
        default=True,
        help_text="Permite desactivar temporalmente sin eliminar"
    )
    
    class Meta:
        db_table = 'usuario_permiso'
        managed = True
        verbose_name = 'Usuario-Permiso Individual'
        verbose_name_plural = 'Usuarios-Permisos Individuales'
        unique_together = [['usuario', 'permiso']]
        indexes = [
            models.Index(fields=['usuario', 'permiso']),
            models.Index(fields=['usuario', 'activo']),
            models.Index(fields=['fecha_expiracion']),
        ]
    
    def __str__(self):
        tipo = "Concedido" if self.concedido else "❌ Revocado"
        return f"{self.usuario.nombre_usuario} → {self.permiso.nombre} ({tipo})"
    
    def esta_vigente(self):
        """Verifica si el permiso está vigente (no expirado)"""
        if not self.activo:
            return False
        if self.fecha_expiracion:
            return timezone.now() <= self.fecha_expiracion
        return True
    
    def save(self, *args, **kwargs):
        """Validaciones antes de guardar"""
        # No permitir revocar permisos que el usuario no tiene por rol
        if not self.concedido:
            tiene_por_rol = False
            if self.usuario.id_rol:
                tiene_por_rol = self.usuario.id_rol.tiene_permiso(
                    self.permiso.codigo
                )
            if not tiene_por_rol:
                raise ValueError(
                    f"No se puede revocar el permiso '{self.permiso.nombre}' "
                    f"porque el usuario no lo tiene por su rol."
                )
        super().save(*args, **kwargs)
