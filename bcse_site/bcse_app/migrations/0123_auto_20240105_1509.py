# Generated by Django 3.2.11 on 2024-01-05 21:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0122_remove_workshopcategory_audience'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='vignette',
            name='attachment',
        ),
        migrations.AddField(
            model_name='vignette',
            name='external_link',
            field=models.URLField(blank=True, max_length=2048, null=True),
        ),
    ]