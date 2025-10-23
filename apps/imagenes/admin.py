from django.contrib import admin
from .models import ImagenProducto

@admin.register(ImagenProducto)
class ImagenProductoAdmin(admin.ModelAdmin):
    list_display = [
        'id_imagen', 'get_producto', 'url', 'es_principal', 
        'orden', 'estado_imagen', 'formato', 'fecha_subida'
    ]
    list_filter = ['es_principal', 'estado_imagen', 'formato']
    search_fields = ['url', 'public_id', 'id_producto__nombre']
    ordering = ['id_producto', 'orden']
    
    def get_producto(self, obj):
        return f"{obj.id_producto.id_producto} - {obj.id_producto.nombre}"
    get_producto.short_description = 'Producto'
