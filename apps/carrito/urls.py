from django.urls import path
from .views import (
    carrito_ver,
    carrito_agregar,
    carrito_actualizar,
    carrito_vaciar
)

urlpatterns = [
    path('', carrito_ver, name='carrito_ver'),
    path('agregar/', carrito_agregar, name='carrito_agregar'),
    path('actualizar/', carrito_actualizar, name='carrito_actualizar'),
    path('vaciar/', carrito_vaciar, name='carrito_vaciar'),
]