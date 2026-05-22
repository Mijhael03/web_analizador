from django.core.files.base import ContentFile
from rest_framework import viewsets
from .models import Asesor, Campaign, Registro
from .serializers import AsesorSerializer, CampaignSerializer, RegistroSerializer

class AsesorViewSet(viewsets.ModelViewSet):
    queryset = Asesor.objects.all()
    serializer_class = AsesorSerializer

class CampaignViewSet(viewsets.ModelViewSet):
    queryset = Campaign.objects.all()
    serializer_class = CampaignSerializer

class RegistroViewSet(viewsets.ModelViewSet):
    queryset = Registro.objects.all()
    serializer_class = RegistroSerializer

    def perform_create(self, serializer):
        registro = serializer.save()
        if registro.foto_perfil:
            old_name = registro.foto_perfil.name
            ext = old_name.rsplit('.', 1)[-1]
            content = registro.foto_perfil.read()
            registro.foto_perfil.save(f'{registro.pk}.{ext}', ContentFile(content), save=True)
            if old_name != registro.foto_perfil.name:
                registro.foto_perfil.storage.delete(old_name)
