# Generated by Django 3.2.11 on 2022-04-18 14:51

import bcse_app.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0032_alter_userprofile_subscribe'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='activity',
            name='kit',
        ),
        migrations.AddField(
            model_name='activity',
            name='image',
            field=models.ImageField(blank=True, help_text='Upload an image that represents this Consumable Kit', null=True, upload_to=bcse_app.models.upload_file_to),
        ),
        migrations.AddField(
            model_name='activity',
            name='kit_name',
            field=models.CharField(default='abc', help_text='Name of the Consumable Kit', max_length=256),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='subscribe',
            field=models.BooleanField(default=False),
        ),
        migrations.DeleteModel(
            name='ActivityKit',
        ),
    ]
