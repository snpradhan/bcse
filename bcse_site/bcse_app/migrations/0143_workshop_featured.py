# Generated by Django 3.2.11 on 2024-09-09 18:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0142_surveysubmissionworkplace'),
    ]

    operations = [
        migrations.AddField(
            model_name='workshop',
            name='featured',
            field=models.BooleanField(default=False),
        ),
    ]