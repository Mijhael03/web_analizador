#!/usr/bin/env python3
import os
import sys
import django

sys.path.insert(0, "/home/mijhael/Desktop/Tesis_web/tesis_backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Tesis.settings")
django.setup()

from apps.asesores.models import Registro

registros = Registro.objects.all()
actualizados = 0

for r in registros:
    edad = r.calcular_edad()
    if edad != r.edad:
        r.edad = edad
        r.save(update_fields=["edad"])
        actualizados += 1

print(f"Registros procesados: {registros.count()}")
print(f"Registros actualizados: {actualizados}")
