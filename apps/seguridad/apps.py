from django.apps import AppConfig


class SeguridadConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.seguridad'
    verbose_name = 'Seguridad y Permisos'
    
    # NO necesita importar signals porque están en apps.bitacora.signals
    # Las señales se disparan desde views.py importándolas directamente de bitácora
