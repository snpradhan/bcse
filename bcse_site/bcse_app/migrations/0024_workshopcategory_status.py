# Generated by Django 3.2.11 on 2022-03-15 14:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0023_workshopregistrationsetting_survey_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='workshopcategory',
            name='status',
            field=models.CharField(choices=[('A', 'Active'), ('I', 'Inactive')], default='A', max_length=1),
        ),
    ]