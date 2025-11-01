from django.db import models
from django.conf import settings
from core.constants.acciones import BitacoraActions

class Bitacora(models.Model):
    """
    Modelo adaptado a la tabla existente `bitacora`,
    pero con mejoras modernas para auditoría y extensibilidad.
    """
    ACCIONES = BitacoraActions.choices()


    id_bitacora = models.AutoField(primary_key=True)
    fecha_hora = models.DateTimeField(auto_now_add=True, db_column="fecha_hora")
    accion = models.CharField(max_length=255, choices=ACCIONES)
    descripcion = models.TextField(blank=True, null=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    id_usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        db_column='id_usuario',
        related_name='bitacora_eventos',
        null=True,
        blank=True
    )

    class Meta:
        db_table = 'bitacora'
        ordering = ['-fecha_hora']

    def __str__(self):
        usuario = self.id_usuario.nombre_usuario if self.id_usuario else "Usuario anónimo"
        return f"{self.accion} - {usuario} - {self.fecha_hora}"