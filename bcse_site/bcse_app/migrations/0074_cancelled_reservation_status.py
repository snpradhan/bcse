# Generated by Django 3.2.11 on 2023-05-10 15:09

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0073_reservation_email_sent'),
    ]

    operations = [
        migrations.RunSQL(
                "update bcse_app_reservation set status='N' where status='D'"
            ),
    ]