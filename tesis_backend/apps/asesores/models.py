from datetime import date
from django.db import models

class Asesor(models.Model):
    name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    date_of_admission = models.DateField(auto_now_add=True)
    picture = models.ImageField(blank=True, null=True)

    def __str__(self):
        return f"{self.name} {self.last_name}"


class Campaign(models.Model):
    cliente = models.CharField(max_length=100)
    subcampaign = models.CharField(max_length=100)

    class Meta:
        db_table = 'campaign'

    def __str__(self):
        return self.cliente


class Registro(models.Model):
    GENEROS = [
        ("masculino", "Masculino"),
        ("femenino", "Femenino"),
    ]
    ESTADOS_CIVILES = [
        ("soltero", "Soltero/a"),
        ("casado", "Casado/a"),
        ("conviviente", "Conviviente"),
        ("divorciado", "Divorciado/a"),
        ("viudo", "Viudo/a"),
    ]

    nombres = models.CharField(max_length=100)
    apellidos = models.CharField(max_length=100)
    edad = models.PositiveSmallIntegerField(blank=True, null=True)
    genero = models.CharField(max_length=20, choices=GENEROS, blank=True, null=True)
    estado_civil = models.CharField(max_length=20, choices=ESTADOS_CIVILES, blank=True, null=True)
    fecha_nacimiento = models.DateField()
    fecha_ingreso = models.DateField()
    cliente = models.CharField(max_length=100)
    campana = models.CharField(max_length=100)
    foto_perfil = models.ImageField(upload_to='fotos/', blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def calcular_edad(self):
        if not self.fecha_nacimiento:
            return None
        hoy = date.today()
        edad = hoy.year - self.fecha_nacimiento.year
        if (hoy.month, hoy.day) < (self.fecha_nacimiento.month, self.fecha_nacimiento.day):
            edad -= 1
        return edad

    def save(self, *args, **kwargs):
        self.edad = self.calcular_edad()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombres} {self.apellidos}"
