# Generated by Django 3.2.11 on 2022-07-12 19:09

from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('bcse_app', '0052_auto_20220712_1405'),
    ]

    operations = [
        migrations.CreateModel(
            name='SurveySubmission',
            fields=[
                ('UUID', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('created_date', models.DateTimeField(auto_now_add=True)),
                ('modified_date', models.DateTimeField(auto_now=True)),
                ('survey', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='survey_instance', to='bcse_app.survey')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='user_survey', to='bcse_app.userprofile')),
            ],
        ),
        migrations.CreateModel(
            name='SurveyResponse',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('response', models.TextField(blank=True, null=True)),
                ('responseFile', models.FileField(blank=True, null=True, upload_to='')),
                ('submission', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='survey_response', to='bcse_app.surveysubmission')),
                ('survey_component', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='survey_response', to='bcse_app.surveycomponent')),
            ],
        ),
    ]
