# Generated by Django 3.2.11 on 2023-11-02 18:57

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0101_auto_20231024_0900'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reservation',
            name='feedback_email_count',
            field=models.IntegerField(blank=True, null=True),
        ),
    ]
