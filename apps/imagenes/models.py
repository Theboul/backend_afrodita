from django.db import models
from django.core.validators import MinValueValidator
import cloudinary
import cloudinary.uploader
import cloudinary.api

from core.constants import ImageStatus


class ImagenProducto(models.Model):
    id_imagen = models.AutoField(primary_key=True)
    id_producto = models.ForeignKey(
        'productos.Producto',
        on_delete=models.CASCADE,
        db_column='id_producto',
        related_name='imagenes'
    )
    url = models.CharField(max_length=255)
    public_id = models.CharField(max_length=150, unique=True)
    formato = models.CharField(max_length=10)
    es_principal = models.BooleanField(default=False)
    orden = models.SmallIntegerField(
        default=1,
        validators=[MinValueValidator(1)]
    )
    estado_imagen = models.CharField(
        max_length=10,
        choices=ImageStatus.choices(),
        default=ImageStatus.ACTIVA
    )
    subido_por = models.ForeignKey(
        'usuarios.Usuario',
        on_delete=models.SET_NULL,
        null=True,
        related_name='imagenes_subidas',
        db_column='subido_por'
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'imagen_producto'
        ordering = ['orden', 'id_imagen']
        unique_together = ('id_producto', 'orden')
        indexes = [
            models.Index(fields=['id_producto', 'es_principal']),
            models.Index(fields=['public_id']),
        ]

    def __str__(self):
        return f"Imagen {self.id_imagen} - {self.id_producto.nombre}"

    # ===============================
    # Métodos utilitarios Cloudinary
    # ===============================
    @staticmethod
    def subir_a_cloudinary(archivo, producto_id, orden=1):
        try:
            upload = cloudinary.uploader.upload(
                archivo,
                folder=f"afrodita/products/{producto_id}",
                public_id=f"{producto_id}_{orden}",
                overwrite=True,
                resource_type="image",
                transformation=[{'quality': 'auto'}, {'fetch_format': 'auto'}]
            )
            return {
                'url': upload['secure_url'],
                'public_id': upload['public_id'],
                'formato': upload['format'],
                'width': upload.get('width'),
                'height': upload.get('height'),
                'bytes': upload.get('bytes')
            }
        except Exception as e:
            raise ValueError(f"Error al subir imagen a Cloudinary: {str(e)}")

    def eliminar_de_cloudinary(self):
        try:
            result = cloudinary.uploader.destroy(self.public_id)
            return result.get('result') == 'ok'
        except Exception as e:
            print(f"Error al eliminar de Cloudinary: {e}")
            return False

    def marcar_como_principal(self):
        ImagenProducto.objects.filter(
            id_producto=self.id_producto,
            es_principal=True
        ).update(es_principal=False)
        self.es_principal = True
        self.save()

    def get_metadata(self):
        try:
            return cloudinary.api.resource(self.public_id)
        except Exception:
            return None
