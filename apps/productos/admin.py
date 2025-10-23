from django.contrib import admin
from .models import Producto, ConfiguracionLente, Medida

@admin.register(Medida)
class MedidaAdmin(admin.ModelAdmin):
    list_display = ['id_medida', 'medida', 'descripcion']
    search_fields = ['medida', 'descripcion']
    ordering = ['medida']


@admin.register(ConfiguracionLente)
class ConfiguracionLenteAdmin(admin.ModelAdmin):
    list_display = [
        'id_configuracion', 'color', 'curva', 'diametro', 
        'duracion_meses', 'material', 'get_medida'
    ]
    list_filter = ['color', 'material', 'duracion_meses']
    search_fields = ['id_configuracion', 'color', 'material']
    ordering = ['color', 'curva']
    
    def get_medida(self, obj):
        return f"{obj.id_medida.medida}"
    get_medida.short_description = 'Medida'


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = [
        'id_producto', 'nombre', 'precio', 'stock', 
        'estado_producto', 'get_categoria', 'tiene_stock', 
        'stock_bajo', 'fecha_creacion'
    ]
    list_filter = ['estado_producto', 'id_categoria', 'fecha_creacion']
    search_fields = ['id_producto', 'nombre', 'descripcion']
    ordering = ['-fecha_creacion', 'nombre']
    readonly_fields = ['fecha_creacion', 'ultima_actualizacion']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('id_producto', 'nombre', 'descripcion')
        }),
        ('Precio y Stock', {
            'fields': ('precio', 'stock', 'estado_producto')
        }),
        ('Categorización', {
            'fields': ('id_categoria', 'id_configuracion')
        }),
        ('Metadata', {
            'fields': ('fecha_creacion', 'ultima_actualizacion'),
            'classes': ('collapse',)
        }),
    )
    
    def get_categoria(self, obj):
        return obj.id_categoria.nombre if obj.id_categoria else 'Sin categoría'
    get_categoria.short_description = 'Categoría'
    
    def tiene_stock(self, obj):
        return '✅' if obj.tiene_stock else '❌'
    tiene_stock.short_description = 'Stock'
    tiene_stock.boolean = True
    
    def stock_bajo(self, obj):
        if obj.stock == 0:
            return '🔴'
        elif obj.stock_bajo:
            return '🟡'
        return '🟢'
    stock_bajo.short_description = 'Estado Stock'
