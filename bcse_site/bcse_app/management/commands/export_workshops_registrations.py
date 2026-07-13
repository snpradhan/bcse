from django.core.management.base import BaseCommand
from bcse_app.cron import export_workshops_registrations

class Command(BaseCommand):

    def handle(self, *args, **options):
        export_workshops_registrations()
