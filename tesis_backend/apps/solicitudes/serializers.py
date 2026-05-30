from rest_framework import serializers
from .models import Solicitud


class SolicitudSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source='id_user.user_name', read_only=True)

    class Meta:
        model = Solicitud
        fields = '__all__'
