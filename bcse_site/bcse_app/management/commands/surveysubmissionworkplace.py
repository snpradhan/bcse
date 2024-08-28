from django.core.management.base import BaseCommand
from bcse_app import models

class Command(BaseCommand):

    def handle(self, *args, **options):
        submissions = models.SurveySubmission.objects.all()
        for submission in submissions:
            if submission.user and submission.user.work_place:
                submission_work_place = models.SurveySubmissionWorkPlace(submission=submission, work_place=submission.user.work_place)
                submission_work_place.save()
