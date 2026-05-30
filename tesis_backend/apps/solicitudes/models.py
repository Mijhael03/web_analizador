from django.db import models

from apps.user.models import Profile


class Solicitud(models.Model):
    ESTADOS = [
        ("en espera", "En espera"),
        ("en proceso", "En proceso"),
        ("completado", "Completado"),
    ]

    codigo = models.CharField(max_length=10)
    status = models.CharField(max_length=20, choices=ESTADOS)
    id_user = models.ForeignKey(Profile, on_delete=models.CASCADE, db_column='id_user')
    json_data = models.JSONField(null=True)
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    resultado_excel = models.CharField(max_length=200, blank=True, null=True)
    mensaje_error = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Solicitud {self.pk} - {self.status}"
