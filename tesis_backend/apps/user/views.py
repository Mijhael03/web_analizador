from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import Profile
from .serializers import ProfileSerializer, LoginSerializer


class ProfileViewSet(viewsets.ModelViewSet):
    queryset = Profile.objects.all()
    serializer_class = ProfileSerializer

    @action(detail=False, methods=['post'], url_path='login')
    def login(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        data = ser.validated_data
        try:
            profile = Profile.objects.get(
                user_name=data['user_name'],
                password=data['password'],
            )
            return Response({
                "id": profile.id,
                "user_name": profile.user_name,
                "email": profile.email,
            })
        except Profile.DoesNotExist:
            return Response(
                {"error": "Credenciales inválidas"},
                status=status.HTTP_401_UNAUTHORIZED,
            )
