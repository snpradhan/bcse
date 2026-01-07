from django import template
from bcse_app import models, views, utils
from django.contrib import messages
import datetime
from django.db.models import Q
from django.utils import timezone
from collections import OrderedDict
import re
from itertools import chain

register = template.Library()

@register.filter
def get_item(dictionary, key):
  return dictionary.get(key)

@register.filter
def get_list_item(lst, index):
  return lst[index]

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
    reservations = models.Reservation.objects.all().filter(delivery_date__lte=datetime.datetime.now(), return_date__gte=datetime.datetime.now(), equipment__id=equipment.id).exclude(status='N')
    if reservations.count() == 1:
      return reservations[0].get_status_display()
    else:
      return 'Available'
  else:
    return 'Inactive'

@register.filter
def get_available_equipment_count(equipment_type):
  if equipment_type.status == 'A':
    total_equipment = models.Equipment.objects.all().filter(equipment_type__id=equipment_type.id, status='A').count()
    reserved_equipment = models.Reservation.objects.all().filter(delivery_date__lte=datetime.datetime.now(),
                                                           return_date__gte=datetime.datetime.now(),
                                                           equipment__equipment_type__id=equipment_type.id,
                                                           equipment__status='A'
                                                           ).exclude(status='N').count()
    return total_equipment - reserved_equipment
  else:
    return 0

@register.filter
def get_inactive_equipment_count(equipment_type):
  if equipment_type.status == 'A':
    inactive_equipment = models.Equipment.objects.all().filter(equipment_type__id=equipment_type.id, status='I').count()
    return inactive_equipment
  else:
    return 0

@register.filter
def get_reserved_equipment_count(equipment_type):
  if equipment_type.status == 'A':
    reserved_equipment = models.Reservation.objects.all().filter(delivery_date__lte=datetime.datetime.now(),
                                                           return_date__gte=datetime.datetime.now(),
                                                           equipment__equipment_type__id=equipment_type.id,
                                                           equipment__status='A'
                                                           ).exclude(status='N').count()
    return reserved_equipment
  else:
    return 0

@register.filter
def get_reservation_all_message_count(reservation, userProfile):
  total_message_count = 0

  if reservation and userProfile:
    reservation_messages = models.ReservationMessage.objects.all().filter(reservation=reservation)
    total_message_count = reservation_messages.count()

  return total_message_count

@register.filter
def get_reservation_new_message_count(reservation, userProfile):
  new_message_count = 0

  if reservation and userProfile:
    reservation_messages = models.ReservationMessage.objects.all().filter(reservation=reservation)
    new_message_count = reservation_messages.exclude(created_by=userProfile).exclude(viewed_by=userProfile).count()

  return new_message_count

@register.filter
def get_all_reservations_new_message_count(userProfile):
  new_message_count = 0

  if userProfile:
    reservation_messages = models.ReservationMessage.objects.all()
    if userProfile.user_role in ['T', 'P']:
      reservation_messages = reservation_messages.filter(reservation__user=userProfile)
    new_message_count = reservation_messages.exclude(created_by=userProfile).exclude(viewed_by=userProfile).count()

  return new_message_count

@register.filter
def get_days_of_week(daysofweek):
  days_of_week = []
  week_days=["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]
  for day in daysofweek:
    days_of_week.append(week_days[day])

  return "{} and {}".format(", ".join(days_of_week[:-1]),  days_of_week[-1])

@register.filter
def is_future(dt):
  if dt > datetime.datetime.now().date():
    return True
  else:
    return False

@register.filter
def is_past(dt):
  if dt < datetime.datetime.now().date():
    return True
  else:
    return False

@register.filter
def add_days_to_date(dt, days):
  abs_days = abs(days)
  delta = datetime.timedelta(days=abs(days))
  if days < 0:
    return dt - delta
  else:
    return dt + delta

@register.filter
def inline_style(html_string):
  return html_string.replace('<li', '<li style="margin:0;padding:0"')

@register.filter
def strip_html(html_string):
  return utils.strip_html(html_string)

@register.filter(name='split')
def split(value, arg):
    return value.split(arg)

@register.filter(name='splitlines')
def split(value):
    return value.splitlines()

@register.filter
def is_in(var, obj):
    return var in obj

@register.filter
def is_subset(set1, set2):
    return set(set1).issubset(set(set2))

@register.filter
def find_other_option(chosen, options):
  other_option = ''
  for choice in chosen:
    if choice not in options:
      other_option = choice
      break
  return other_option

@register.filter
def iterate(value):
  return list(range(1, value+1))

@register.filter
def replace_space(text, replacement):
  return text.replace(' ', replacement)


@register.simple_tag(takes_context=True)
def get_registration(context, workshop_id):
  request = context.get('request')
  return views.workshopRegistration(request, workshop_id)

@register.simple_tag(takes_context=True)
def get_user_registration(context, workshop_id, user_id):
  request = context.get('request')
  return views.userRegistration(request, workshop_id, user_id)

@register.simple_tag(takes_context=True)
def get_registration_breakdown(context, workshop_registration_setting):
  registrants = models.Registration.objects.filter(workshop_registration_setting=workshop_registration_setting)
  breakdown = {}
  for registrant in registrants:
    status = registrant.get_status_display()
    if status in breakdown:
      breakdown[status] += 1
    else:
      breakdown[status] = 1

  keys = list(breakdown.keys())
  keys.sort()
  sorted_breakdown = {i: breakdown[i] for i in keys}
  return sorted_breakdown

@register.simple_tag(takes_context=True)
def get_registration_attended_breakdown(context, workshop_registration_setting):
  registrants = models.Registration.objects.filter(workshop_registration_setting=workshop_registration_setting, status='T')
  breakdown = {}
  for registrant in registrants:
    sub_status = registrant.get_sub_status_display()
    if sub_status in breakdown:
      breakdown[sub_status] += 1
    else:
      breakdown[sub_status] = 1

  keys = list(breakdown.keys())
  keys.sort()
  sorted_breakdown = {i: breakdown[i] for i in keys}
  return sorted_breakdown


@register.simple_tag(takes_context=True)
def get_survey_submission_breakdown(context, survey):
  surveySubmissions = models.SurveySubmission.objects.filter(survey=survey)
  breakdown = {}
  for submission in surveySubmissions:
    status = submission.get_status_display()
    if status in breakdown:
      breakdown[status] += 1
    else:
      breakdown[status] = 1

  keys = list(breakdown.keys())
  keys.sort()
  sorted_breakdown = {i: breakdown[i] for i in keys}
  return sorted_breakdown

@register.simple_tag(takes_context=True)
def get_registrant_application(context, registration_id):
  request = context.get('request')
  applications = models.SurveySubmission.objects.all().filter(application_to_registration__registration__id=registration_id)
  if applications.count():
    return applications[0]
  else:
    return None

@register.simple_tag(takes_context=True)
def get_reservation_feedback(context, reservation_id):
  request = context.get('request')
  feedback = models.SurveySubmission.objects.all().filter(feedback_to_reservation__reservation__id=reservation_id).order_by('-created_date')
  if feedback.count():
    return feedback[0]
  else:
    return None

@register.simple_tag(takes_context=True)
def activate_reservation_feedback(context, reservation_id):
  request = context.get('request')
  reservation = models.Reservation.objects.get(id=reservation_id)
  #for reservations with return date, activate feedback link when it is marked completed
  if reservation.status == 'I':
    if reservation.return_date:
      return True
    else:
      #for reservations without return date, activate feedback link when it is marked complete and 14 days have passed since delivery date
      if reservation.delivery_date + datetime.timedelta(days=14) <= datetime.date.today():
        return True
      else:
        return False
  else:
    return False


@register.simple_tag(takes_context=True)
def get_baxterbox_feedback_survey(context):
  request = context.get('request')
  survey = models.Survey.objects.all().filter(status='A', survey_type='B').first()
  if survey:
    return survey
  else:
    return None


@register.simple_tag(takes_context=True)
def get_submission_connected_entity(context, submission_id):
  request = context.get('request')
  return views.get_submission_connected_entity(submission_id)

@register.simple_tag(takes_context=True)
def get_reservation_activity(context, reservation_id):
  request = context.get('request')
  reservation = models.Reservation.objects.get(id=reservation_id)
  if reservation.activity:
    return reservation.activity.name
  elif reservation.other_activity:
    return reservation.other_activity
  else:
    return None

@register.filter
def is_teacher_leader(userProfile):
  teacher_leader = models.TeacherLeader.objects.all().filter(teacher=userProfile, status='A')
  if teacher_leader.count() > 0:
    return True
  else:
    return False

@register.filter
def is_workshop_teacher_leader(workshop, userProfile):

  teacher_leader = models.TeacherLeader.objects.all().filter(teacher=userProfile, status='A', id__in=workshop.teacher_leaders.all())
  if teacher_leader.count() > 0:
    return True
  else:
    return False

@register.filter
def multiply(a, b):
  return a*b

@register.filter
def get_tag_dictionary(tags):
  return utils.get_tag_dictionary(tags)

@register.simple_tag(takes_context=True)
def is_activity_low_in_stock(context, id):
  request = context.get('request')
  return views.is_activity_low_in_stock(id)


@register.simple_tag(takes_context=True)
def get_low_stock_message(context, id):
  request = context.get('request')
  return views.get_low_stock_message(id)

@register.filter
def get_registrants_email(workshop_email):
  #get the receipients
  registration_email_addresses = None
  if workshop_email.registration_status or workshop_email.registration_sub_status:
    query_filter = Q(workshop_registration_setting__workshop__id=workshop_email.workshop.id)

    if workshop_email.registration_status:
      registration_status = workshop_email.registration_status.split(',')
      query_filter = query_filter & Q(status__in=registration_status)

    if workshop_email.registration_sub_status:
      registration_sub_status = workshop_email.registration_sub_status.split(',')
      query_filter = query_filter & Q(sub_status__in=registration_sub_status)

    if workshop_email.photo_release_incomplete:
      query_filter = query_filter & Q(user__photo_release_complete=False)


    registrations = models.Registration.objects.all().filter(query_filter)

    qs = registrations.values_list('user__user__email', 'user__secondary_email')
    registration_email_addresses = [email for email in chain.from_iterable(qs) if email]

  return registration_email_addresses



@register.filter
def get_reservation_equipment_types(reservation):
  equipment_type_ids = list(set(list(reservation.equipment.all().values_list('equipment_type', flat=True))))
  equipment_types = models.EquipmentType.objects.all().filter(id__in=equipment_type_ids)
  return equipment_types

@register.filter
def is_equipment_overbooked(equipment, reservation):
  overbooked = models.Reservation.objects.all().filter(Q(equipment=equipment), ~Q(status='N'), Q(Q(delivery_date__range=(reservation.delivery_date, reservation.return_date)) | Q(return_date__range=(reservation.delivery_date, reservation.return_date)))).exclude(id=reservation.id).distinct().count()
  if overbooked > 0:
    return True
  else:
    return False

@register.filter
def get_storage_label(key, default='Unknown'):
    return dict(models.INVENTORY_STORAGE_LOCATION).get(key, 'Unknown')


