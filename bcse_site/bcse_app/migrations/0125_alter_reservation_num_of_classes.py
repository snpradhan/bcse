# Generated by Django 3.2.11 on 2024-02-08 17:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0124_surveysubmission_admin_notes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reservation',
            name='num_of_classes',
            field=models.CharField(choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', 'More than 4')], default=1, max_length=1),
            preserve_default=False,
        ),
    ]
