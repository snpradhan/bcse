# Generated by Django 3.2.11 on 2024-09-16 13:54

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0143_workshop_featured'),
    ]

    operations = [
        migrations.AlterField(
            model_name='vignette',
            name='featured',
            field=models.BooleanField(default=False, help_text='If marked "Featured", this vignette will be displayed on the "Teacher Leadership Opportunities" page'),
        ),
        migrations.AlterField(
            model_name='workshop',
            name='featured',
            field=models.BooleanField(default=False, help_text='If marked "Featured", this workshop will be displayed under "Previous Workshops" tab'),
        ),
    ]
