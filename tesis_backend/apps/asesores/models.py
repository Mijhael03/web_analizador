from django.db import models

class Asesor(models.Model):
    name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    date_of_admission = models.DateField(auto_now_add=True)
    #cod_picture = models.IntegerField(auto_created=True)
    picture = models.ImageField(blank=True, null=True)

    def __str__(self):
        return self.nombre


class campaign(models.Model):
    cliente=models.CharField(max_length=100)
    SubCampaign=models.CharField(max_length=100)
    def __str__(self):
        return self.nombre