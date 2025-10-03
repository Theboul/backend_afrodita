from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .utils import log_activity

User = get_user_model()

@receiver(post_save, sender=User)
def on_user_created(sender, instance, created, **kwargs):
    if not created:
        return
    desc = f'Usuario creado: {getattr(instance, "username", instance.pk)}'
    # Si la creación viene de un endpoint con request, podrías preferir insertar desde la vista
    log_activity('REGISTER', descripcion=desc, request=None, user_id=instance.pk)

@receiver(user_logged_in)
def on_user_logged_in(sender, request, user, **kwargs):
    log_activity('LOGIN', descripcion=f'Inicio de sesión: {user.username}', request=request, user_id=user.pk)

@receiver(user_logged_out)
def on_user_logged_out(sender, request, user, **kwargs):
    uid = getattr(user, 'pk', None)
    username = getattr(user, 'username', 'anon')
    log_activity('LOGOUT', descripcion=f'Cierre de sesión: {username}', request=request, user_id=uid)

@receiver(user_login_failed)
def on_login_failed(sender, credentials, request, **kwargs):
    attempted = credentials.get('username') or credentials.get('email') or 'unknown'
    log_activity('LOGIN_FAIL', descripcion=f'Intento fallido: {attempted}', request=request, user_id=None)