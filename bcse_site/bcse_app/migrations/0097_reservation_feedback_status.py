# Generated by Django 3.2.11 on 2023-09-15 15:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0096_auto_20230914_0949'),
    ]

    operations = [
        migrations.AddField(
            model_name='reservation',
            name='feedback_status',
            field=models.CharField(max_length=256, null=True),
        ),
    ]
