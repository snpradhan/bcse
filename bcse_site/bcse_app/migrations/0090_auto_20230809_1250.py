# Generated by Django 3.2.11 on 2023-08-09 17:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0089_auto_20230809_1040'),
    ]

    operations = [
        migrations.AlterField(
            model_name='baxterboxcategory',
            name='name',
            field=models.CharField(help_text='Name of Baxter Box Category', max_length=256, unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='baxterboxsubcategory',
            unique_together={('category', 'name')},
        ),
    ]
