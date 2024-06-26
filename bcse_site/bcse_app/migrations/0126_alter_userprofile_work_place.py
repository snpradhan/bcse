# Generated by Django 3.2.11 on 2024-02-28 16:45

import bcse_app.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0125_alter_reservation_num_of_classes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='work_place',
            field=models.ForeignKey(default=bcse_app.models.get_placeholder_workplace, on_delete=models.SET(bcse_app.models.get_placeholder_workplace), related_name='users', to='bcse_app.workplace'),
        ),
    ]
