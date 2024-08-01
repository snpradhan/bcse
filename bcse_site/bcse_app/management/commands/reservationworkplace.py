from django.core.management.base import BaseCommand
from bcse_app import models

class Command(BaseCommand):

    def handle(self, *args, **options):
        reservations = models.Reservation.objects.all()
        for reservation in reservations:
            if reservation.user.work_place:
                reservation_work_place = models.ReservationWorkPlace(reservation=reservation, work_place=reservation.user.work_place)
                reservation_work_place.save()
