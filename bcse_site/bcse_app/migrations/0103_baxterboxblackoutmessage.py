# Generated by Django 3.2.11 on 2023-11-02 19:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0102_alter_reservation_feedback_email_count'),
    ]

    operations = [
        migrations.CreateModel(
            name='BaxterBoxBlackoutMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.CharField(max_length=2048)),
                ('status', models.CharField(choices=[('A', 'Active'), ('I', 'Inactive')], default='I', max_length=1)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
            ],
        ),
    ]