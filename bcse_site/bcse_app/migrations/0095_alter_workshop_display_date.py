# Generated by Django 3.2.11 on 2023-09-11 18:17

import ckeditor.fields
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0094_alter_workshop_display_date'),
    ]

    operations = [
        migrations.AlterField(
            model_name='workshop',
            name='display_date',
            field=ckeditor.fields.RichTextField(blank=True, help_text='For multi-day workshop, enter start and end times for each day', null=True),
        ),
    ]