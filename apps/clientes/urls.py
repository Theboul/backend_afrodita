from django.urls import path
from .views import RegistroStep1View, RegistroStep2View

urlpatterns = [
    path("registro/step1/", RegistroStep1View.as_view(), name="registro-step1"),
    path("registro/step2/", RegistroStep2View.as_view(), name="registro-step2"),
]
