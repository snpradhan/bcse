from django.core.management.base import BaseCommand
from bcse_app import models

class Command(BaseCommand):

    def handle(self, *args, **options):
        reservations = models.Reservation.objects.all()
        for reservation in reservations:
            if reservation.activity and not reservation.activity_kit_not_needed and reservation.activity.consumables.all().count() > 0 and reservation.consumables.all().count() == 0:
                consumables = reservation.activity.consumables.all()
                reservation.consumables.add(*consumables)
                print(reservation.id, '%s consumables added' % consumables.count())
            else:
                print(reservation.id, 'consumables NOT added')
