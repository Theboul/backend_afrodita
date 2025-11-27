from django.shortcuts import render

# Create your views here.
from rest_framework import viewsets
from .models import Envio, TipoEnvio
from .serializers import EnvioSerializer, TipoEnvioSerializer

class TipoEnvioViewSet(viewsets.ModelViewSet):
    queryset = TipoEnvio.objects.all()
    serializer_class = TipoEnvioSerializer


class EnvioViewSet(viewsets.ModelViewSet):
    queryset = Envio.objects.all()
    serializer_class = EnvioSerializer
