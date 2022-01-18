from django.shortcuts import render
from bcse_app import models, forms
from django import http, shortcuts, template
from django.contrib import auth, messages
from django.db.models import Q, F
import datetime
from .utils import Calendar
import calendar
from dateutil.relativedelta import relativedelta
# Create your views here.

from django.http import HttpResponse


def home(request):
  context = {}
  return render(request, 'bcse_app/Home.html', context)

def reservations(request):
  reservations = models.Reservation.objects.all()
  context = {'reservations': reservations}
  return render(request, 'bcse_app/Reservations.html', context)

def reservation(request, id=''):

  if '' != id:
    reservation = models.Reservation.objects.get(id=id)
  else:
    reservation = models.Reservation()

  if request.method == 'GET':
    form = forms.ReservationForm(instance=reservation)
    context = {'form': form}

    return render(request, 'bcse_app/Reservation.html', context)

  elif request.method == 'POST':
    data = request.POST.copy()
    only_checking_availability = int(data['checking_availability'])
    form = forms.ReservationForm(data, instance=reservation)
    if form.is_valid():
      equipment_types = form.cleaned_data['equipment_types']
      delivery_date = form.cleaned_data['delivery_date']
      start_date = delivery_date.replace(day=1)
      return_date = form.cleaned_data['return_date']
      end_date = return_date.replace(day=calendar.monthrange(return_date.year, return_date.month)[1])
      equipment_availability_matrix = check_availability(id, equipment_types, start_date, end_date, delivery_date, return_date)
      is_available = all([equipment_type['is_available'] for equipment_type in equipment_availability_matrix.values()])
      availability_calendar = []
      index_date = start_date
      while index_date <= end_date:
        cal = Calendar(index_date.year, index_date.month)
        availability_calendar.append(cal.formatmonth(withyear=True, availability_matrix=equipment_availability_matrix, delivery_date=delivery_date, return_date=return_date))
        index_date += relativedelta(months=1)

      if only_checking_availability:
        messages.info(request, "Selected equipment is %s for the selected dates" % ('available' if is_available else 'unavailable'))
        context = {'form': form, 'is_available': is_available, 'equipment_availability_matrix': equipment_availability_matrix,
                   'delivery_date': delivery_date, 'return_date': return_date, 'availability_calendar': availability_calendar,
                   'start_date': start_date, 'end_date': end_date}
        return render(request, 'bcse_app/Reservation.html', context)
      else:
        if is_available:
          savedReservation = form.save()
          savedReservation.equipment.clear()

          for equipment_type, availability in equipment_availability_matrix.items():
            savedReservation.equipment.add(availability['most_available_equip'])

          savedReservation.save()

          messages.success(request, "Reservation made")
          return shortcuts.redirect('bcse:reservation', id=savedReservation.id)
        else:
          messages.info(request, "Selected equipment is %s for the selected dates" % ('available' if is_available else 'unavailable'))
          context = {'form': form, 'is_available': is_available, 'equipment_availability_matrix': equipment_availability_matrix,
                   'delivery_date': delivery_date, 'return_date': return_date, 'availability_calendar': availability_calendar,
                   'start_date': start_date, 'end_date': end_date}
          return render(request, 'bcse_app/Reservation.html', context)

def check_availability(current_reservation_id, equipment_types, start_date, end_date, delivery_date, return_date):
  equipment_availability_matrix = {}
  delta = return_date - delivery_date
  reservation_days = delta.days + 1

  oneday = datetime.timedelta(days=1)

  #iterate each equipment type selected
  for equipment_type in equipment_types:
    equipment_availability_matrix[equipment_type] = {}
    equipment_availability_matrix[equipment_type]['most_available_equip'] = None
    equipment_availability_matrix[equipment_type]['most_available_days'] = None
    equipment_availability_matrix[equipment_type]['availability_dates'] = {}
    equipment_availability_matrix[equipment_type]['is_available'] = False

    #get all active equipment of the equipment type
    equipment = models.Equipment.objects.all().filter(equipment_type__id=equipment_type.id, status='A')
    #check if each copy of the equipment type is available on the selected dates
    most_available_equip = None
    most_available_days = 0
    for equip in equipment:
      index_date = start_date
      equipment_availability_matrix[equipment_type]['availability_dates'][equip] = {}
      available_days = 0
      while index_date <= end_date:
        reservations = models.Reservation.objects.all().filter(equipment=equip, delivery_date__lte=index_date, return_date__gte=index_date).exclude(status='N')
        if current_reservation_id != '':
          reservations = reservations.exclude(id=current_reservation_id)
        reservation_count = reservations.count()
        if reservation_count > 0:
          equipment_availability_matrix[equipment_type]['availability_dates'][equip][index_date] = False
        else:
          equipment_availability_matrix[equipment_type]['availability_dates'][equip][index_date] = True
          if index_date >= delivery_date and index_date <= return_date:
            available_days += 1

        index_date += oneday

      if available_days >= most_available_days:
        most_available_days = available_days
        most_available_equip = equip

    equipment_availability_matrix[equipment_type]['most_available_equip'] = most_available_equip
    equipment_availability_matrix[equipment_type]['most_available_days'] = most_available_days

    if reservation_days == most_available_days:
      equipment_availability_matrix[equipment_type]['is_available'] = True


  return equipment_availability_matrix


def workshop(request, id=''):

  workshop_registration_setting = None

  if '' != id:
    workshop = models.Workshop.objects.get(id=id)
    if workshop.enable_registration:
      workshop_registration_setting, created = models.WorkshopRegistrationSetting.objects.get_or_create(workshop=workshop)
  else:
    workshop = models.Workshop()

  if request.method == 'GET':
    form = forms.WorkshopForm(instance=workshop)

    context = {'form': form, 'workshop_registration_setting': workshop_registration_setting}

    return render(request, 'bcse_app/Workshop.html', context)

  elif request.method == 'POST':
    data = request.POST.copy()
    form = forms.WorkshopForm(data, instance=workshop)
    if form.is_valid():
      savedWorkshop = form.save()
      if savedWorkshop.enable_registration:
        workshop_registration_setting, created = models.WorkshopRegistrationSetting.objects.get_or_create(workshop=savedWorkshop)

      messages.success(request, "Workshop saved")
      return shortcuts.redirect('bcse:workshop', id=savedWorkshop.id)
    else:
      context = {'form': form, 'workshop_registration_setting': workshop_registration_setting}

      return render(request, 'bcse_app/Workshop.html', context)


def workshops(request):
  workshops = models.Workshop.objects.all()
  context = {'workshops': workshops}
  return render(request, 'bcse_app/Workshops.html', context)


def workshop_registration_setting(request, id=''):
  if '' != id:
    workshop_registration_setting = models.WorkshopRegistrationSetting.objects.get(id=id)
    workshop = workshop_registration_setting.workshop
  else:
    workshop_registration_setting = models.WorkshopRegistrationSetting()

  if request.method == 'GET':
    form = forms.WorkshopRegistrationSettingForm(instance=workshop_registration_setting)
    context = {'form': form, 'workshop': workshop}

    return render(request, 'bcse_app/WorkshopRegistrationSetting.html', context)

  elif request.method == 'POST':
    data = request.POST.copy()
    form = forms.WorkshopRegistrationSettingForm(data, instance=workshop_registration_setting)
    if form.is_valid():
      savedWorkshopRegistrationSetting = form.save()

      messages.success(request, "Workshop Registration Setting saved")
      return shortcuts.redirect('bcse:workshop_registration_setting', id=savedWorkshopRegistrationSetting.id)
    else:
      context = {'form': form, 'workshop': workshop}

      return render(request, 'bcse_app/WorkshopRegistrationSetting.html', context)

def workshop_registrants(request, id=''):
  workshop_registration_setting = models.WorkshopRegistrationSetting.objects.get(id=id)
  context = {'workshop_registration_setting': workshop_registration_setting}
  return render(request, 'bcse_app/WorkshopRegistrants.html', context)

