# Generated by Django 3.2.11 on 2023-11-29 14:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0111_auto_20231117_0844'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='dietary_preference',
            field=models.CharField(blank=True, choices=[('V', 'Veg'), ('N', 'Non_veg'), ('D', 'Dairy-Free'), ('G', 'Gluten-Free')], max_length=1, null=True),
        ),
        migrations.AddField(
            model_name='workshopregistrationsetting',
            name='isbe_link',
            field=models.URLField(blank=True, null=True),
        ),
    ]
