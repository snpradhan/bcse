# Generated by Django 3.2.11 on 2022-04-28 11:42

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0038_auto_20220427_1431'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reservation',
            name='activity',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='bcse_app.activity'),
        ),
    ]