# Generated by Django 3.2.11 on 2023-02-02 15:00

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0069_baxterboxblackoutdate'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='more_num_of_classes',
            field=models.CharField(blank=True, help_text='Enter number of classes', max_length=3, null=True),
        ),
    ]
