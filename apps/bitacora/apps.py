from django.apps import AppConfig


class BitacoraConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.bitacora'

    def ready(self):
        import apps.bitacora.signals
