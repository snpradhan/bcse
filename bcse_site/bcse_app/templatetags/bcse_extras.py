from django import template
from bcse_app import models, views
from django.contrib import messages
import datetime
from django.db.models import Q
from django.utils import timezone
from collections import OrderedDict

register = template.Library()

@register.filter
def get_item(dictionary, key):
  return dictionary.get(key)

@register.filter
def daterange(start_date, end_date):
  delta = end_date - start_date
  days = delta.days + 1
  for n in range(int(days)):
    yield start_date + datetime.timedelta(n)

@register.filter
def get_page_start_index(paginator, page_number):
  return paginator.page(page_number).start_index()

@register.filter
def get_page_end_index(paginator, page_number):
  return paginator.page(page_number).end_index()

@register.filter
def get_current_reservation_status(equipment):
  if equipment.status == 'A':
    reservations = models.Reservation.objects.all().filter(delivery_date__lte=datetime.datetime.now(), return_date__gte=datetime.datetime.now(), equipment__id=equipment.id)
    if reservations.count() == 1:
      return 'Checked Out'
    else:
      return 'Available'
  else:
    return 'Unavailable'

@register.filter
def get_available_equipment_count(equipment_type):
  if equipment_type.status == 'A':
    total_equipment = models.Equipment.objects.all().filter(equipment_type__id=equipment_type.id, status='A').count()
    checked_out_equipment = models.Reservation.objects.all().filter(delivery_date__lte=datetime.datetime.now(),
                                                           return_date__gte=datetime.datetime.now(),
                                                           equipment__equipment_type__id=equipment_type.id,
                                                           equipment__status='A'
                                                           ).count()
    return total_equipment - checked_out_equipment
  else:
    return 0

@register.filter
def get_unavailable_equipment_count(equipment_type):
  if equipment_type.status == 'A':
    unavailable_equipment = models.Equipment.objects.all().filter(equipment_type__id=equipment_type.id, status='I').count()
    return unavailable_equipment
  else:
    return 0

@register.filter
def get_checked_out_equipment_count(equipment_type):
  if equipment_type.status == 'A':
    checked_out_equipment = models.Reservation.objects.all().filter(delivery_date__lte=datetime.datetime.now(),
                                                           return_date__gte=datetime.datetime.now(),
                                                           equipment__equipment_type__id=equipment_type.id,
                                                           equipment__status='A'
                                                           ).count()
    return checked_out_equipment
  else:
    return 0

@register.filter
def get_reservation_all_message_count(reservation, userProfile):
  reservation_messages = models.ReservationMessage.objects.all().filter(reservation=reservation)
  total_message_count = reservation_messages.count()
  return total_message_count

@register.filter
def get_reservation_new_message_count(reservation, userProfile):
  reservation_messages = models.ReservationMessage.objects.all().filter(reservation=reservation)
  new_message_count = reservation_messages.exclude(created_by=userProfile).exclude(viewed_by=userProfile).count()
  return new_message_count

@register.filter
def get_all_reservations_new_message_count(userProfile):
  reservation_messages = models.ReservationMessage.objects.all()
  if userProfile.user_role in ['T', 'P']:
    reservation_messages = reservation_messages.filter(reservation__user=userProfile)
    print(reservation_messages)
  new_message_count = reservation_messages.exclude(created_by=userProfile).exclude(viewed_by=userProfile).count()
  return new_message_count
