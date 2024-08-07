# Generated by Django 3.2.11 on 2022-10-18 19:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0063_standalonepage_url_alias'),
    ]

    operations = [
        migrations.AddField(
            model_name='workplace',
            name='distance_from_base',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='workplace',
            name='latitude',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='workplace',
            name='longitude',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
        migrations.AddField(
            model_name='workplace',
            name='time_from_base',
            field=models.CharField(blank=True, max_length=256, null=True),
        ),
    ]
