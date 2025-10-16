
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class AutenticacionConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.autenticacion"

    def ready(self):
        # Esto se ejecuta en el punto correcto del arranque de Django.
        try:
            from django.contrib.auth.signals import user_logged_in
            from django.contrib.auth.models import update_last_login
            user_logged_in.disconnect(update_last_login)
            logger.info("Desconectado update_last_login de user_logged_in (autenticacion).")
        except Exception:
            logger.exception("No se pudo desconectar update_last_login (posiblemente ya desconectado).")
