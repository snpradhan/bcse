# Generated by Django 3.2.11 on 2022-04-15 15:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0031_userprofile_subscribe'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userprofile',
            name='subscribe',
            field=models.BooleanField(blank=True, null=True),
        ),
    ]