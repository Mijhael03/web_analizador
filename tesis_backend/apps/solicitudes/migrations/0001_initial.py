from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('user', '0002_remove_profile_bio_remove_profile_birth_date_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='Solicitud',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=10)),
                ('status', models.CharField(choices=[('espera', 'Espera'), ('en proceso', 'En proceso'), ('completado', 'Completado')], max_length=10)),
                ('id_user', models.ForeignKey(db_column='id_user', on_delete=django.db.models.deletion.CASCADE, to='user.profile')),
            ],
            options={
                'db_table': 'solicitudes_solicitud',
            },
        ),
    ]
