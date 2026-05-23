from django.db import models
from django.contrib.auth.models import User

class Profile(models.Model):
    user_name = models.CharField(max_length=100)
    email = models.CharField(max_length=100, blank=True, null=True)
    password = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f'{self.user_name} Profile'
