# Generated by Django 3.2.11 on 2022-06-08 14:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0045_auto_20220527_1251'),
    ]

    operations = [
        migrations.AddField(
            model_name='workshopcategory',
            name='audience',
            field=models.CharField(choices=[('T', 'Teachers'), ('S', 'Students')], default='T', max_length=1),
        ),
    ]