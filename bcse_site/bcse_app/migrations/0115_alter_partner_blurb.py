# Generated by Django 3.2.11 on 2023-12-01 20:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0114_alter_userprofile_dietary_preference'),
    ]

    operations = [
        migrations.AlterField(
            model_name='partner',
            name='blurb',
            field=models.CharField(blank=True, help_text='Short callout blurb', max_length=1024, null=True),
        ),
    ]
