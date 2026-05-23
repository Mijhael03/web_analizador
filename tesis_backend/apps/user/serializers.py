from rest_framework import serializers
from .models import Profile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = Profile
        fields = ['id', 'user_name', 'email', 'password']


class LoginSerializer(serializers.Serializer):
    user_name = serializers.CharField()
    password = serializers.CharField()
