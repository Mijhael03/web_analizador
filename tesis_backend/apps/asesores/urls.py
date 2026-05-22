from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AsesorViewSet, CampaignViewSet, RegistroViewSet

router = DefaultRouter()
router.register(r'asesores', AsesorViewSet, basename='asesor')
router.register(r'campaigns', CampaignViewSet, basename='campaign')
router.register(r'registros', RegistroViewSet, basename='registro')

urlpatterns = [
    path('', include(router.urls)),
]
