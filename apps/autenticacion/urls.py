from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login_usuario, name="login_usuario"),
    path("logout/", views.logout_usuario, name="logout_usuario"),
    path("refresh/", views.refresh_token, name="refresh_token"),
    path("verificar-sesion/", views.verificar_sesion, name="verificar_sesion"),
]
