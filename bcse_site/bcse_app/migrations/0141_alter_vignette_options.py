# Generated by Django 3.2.11 on 2024-08-28 12:27

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0140_vignette_order'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='vignette',
            options={'ordering': ['order']},
        ),
    ]
