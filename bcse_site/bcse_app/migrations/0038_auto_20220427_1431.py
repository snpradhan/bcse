# Generated by Django 3.2.11 on 2022-04-27 19:31

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0037_equipmenttype_short_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reservation',
            name='num_of_classes',
            field=models.CharField(blank=True, choices=[('1', '1'), ('2', '2'), ('3', '3'), ('4', '4'), ('5', 'More than 4')], max_length=1, null=True),
        ),
        migrations.AlterField(
            model_name='reservation',
            name='status',
            field=models.CharField(choices=[('D', 'Cancelled'), ('I', 'Checked In'), ('O', 'Checked Out'), ('R', 'Confirmed'), ('U', 'Unconfirmed')], default='R', max_length=1),
        ),
    ]
