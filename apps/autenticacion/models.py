from django.db import models
from django.conf import settings


class LoginAttempt(models.Model):
    """
    Modelo para registrar intentos de login (exitosos y fallidos).
    Útil para detectar ataques de fuerza bruta y auditoría.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='login_attempts'
    )
    ip = models.GenericIPAddressField(
        verbose_name="Dirección IP"
    )
    exitoso = models.BooleanField(
        default=False,
        verbose_name="¿Exitoso?"
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha y hora"
    )
    user_agent = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name="User Agent"
    )

    class Meta:
        db_table = 'login_attempts'
        verbose_name = 'Intento de Login'
        verbose_name_plural = 'Intentos de Login'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['ip', 'timestamp']),
            models.Index(fields=['usuario', 'timestamp']),
        ]

    def __str__(self):
        status = "Exitoso" if self.exitoso else "Fallido"
        usuario = self.usuario.nombre_usuario if self.usuario else "Desconocido"
        return f"{status} - {usuario} - {self.ip} - {self.timestamp}"

    @classmethod
    def obtener_intentos_fallidos_recientes(cls, ip, minutos=15):
        """
        Cuenta intentos fallidos desde una IP en los últimos X minutos.
        """
        from django.utils import timezone
        from datetime import timedelta
        
        limite_tiempo = timezone.now() - timedelta(minutes=minutos)
        return cls.objects.filter(
            ip=ip,
            exitoso=False,
            timestamp__gte=limite_tiempo
        ).count()


class IPBlacklist(models.Model):
    """
    Modelo para gestionar IPs bloqueadas.
    Útil para bloquear IPs con comportamiento sospechoso.
    """
    ip = models.GenericIPAddressField(
        unique=True,
        verbose_name="Dirección IP"
    )
    razon = models.TextField(
        verbose_name="Razón del bloqueo"
    )
    bloqueada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='ips_bloqueadas'
    )
    fecha_bloqueo = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Fecha de bloqueo"
    )
    activa = models.BooleanField(
        default=True,
        verbose_name="¿Activa?"
    )

    class Meta:
        db_table = 'ip_blacklist'
        verbose_name = 'IP Bloqueada'
        verbose_name_plural = 'IPs Bloqueadas'
        ordering = ['-fecha_bloqueo']

    def __str__(self):
        return f"{self.ip} - {'Activa' if self.activa else 'Inactiva'}"

    @classmethod
    def esta_bloqueada(cls, ip):
        """
        Verifica si una IP está bloqueada.
        """
        return cls.objects.filter(ip=ip, activa=True).exists()