# Generated by Django 3.2.11 on 2024-07-18 17:58

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0132_auto_20240627_1039'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='confirmation_email_dates',
            field=models.TextField(blank=True, null=True),
        ),
    ]
