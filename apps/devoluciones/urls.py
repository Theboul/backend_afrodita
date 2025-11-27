from django.urls import path
from .views import (
    CrearDevolucionView,
    MisDevolucionesView,
    TodasDevolucionesView,
    AprobarDevolucionView,
    RechazarDevolucionView,
)

urlpatterns = [
    path("crear/", CrearDevolucionView.as_view()),
    path("mias/", MisDevolucionesView.as_view()),
    path("todas/", TodasDevolucionesView.as_view()),
    path("<int:pk>/aprobar/", AprobarDevolucionView.as_view()),
    path("<int:pk>/rechazar/", RechazarDevolucionView.as_view()),
]
