# Generated by Django 3.2.11 on 2023-07-31 19:53

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0085_merge_20230731_1206'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reservation',
            name='status',
            field=models.CharField(choices=[('N', 'Cancelled'), ('I', 'Checked In'), ('O', 'Checked Out'), ('R', 'Confirmed'), ('U', 'Unconfirmed')], default='U', max_length=1),
        ),
    ]