
from django.apps import AppConfig


class ProductosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.productos'
    verbose_name = 'Gestión de Productos'
    
    def ready(self):
        """
        Se ejecuta cuando Django inicia.
        Aquí importamos las señales para que se registren.
        """
        # Importar señales para que se conecten los receivers
        import apps.bitacora.signals
