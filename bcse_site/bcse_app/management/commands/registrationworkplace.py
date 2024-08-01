from django.core.management.base import BaseCommand
from bcse_app import models

class Command(BaseCommand):

    def handle(self, *args, **options):
        registrations = models.Registration.objects.all()
        for registration in registrations:
            if registration.user.work_place:
                registration_work_place = models.RegistrationWorkPlace(registration=registration, work_place=registration.user.work_place)
                registration_work_place.save()
