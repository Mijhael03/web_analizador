from django.db import models


class Solicitud(models.Model):
    ESTADOS = ["espera","en proceso","completado"]

    codigo = models.CharField(max_length=10)
    status = models.CharField(max_length=10, choices=ESTADOS)
    id_user = models.CharField(max_length=10)
    
    def __str__(self):
        return f"Solicitud {self.pk} - {self.estado} - {self.ids_empleados}"
