# Generated by Django 3.2.11 on 2022-01-05 15:59

import bcse_app.models
import ckeditor.fields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import localflavor.us.models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('bcse_app', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkPlace',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(blank=True, help_text='Name of Work Place', max_length=256)),
                ('work_place_type', models.CharField(choices=[('S', 'School'), ('C', 'Company')], max_length=1)),
                ('district_number', models.CharField(blank=True, help_text='District Number for School', max_length=256, null=True)),
                ('hub', models.CharField(blank=True, choices=[('N', 'North'), ('C', 'Chicago')], help_text='Hub for School', max_length=1, null=True)),
                ('street_address_1', models.CharField(blank=True, help_text='Street Address 1', max_length=256, null=True)),
                ('street_address_2', models.CharField(blank=True, help_text='Street Address 2', max_length=256, null=True)),
                ('city', models.CharField(blank=True, help_text='City', max_length=256, null=True)),
                ('state', localflavor.us.models.USStateField(blank=True, help_text='State', max_length=2, null=True)),
                ('zip_code', models.CharField(blank=True, help_text='Zip Code of Work Place', max_length=256)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.CreateModel(
            name='WorkshopType',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='Name of Workshop Type', max_length=256)),
                ('icon', models.ImageField(blank=True, help_text='Upload an image that represents this Workshop Type', null=True, upload_to=bcse_app.models.upload_file_to)),
                ('description', ckeditor.fields.RichTextField(blank=True, null=True)),
                ('is_virtual', models.CharField(choices=[('I', 'In-Person'), ('V', 'Virtual')], max_length=1)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['title'],
            },
        ),
        migrations.AddField(
            model_name='equipment',
            name='created_date',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='equipment',
            name='modified_date',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='equipmenttype',
            name='created_date',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='equipmenttype',
            name='modified_date',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AlterField(
            model_name='equipment',
            name='status',
            field=models.CharField(choices=[('A', 'Active'), ('I', 'Inactive')], max_length=1),
        ),
        migrations.CreateModel(
            name='Workshop',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(help_text='Name of Workshop', max_length=256)),
                ('status', models.CharField(choices=[('A', 'Active'), ('I', 'Inactive')], max_length=1)),
                ('icon', models.ImageField(blank=True, help_text='Upload an image that represents this Workshop', null=True, upload_to=bcse_app.models.upload_file_to)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('workshop_type', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='workshop', to='bcse_app.workshoptype')),
            ],
            options={
                'ordering': ['-id'],
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_role', models.CharField(choices=[('A', 'Admin'), ('T', 'Teacher'), ('S', 'Staff')], max_length=1)),
                ('image', models.ImageField(blank=True, help_text='Profile image', null=True, upload_to=bcse_app.models.upload_file_to)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('work_place', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='users', to='bcse_app.workplace')),
            ],
        ),
    ]
