from django.shortcuts import render
from bcse_app import models, forms
from bcse_app.exceptions import CustomException
from django import http, shortcuts, template
from django.contrib import auth, messages
from django.contrib.auth.models import User
from django.db.models import Q, F
from django.db.models.functions import Lower
import datetime, time
from .utils import Calendar
import calendar
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.template.loader import render_to_string, get_template
import json
import csv
from django.utils.crypto import get_random_string
from django.contrib.sites.models import Site
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from django.core.files.base import ContentFile
import os
from mailchimp_marketing import Client
from mailchimp_marketing.api_client import ApiClientError
import hashlib
from django.db.models import Q, F, Max
from django.core.mail import EmailMessage
from django.contrib.sites.models import Site
import pyexcel
import boto3
from botocore.exceptions import ClientError
from django.forms import modelformset_factory
import uuid
from urllib.request import urlretrieve, urlcleanup
from django.core.files import File

# Create your views here.

from django.http import HttpResponse

####################################
# HOMEPAGE
####################################
def home(request):
  homepage_blocks = models.HomepageBlock.objects.all().filter(status='A').order_by('order')
  members = models.Team.objects.all().filter(status='A').order_by('order')
  context = {'homepage_blocks': homepage_blocks, 'members': members}
  return render(request, 'bcse_app/Home.html', context)

####################################
# ADMIN CONFIGURATION
####################################
@login_required
def adminConfiguration(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in 'AS':
      raise CustomException('You do not have the permission to access this configuration')

    context = {}
    return render(request, 'bcse_app/AdminConfiguration.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def aboutBCSE(request):
  context = {}
  return render(request, 'bcse_app/AboutBCSE.html', context)

def aboutCaseStudy(request):
  context = {}
  return render(request, 'bcse_app/AboutCaseStudy.html', context)

def aboutCenters(request):
  context = {}
  return render(request, 'bcse_app/AboutCenters.html', context)

def aboutPartners(request):
  partners = models.Partner.objects.all().filter(status='A').order_by('order')
  context = {'partners': partners}
  return render(request, 'bcse_app/AboutPartners.html', context)

def aboutTeam(request):
  members = models.Team.objects.all().filter(status='A').order_by('order')
  context = {'members': members}
  return render(request, 'bcse_app/AboutTeam.html', context)

def contactUs(request):
  context = {}
  return render(request, 'bcse_app/ContactUs.html', context)

####################################
# BAXTER BOX INFO
####################################
def baxterBoxInfo(request):
  try:
    activities = models.Activity.objects.all().filter(status='A')
    equipment_types = models.EquipmentType.objects.all().filter(status='A')
    context = {'activities': activities, 'equipment_types': equipment_types}
    return render(request, 'bcse_app/BaxterBoxInfo.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# CLASSROOM SUPPORT
####################################
def classroomSupport(request):
  try:
    context = {}
    return render(request, 'bcse_app/ClassroomSupport.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
####################################
# USER LOGIN
####################################
def userSignin(request, user_email=''):
  email = password = ''
  print(request.method)
  redirect_url = request.GET.get('next', '')
  if request.method == 'POST':
    data = request.POST.copy()
    form = forms.SignInForm(data)
    response_data = {}
    if form.is_valid():
      email = form.cleaned_data['email'].lower()
      password = form.cleaned_data['password']
      user = authenticate(username=email, password=password)

      if user.is_active:
        login(request, user)
        messages.success(request, "You have signed in")
        response_data['success'] = True
        response_data['redirect_url'] = redirect_url
      else:
        messages.error(request, 'Your account has not been activated')
        context = {'form': form, 'redirect_url': redirect_url}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/SignInModal.html', context, request)
    else:
      context = {'form': form, 'redirect_url': redirect_url}
      response_data['success'] = False
      response_data['html'] = render_to_string('bcse_app/SignInModal.html', context, request)

    return http.HttpResponse(json.dumps(response_data), content_type="application/json")
  elif request.method == 'GET':
    if user_email:
      form = forms.SignInForm(initial={'email': user_email})
    else:
      form = forms.SignInForm()
    context = {'form': form, 'redirect_url': redirect_url}
    return render(request, 'bcse_app/SignInModal.html', context)

  return http.HttpResponseNotAllowed(['GET', 'POST'])

####################################
# USER LOGOUT
####################################
@login_required
def userSignout(request):
  logout(request)
  messages.success(request, "You have signed out")
  return shortcuts.redirect('bcse:home')

####################################
# REGISTER
####################################
def userSignup(request):

  work_place = models.WorkPlace()
  ########### GET ###################
  if request.method == 'GET':

    if request.user.is_anonymous or request.user.userProfile.user_role in ['A', 'S']:
      form = forms.SignUpForm(user=request.user)
      work_place_form = forms.WorkPlaceForm(instance=work_place, prefix='work_place')
      context = {'form': form, 'work_place_form': work_place_form}
      return render(request, 'bcse_app/SignUpModal.html', context)
    else:
      raise CustomException('You cannot create another user account')


  elif request.method == 'POST':
    new_work_place = None
    response_data = {}

    form = forms.SignUpForm(user=request.user, files=request.FILES, data=request.POST)
    work_place_form = forms.WorkPlaceForm(data=request.POST, instance=work_place, prefix="work_place")

    if form.is_valid():
      # checking for bot signup
      # anonymous users signing up as teachers need to go through recaptcha validation
      if request.user.is_anonymous:
        recaptcha_response = request.POST.get('g-recaptcha-response')
        is_human = True #validate_recaptcha(request, recaptcha_response)
        if not is_human:
          context = {'form': form, 'work_place_form': work_place_form, 'recaptcha_error':  'Invalid reCAPTCHA'}
          response_data['success'] = False
          response_data['html'] = render_to_string('bcse_app/SignUpModal.html', context, request)
          return http.HttpResponse(json.dumps(response_data), content_type="application/json")

      user = User.objects.create_user(form.cleaned_data['email'].lower(),
                                      form.cleaned_data['email'].lower(),
                                      form.cleaned_data['password1'])
      user.first_name = form.cleaned_data['first_name']
      user.last_name = form.cleaned_data['last_name']
      user.is_active = True
      user.save()

      role = ''
      newUser = models.UserProfile()
      newUser.user_role = form.cleaned_data['user_role']
      newUser.iein = form.cleaned_data['iein']
      newUser.grades_taught = form.cleaned_data['grades_taught']
      newUser.phone_number = form.cleaned_data['phone_number']
      newUser.twitter_handle = form.cleaned_data['twitter_handle']
      newUser.instagram_handle = form.cleaned_data['instagram_handle']
      if request.FILES:
        newUser.image = request.FILES['image']
      if form.cleaned_data['subscribe']:
        newUser.subscribe = True

      if form.cleaned_data['user_role'] in ['A', 'S', 'T','P']:
        if form.cleaned_data['user_role'] in ['T','P']:
          newUser.validation_code = get_random_string(length=5)
          #get the work place id
          selected_work_place = form.cleaned_data['work_place']
          new_work_place_flag = form.cleaned_data['new_work_place_flag']
          if new_work_place_flag:
            if work_place_form.is_valid():
              #create a new school entry
              new_work_place = work_place_form.save(commit=False)
              if user.is_active:
                new_work_place.is_active = True
              new_work_place.save()
              newUser.work_place = new_work_place
            else:
              print(work_place_form.errors)
              user.delete()
              context = {'form': form, 'work_place_form': work_place_form, 'redirect_url': redirect_url}
              response_data['success'] = False
              response_data['html'] = render_to_string('bcse_app/SignUpModal.html', context, request)
              return http.HttpResponse(json.dumps(response_data), content_type="application/json")
          else:
            newUser.work_place = form.cleaned_data['work_place']

        newUser.user = user
        newUser.save()

      if form.cleaned_data['subscribe']:
        subscription(newUser, 'add')

      current_site = Site.objects.get_current()
      domain = current_site.domain

      #anonymous user creates an account
      if request.user.is_anonymous:
        #account type created is Teacher or Professional
        if form.cleaned_data['user_role'] in ['T', 'P']:
          #send an email with the validation code to validate the account
          #send_account_validation_email(newUser)
          response_data['success'] = True
          messages.success(request, 'Your account has been successfully created. You may now login with your email and password.')
          #messages.success(request, 'An email has been sent to %s to validate your account.  Please validate your account with in 24 hours.' % newUser.user.email);
        else:
          response_data['success'] = False
          messages.error(request, 'Sorry you cannot create this user account')
      else:
        messages.success(request, '%s account has been created.' % newUser.get_user_role_display())
        #send_account_by_admin_confirmation_email(newUser, form.cleaned_data['password1'])
        response_data['success'] = True

    else:
      print(form.errors)
      work_place_form.is_valid()
      context = {'form': form, 'work_place_form': work_place_form}
      response_data['success'] = False
      response_data['html'] = render_to_string('bcse_app/SignUpModal.html', context, request)

    return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  return http.HttpResponseNotAllowed(['GET', 'POST'])

####################################
# REDIRECT TO HOMEPAGE AFTER LOGIN
####################################
@login_required
def signinRedirect(request):
  messages.success(request, "You have signed in")
  return shortcuts.redirect('bcse:home')

####################################
# ACTIVITIES
####################################
@login_required
def activities(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view activities')

    activities = models.Activity.objects.all()
    context = {'activities': activities}
    return render(request, 'bcse_app/Activities.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# EDIT ACTIVITY
####################################
@login_required
def activityEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit activity')
    if '' != id:
      activity = models.Activity.objects.get(id=id)
    else:
      activity = models.Activity()

    if request.method == 'GET':
      form = forms.ActivityForm(instance=activity)
      context = {'form': form}
      return render(request, 'bcse_app/ActivityEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.ActivityForm(data, files=request.FILES, instance=activity)
      if form.is_valid():
        savedActivity = form.save()
        messages.success(request, "Activity saved")
        return shortcuts.redirect('bcse:activityEdit', id=savedActivity.id)
      else:
        print(form.errors)
        message.error(request, "Activity could not be saved. Check the errors below.")
        context = {'form': form}
        return render(request, 'bcse_app/ActivityEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# VIEW ACTIVITY
####################################
def activityView(request, id=''):

  try:
    if '' != id:
      activity = models.Activity.objects.get(id=id)
    else:
      raise CustomException('Activity does not exist')

    if request.method == 'GET':

      if request.is_ajax():
        context = {'activity': activity}
        if 'reservation' in request.META.get('HTTP_REFERER'):
          response_data = {}
          response_data['success'] = True
          response_data['kit_name'] = activity.kit_name
          response_data['html'] = render_to_string('bcse_app/ActivityView.html', context, request)
          return http.HttpResponse(json.dumps(response_data), content_type="application/json")
        else:
          context = {'title': activity.kit_name, 'kit': activity}
          return render(request, 'bcse_app/BaxterBoxKitModal.html', context)
      else:
        context = {'activity': activity}
        return render(request, 'bcse_app/ActivityBaseView.html', context)

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# DELETE ACTIVITY
####################################
@login_required
def activityDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete activity')
    if '' != id:
      activity = models.Activity.objects.get(id=id)
      activity.delete()
      messages.success(request, "Activity deleted")

    return shortcuts.redirect('bcse:activities')

  except models.Activity.DoesNotExist:
    messages.success(request, "Activity not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################
# EQUIPMENT TYPES
####################################
@login_required
def equipmentTypes(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view equipment types')

    equipment_types = models.EquipmentType.objects.all()
    context = {'equipment_types': equipment_types}
    return render(request, 'bcse_app/EquipmentTypes.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# EDIT EQUIPMENT TYPE
####################################
@login_required
def equipmentTypeEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit equipment type')
    if '' != id:
      equipment_type = models.EquipmentType.objects.get(id=id)
    else:
      equipment_type = models.EquipmentType()

    if request.method == 'GET':
      form = forms.EquipmentTypeForm(instance=equipment_type)
      context = {'form': form}
      return render(request, 'bcse_app/EquipmentTypeEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.EquipmentTypeForm(data, files=request.FILES, instance=equipment_type)
      if form.is_valid():
        savedEquipmentType = form.save()
        messages.success(request, "Equipment Type saved")
        return shortcuts.redirect('bcse:equipmentTypeEdit', id=savedEquipmentType.id)
      else:
        print(form.errors)
        message.error(request, "Equipment Type could not be saved. Check the errors below.")
        context = {'form': form}
        return render(request, 'bcse_app/EquipmentTypeEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# DELETE EQUIPMENT TYPE
####################################
@login_required
def equipmentTypeDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete equipment type')
    if '' != id:
      equipment_type = models.EquipmentType.objects.get(id=id)
      equipment_type.delete()
      messages.success(request, "Equipment Type deleted")

    return shortcuts.redirect('bcse:equipmentTypes')

  except models.EquipmentType.DoesNotExist:
    messages.success(request, "Equipment Type not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# VIEW EQUIPMENT TYPE
####################################
def equipmentTypeView(request, id=''):

  try:
    if '' != id:
      equipment_type = models.EquipmentType.objects.get(id=id)
    else:
      raise CustomException('Equipment does not exist')

    if request.method == 'GET':
      if request.is_ajax():
        context = {'title': equipment_type.name, 'kit': equipment_type}
        return render(request, 'bcse_app/BaxterBoxKitModal.html', context)

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# EQUIPMENT LIST
####################################
@login_required
def equipments(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view equipment list')

    equipments = models.Equipment.objects.all()
    context = {'equipments': equipments}
    return render(request, 'bcse_app/Equipments.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# EDIT EQUIPMENT
####################################
@login_required
def equipmentEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit equipment')
    if '' != id:
      equipment = models.Equipment.objects.get(id=id)
    else:
      equipment = models.Equipment()

    if request.method == 'GET':
      form = forms.EquipmentForm(instance=equipment)
      context = {'form': form}
      return render(request, 'bcse_app/EquipmentEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.EquipmentForm(data, files=request.FILES, instance=equipment)
      if form.is_valid():
        savedEquipment = form.save()
        messages.success(request, "Equipment saved")
        return shortcuts.redirect('bcse:equipmentEdit', id=savedEquipment.id)
      else:
        print(form.errors)
        message.error(request, "Equipment could not be saved. Check the errors below.")
        context = {'form': form}
        return render(request, 'bcse_app/EquipmentEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# DELETE EQUIPMENT TYPE
####################################
@login_required
def equipmentDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete equipment')
    if '' != id:
      equipment = models.Equipment.objects.get(id=id)
      equipment.delete()
      messages.success(request, "Equipment deleted")

    return shortcuts.redirect('bcse:equipments')

  except models.Equipment.DoesNotExist:
    messages.success(request, "Equipment not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# DELETE ACTIVITY
####################################
@login_required
def activityDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete activity')
    if '' != id:
      activity = models.Activity.objects.get(id=id)
      activity.delete()
      messages.success(request, "Activity deleted")

    return shortcuts.redirect('bcse:activities')

  except models.Activity.DoesNotExist:
    messages.success(request, "Activity not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################
# RESERVATIONS
####################################
def reservations(request):
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to view reservations')

    reservations = reservationsList(request)

    sort_order = [{'order_by': 'created_date', 'direction': 'asc', 'ignorecase': 'false'}]
    reservations = paginate(request, reservations, sort_order, settings.DEFAULT_ITEMS_PER_PAGE)
    searchForm = forms.ReservationsSearchForm(user=request.user, prefix="reservation_search")

    context = {'reservations': reservations, 'searchForm': searchForm}
    return render(request, 'bcse_app/Reservations.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def reservationsList(request, user_id=''):
  reservations = None
  if request.user.is_authenticated:
    if request.user.userProfile.user_role not in ['A', 'S']:
      reservations = models.Reservation.objects.all().filter(user__user=request.user)
    elif user_id:
      reservations = models.Reservation.objects.all().filter(user__id=user_id)
    else:
      reservations = models.Reservation.objects.all()

  return reservations

####################################
# EDIT RESERVATION
####################################
@login_required
def reservationEdit(request, id=''):
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to create/edit a reservation')

    if '' != id:
      reservation = models.Reservation.objects.get(id=id)
    else:
      reservation = models.Reservation(created_by=request.user.userProfile)

    reservation_settings = {}
    reservation_settings['reservation_delivery_days'] = settings.BAXTER_BOX_DELIVERY_DAYS
    reservation_settings['reservation_return_days'] = settings.BAXTER_BOX_RETURN_DAYS
    reservation_settings['reservation_min_days'] = settings.BAXTER_BOX_MIN_RESERVATION_DAYS
    reservation_settings['reservation_max_days'] = settings.BAXTER_BOX_MAX_RESERVATION_DAYS
    reservation_settings['reservation_min_advance_days'] = settings.BAXTER_BOX_MIN_ADVANCE_RESERVATION_DAYS
    reservation_settings['reservation_max_advance_days'] = settings.BAXTER_BOX_MAX_ADVANCE_RESERVATION_DAYS
    reservation_settings['reservation_reminder_days'] = settings.BAXTER_BOX_RESERVATION_REMINDER_DAYS

    if request.method == 'GET':
      if request.user.userProfile.user_role in ['T', 'P']:
        form = forms.ReservationForm(instance=reservation, user=request.user.userProfile, initial={'user': request.user.userProfile})
      else:
        form = forms.ReservationForm(instance=reservation, user=request.user.userProfile)

      context = {'form': form, 'reservation_settings': reservation_settings}

      return render(request, 'bcse_app/ReservationEdit.html', context)

    elif request.method == 'POST':
      if request.user.userProfile.user_role in ['T', 'P'] and reservation.status in ['D', 'O', 'I']:
        raise CustomException('This reservation is %s and cannot be modified' % reservation.get_status_display())

      data = request.POST.copy()
      form = forms.ReservationForm(data, instance=reservation, user=request.user.userProfile)
      if form.is_valid():
        equipment_types = form.cleaned_data['equipment_types']

        if equipment_types:
          availability_data = getAvailabilityData(request, id)
          is_available = availability_data['is_available']
          equipment_availability_matrix = availability_data['equipment_availability_matrix']
          availability_calendar = availability_data['availability_calendar']

          if is_available:
            savedReservation = form.save()
            savedReservation.equipment.clear()

            for equipment_type, availability in equipment_availability_matrix.items():
              savedReservation.equipment.add(availability['most_available_equip'])

            savedReservation.save()
            if '' != id:
              messages.success(request, "Reservation saved")
            else:
              messages.success(request, "Reservation made")
              send_reservation_confirmation_email(request, savedReservation)

            return shortcuts.redirect('bcse:reservationView', id=savedReservation.id)
          else:
            messages.error(request, "Selected equipment is unavailable for the selected dates. Please revise your dates and try making reservation again.")
            context = {'form': form, 'is_available': is_available, 'availability_calendar': availability_calendar, 'reservation_settings': reservation_settings }
            return render(request, 'bcse_app/ReservationEdit.html', context)
        else:
          savedReservation = form.save()
          savedReservation.equipment.clear()
          savedReservation.save()
          if '' != id:
            messages.success(request, "Reservation saved")
          else:
            messages.success(request, "Reservation made")
            send_reservation_confirmation_email(request, savedReservation)

          return shortcuts.redirect('bcse:reservationView', id=savedReservation.id)
      else:
        print(form.errors)
        messages.error(request, "Please correct the errors below and click Save again")
        context = {'form': form, 'reservation_settings': reservation_settings}
        return render(request, 'bcse_app/ReservationEdit.html', context)
    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# VIEW RESERVATION
####################################
def reservationView(request, id=''):
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to view this reservation')

    if '' != id:
      reservation = models.Reservation.objects.get(id=id)

      if request.user.userProfile.user_role in ['T', 'P'] and reservation.user != request.user.userProfile:
        raise CustomException('You do not have the permission to view this reservation')

      form = reservationMessage(request, id)
      reservation_messages = models.ReservationMessage.objects.all().filter(reservation=reservation).order_by('created_date')
      reservation_messages_html = []
      for reservation_message in reservation_messages:
        context= {'reservationMessage': reservation_message}
        if request.user.userProfile not in reservation_message.viewed_by.all() and request.user.userProfile != reservation_message.created_by:
          context['new_message'] = True
          reservation_message.viewed_by.add(request.user.userProfile)
        else:
          context['new_message'] = False

        reservation_messages_html.append(render_to_string('bcse_app/ReservationMessage.html', context, request))
      context = {'reservation': reservation, 'form': form, 'reservation_messages_html': reservation_messages_html}
      return render(request, 'bcse_app/ReservationView.html', context)
    else:
      raise models.Reservation.DoesNotExist

  except models.Reservation.DoesNotExist:
    messages.error(request, 'Reservation not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def reservationMessage(request, id=''):
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to view this reservation')

    if '' != id:
      reservation = models.Reservation.objects.get(id=id)
      if request.user.userProfile.user_role in ['T', 'P'] and reservation.user != request.user.userProfile:
        raise CustomException('You do not have the permission to view this reservation')
    else:
      raise models.Reservation.DoesNotExist

    if request.method == 'GET':
      form = forms.ReservationMessageForm(initial={'reservation': reservation, 'created_by':request.user.userProfile})
      return form

    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.ReservationMessageForm(data)
      if form.is_valid():
        savedMessage = form.save()
        send_reservation_message_email(request, savedMessage)
        if request.is_ajax():
          response_data = {}
          response_data['success'] = True
          context= {'reservationMessage': savedMessage}
          response_data['html'] = render_to_string('bcse_app/ReservationMessage.html', context, request)
          return http.HttpResponse(json.dumps(response_data), content_type="application/json")
        else:
          newForm = forms.ReservationMessageForm(initial={'reservation': reservation, 'created_by':request.user.userProfile})
          return newForm
      else:
        print(form.errors)
        if request.is_ajax():
          response_data = {}
          response_data['success'] = False
          return http.HttpResponse(json.dumps(response_data), content_type="application/json")
        else:
          messages.error(request, "Please correct the errors below and click Post again")
          return form
    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.Reservation.DoesNotExist:
    messages.error(request, 'Reservation not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))



####################################
# DELETE RESERVATION
####################################
@login_required
def reservationDelete(request, id=''):

  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to delete reservation')

    if '' != id:
      reservation = models.Reservation.objects.get(id=id)

      #non admin/staff users cannot delete reservations that they do not own
      if request.user.userProfile.user_role not in ['A', 'S'] and reservation.user.user != request.user:
        raise CustomException('You do not have the permission to delete this reservation')
      #reservations that are checked out or checked in cannot be deleted
      elif reservation.status in ['O', 'I']:
        raise CustomException('This reservation is %s and cannot be deleted' % reservation.get_status_display())

      reservation.delete()
      messages.success(request, "Reservation deleted")

    return shortcuts.redirect('bcse:reservations')

  except models.Reservation.DoesNotExist:
    messages.success(request, "Reservation not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
##########################################################
# FILTER RESERVATIONS BASED ON FILTER CRITERIA
##########################################################
def reservationsSearch(request):
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to view reservations')
    elif request.user.is_authenticated and request.user.userProfile.user_role not in ['A', 'S']:
      reservations = models.Reservation.objects.all().filter(user__user=request.user)
    else:
      reservations = models.Reservation.objects.all()

    if request.method == 'GET':

      query_filter = Q()
      keyword_filter = None
      user_filter = None
      activity_filter = None
      equipment_filter = None
      delivery_after_filter = None
      return_before_filter = None
      status_filter = None

      keywords = request.GET.get('reservation_search-keywords', '')
      user = request.GET.get('reservation_search-user', '')
      activity = request.GET.get('reservation_search-activity', '')
      equipment = request.GET.getlist('reservation_search-equipment', '')
      delivery_after = request.GET.get('reservation_search-delivery_after', '')
      return_before = request.GET.get('reservation_search-return_before', '')
      status = request.GET.getlist('reservation_search-status', '')
      sort_by = request.GET.get('reservation_search-sort_by', '')

      if keywords:
        keyword_filter = Q(activity__name__icontains=keywords) | Q(other_activity_name__icontains=keywords)
        keyword_filter = keyword_filter | Q(user__user__first_name__icontains=keywords)
        keyword_filter = keyword_filter | Q(user__user__last_name__icontains=keywords)
        keyword_filter = keyword_filter | Q(notes__icontains=keywords)

      if user:
        user_filter = Q(user=user)
      if activity:
        activity_filter = Q(activity=activity)
      if status:
        status_filter = Q(status__in=status)

      if delivery_after:
        delivery_after = datetime.datetime.strptime(delivery_after, '%B %d, %Y')
        delivery_after_filter = Q(delivery_date__gte=delivery_after)

      if return_before:
        return_before = datetime.datetime.strptime(return_before, '%B %d, %Y')
        return_before_filter = Q(return_date__lte=return_before)


      if keyword_filter:
        query_filter = keyword_filter

      if user_filter:
        query_filter = query_filter & user_filter
      if activity_filter:
        query_filter = query_filter & activity_filter
      if equipment_filter:
        query_filter = query_filter & equipment_filter

      if status_filter:
        query_filter = query_filter & status_filter
      if delivery_after_filter:
        query_filter = query_filter & delivery_after_filter
      if return_before_filter:
        query_filter = query_filter & return_before_filter

      reservations = reservations.filter(query_filter)

      if equipment:
        for e in equipment:
          reservations = reservations.filter(equipment__equipment_type__id=e)

      reservations = reservations.distinct()

      direction = request.GET.get('direction') or 'asc'
      ignorecase = request.GET.get('ignorecase') or 'false'

      sort_order = []
      if sort_by:
        if sort_by == 'user':
          sort_order.append({'order_by': 'user__user__first_name', 'direction': 'asc', 'ignorecase': 'true'})
          sort_order.append({'order_by': 'user__user__last_name', 'direction': 'asc', 'ignorecase': 'true'})
        elif sort_by == 'activity':
          sort_order.append({'order_by': 'activity__name', 'direction': 'asc', 'ignorecase': 'true'})
          sort_order.append({'order_by': 'other_activity_name', 'direction': 'asc', 'ignorecase': 'true'})

        elif sort_by == 'delivery_date':
          sort_order.append({'order_by': 'delivery_date', 'direction': 'asc', 'ignorecase': 'false'})
        elif sort_by == 'return_date':
          sort_order.append({'order_by': 'return_date', 'direction': 'asc', 'ignorecase': 'false'})
        elif sort_by == 'status':
          sort_order.append({'order_by': 'status', 'direction': 'asc', 'ignorecase': 'true'})

      sort_order.append({'order_by': 'created_date', 'direction': 'asc', 'ignorecase': 'false'})

      reservations = paginate(request, reservations, sort_order, settings.DEFAULT_ITEMS_PER_PAGE)

      context = {'reservations': reservations, 'tag': 'reservations'}
      response_data = {}
      response_data['success'] = True
      response_data['html'] = render_to_string('bcse_app/ReservationsTableView.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def getAvailabilityData(request, id=''):
  data = request.POST.copy()
  equipment_types = models.EquipmentType.objects.all().filter(id__in=request.POST.getlist('equipment_types', ''))
  delivery_date = datetime.datetime.strptime(request.POST.get('delivery_date'), '%B %d, %Y').date()
  return_date = datetime.datetime.strptime(request.POST.get('return_date'), '%B %d, %Y').date()

  start_date = delivery_date.replace(day=1)
  end_date = return_date.replace(day=calendar.monthrange(return_date.year, return_date.month)[1])
  equipment_availability_matrix = checkAvailability(id, equipment_types, start_date, end_date, delivery_date, return_date)
  is_available = all([equipment_type['is_available'] for equipment_type in equipment_availability_matrix.values()])
  availability_calendar = []
  index_date = start_date
  while index_date <= end_date:
    cal = Calendar(index_date.year, index_date.month)
    cal.setfirstweekday(6)
    availability_calendar.append(cal.formatmonth(withyear=True, availability_matrix=equipment_availability_matrix, delivery_date=delivery_date, return_date=return_date))
    index_date += relativedelta(months=1)

  if request.is_ajax():
    response_data = {}
    response_data['success'] = True
    context = {'availability_calendar': availability_calendar}
    if is_available:
      response_data['message'] = "Selected equipment is available for the selected dates"
    else:
      response_data['message'] = "Selected equipment is unavailable for the selected dates. Please revise your dates and try making reservation again."
    response_data['html'] = render_to_string('bcse_app/AvailabilityCalendar.html', context, request)
    return http.HttpResponse(json.dumps(response_data), content_type="application/json")
  else:
    availability_data = {'is_available': is_available, 'equipment_availability_matrix': equipment_availability_matrix,
                       'availability_calendar': availability_calendar}
    return availability_data

####################################
# CHECK EQUIPMENT AVAILABILITY
####################################
def checkAvailability(current_reservation_id, equipment_types, start_date, end_date, delivery_date, return_date):
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


@login_required
def baxterBoxUsageReport(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view Baxter Box Report')

    reservations = models.Reservation.objects.all().exclude(status='D')
    equipment_types = models.EquipmentType.objects.all().order_by('name')
    activities = models.Activity.objects.all().order_by('name')
    searchForm = forms.BaxterBoxUsageSearchForm(user=request.user, prefix="usage")
    equipment_usage = {}
    kit_usage = {}
    total_usage = {'reservations': 0, 'kits': 0, 'teachers': [], 'schools': []}
    for equipment_type in equipment_types:
      equipment_usage[equipment_type.id] = {'name': equipment_type.name, 'reservations': [], 'teachers': [], 'schools': []}
    for activity in activities:
      kit_usage[activity.id] = {'name': activity.kit_name, 'count': 0, 'teachers': [], 'schools': []}

    from_date = request.GET.get('usage-from_date', '')
    to_date = request.GET.get('usage-to_date', '')

    if from_date:
      from_date = datetime.datetime.strptime(from_date, '%B %d, %Y')
      reservations = reservations.filter(delivery_date__gte=from_date)

    if to_date:
      to_date = datetime.datetime.strptime(to_date, '%B %d, %Y')
      reservations = reservations.filter(return_date__lte=to_date)

    for reservation in reservations:
      if reservation.equipment:
        for equipment in reservation.equipment.all():
          equipment_usage[equipment.equipment_type.id]['reservations'].append(reservation)
          if reservation.user not in equipment_usage[equipment.equipment_type.id]['teachers']:
            equipment_usage[equipment.equipment_type.id]['teachers'].append(reservation.user)
          if reservation.user.work_place not in equipment_usage[equipment.equipment_type.id]['schools']:
            equipment_usage[equipment.equipment_type.id]['schools'].append(reservation.user.work_place)

      if reservation.activity:
        if not reservation.activity_kit_not_needed and reservation.num_of_classes:
          kit_usage[reservation.activity.id]['count'] += int(reservation.num_of_classes)
          total_usage['kits'] += int(reservation.num_of_classes)
        if reservation.user not in kit_usage[reservation.activity.id]['teachers']:
          kit_usage[reservation.activity.id]['teachers'].append(reservation.user)
        if reservation.user.work_place not in kit_usage[reservation.activity.id]['schools']:
          kit_usage[reservation.activity.id]['schools'].append(reservation.user.work_place)

      total_usage['reservations'] += 1
      if reservation.user not in total_usage['teachers']:
        total_usage['teachers'].append(reservation.user)
      if reservation.user.work_place not in total_usage['schools']:
        total_usage['schools'].append(reservation.user.work_place)



    if request.is_ajax():
      response_data = {}
      response_data['success'] = True
      context = {'equipment_usage': equipment_usage, 'kit_usage': kit_usage, 'total_usage': total_usage, 'from_date': from_date, 'to_date': to_date}
      response_data['html'] = render_to_string('bcse_app/BaxterBoxUsageTableView.html', context, request)
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
      context = {'equipment_usage': equipment_usage, 'kit_usage': kit_usage, 'total_usage': total_usage, 'searchForm': searchForm, 'from_date': from_date, 'to_date': to_date}
      return render(request, 'bcse_app/BaxterBoxUsageReport.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################################
# WORKSHOP REGISTRATION CONFIRMATION MESSAGES
####################################################
@login_required
def registrationEmailMessages(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view registration messages')

    registration_messages = models.RegistrationEmailMessage.objects.all()
    context = {'registration_messages': registration_messages}
    return render(request, 'bcse_app/RegistrationEmailMessages.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################################
# EDIT WORKSHOP REGISTRATION CONFIRMATION MESSAGE
####################################################
@login_required
def registrationEmailMessageEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit registration messages')
    if '' != id:
      registration_confirmation = models.RegistrationEmailMessage.objects.get(id=id)
    else:
      registration_confirmation = models.RegistrationEmailMessage()

    if request.method == 'GET':
      form = forms.RegistrationEmailMessageForm(instance=registration_confirmation)
      context = {'form': form}
      return render(request, 'bcse_app/RegistrationEmailMessageEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.RegistrationEmailMessageForm(data, files=request.FILES, instance=registration_confirmation)
      if form.is_valid():
        savedMessage = form.save()
        messages.success(request, "Registration confirmation message saved")
        return shortcuts.redirect('bcse:registrationEmailMessageEdit', id=savedMessage.id)
      else:
        print(form.errors)
        messages.error(request, "Registration email message could not be saved. Check the errors below.")
        context = {'form': form}
        return render(request, 'bcse_app/RegistrationEmailMessageEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################################
# DELETE WORKSHOP REGISTRATION CONFIRMATION MESSAGE
####################################################
def registrationEmailMessageDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete this workshop')

    if '' != id:
      registration_confirmation = models.RegistrationEmailMessage.objects.get(id=id)
      registration_confirmation.delete()
      messages.success(request, "Registration email message deleted")

    return shortcuts.redirect('bcse:registrationEmailMessages')

  except models.RegistrationEmailMessage.DoesNotExist:
    messages.success(request, "Registration email message not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# EDIT WORKSHOP CATEGORY
####################################
@login_required
def workshopCategoryEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view workshop categories')
    if '' != id:
      workshop_category = models.WorkshopCategory.objects.get(id=id)
    else:
      workshop_category = models.WorkshopCategory()

    if request.method == 'GET':
      form = forms.WorkshopCategoryForm(instance=workshop_category)
      context = {'form': form}
      return render(request, 'bcse_app/WorkshopCategoryEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.WorkshopCategoryForm(data, files=request.FILES, instance=workshop_category)
      if form.is_valid():
        savedCategory = form.save()
        messages.success(request, "Workshop Category saved")
        return shortcuts.redirect('bcse:workshopCategoryEdit', id=savedCategory.id)
      else:
        print(form.errors)
        message.error(request, "Workshop Category could not be saved. Check the errors below.")
        context = {'form': form}
        return render(request, 'bcse_app/WorkshopCategoryEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# DELETE WORKSHOP CATEGORY
####################################
@login_required
def workshopCategoryDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view workshop categories')
    if '' != id:
      workshop_category = models.WorkshopCategory.objects.get(id=id)
      workshop_category.delete()
      messages.success(request, "Workshop category deleted")

    return shortcuts.redirect('bcse:workshopCategories')

  except models.WorkshopCategory.DoesNotExist:
    messages.success(request, "Workshop category not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# WORKSHOP CATEGORIES
####################################
@login_required
def workshopCategories(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view workshop categories')

    workshop_categories = models.WorkshopCategory.objects.all().order_by('audience', 'name')
    context = {'workshop_categories': workshop_categories}
    return render(request, 'bcse_app/WorkshopCategories.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# GET WORKSHOP CATEGORY DETAILS
####################################
@login_required
def getWorkshopCategoryDetails(request, id=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view workshop category')

    workshop_category = models.WorkshopCategory.objects.get(id=id)
    response_data = {'success': True, 'name': workshop_category.name, 'workshop_type': workshop_category.workshop_type, 'audience': workshop_category.audience, 'description': workshop_category.description}
  except CustomException as ce:
    response_data = {'success': False}
  except models.WorkshopCategory.DoesNotExist as e:
    response_data = {'success': False}

  return http.HttpResponse(json.dumps(response_data), content_type='application/json')

####################################
# EDIT WORKSHOP
####################################
@login_required
def workshopEdit(request, id=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit this workshop')

    workshop_registration_setting = None

    if '' != id:
      workshop = models.Workshop.objects.get(id=id)
      if workshop.enable_registration:
        workshop_registration_setting, created = models.WorkshopRegistrationSetting.objects.get_or_create(workshop=workshop)
    else:
      workshop = models.Workshop()

    workshop_categories = models.WorkshopCategory.objects.all().filter(status='A')
    if request.method == 'GET':
      form = forms.WorkshopForm(instance=workshop)
      context = {'form': form, 'workshop_registration_setting': workshop_registration_setting, 'workshop_categories': workshop_categories}
      return render(request, 'bcse_app/WorkshopEdit.html', context)

    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.WorkshopForm(data, files=request.FILES, instance=workshop)
      if form.is_valid():
        savedWorkshop = form.save()
        if savedWorkshop.enable_registration:
          workshop_registration_setting, created = models.WorkshopRegistrationSetting.objects.get_or_create(workshop=savedWorkshop)

        messages.success(request, "Workshop saved")
        return shortcuts.redirect('bcse:workshopEdit', id=savedWorkshop.id)
      else:
        messages.error(request, "Workshop could not be saved. Check the errors below.")
        context = {'form': form, 'workshop_registration_setting': workshop_registration_setting, 'workshop_categories': workshop_categories}
        return render(request, 'bcse_app/WorkshopEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.Workshop.DoesNotExist:
    messages.success(request, "Workshop not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# CLONE WORKSHOP
####################################
def workshopCopy(request, id=''):
  try:

    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to copy this workshop')
    if '' != id:
      workshop = models.Workshop.objects.get(id=id)
      title = workshop.name
      workshop.pk = None
      workshop.id = None
      workshop.image = None
      workshop.enable_registration = False
      workshop.save()

      original_workshop = models.Workshop.objects.get(id=id)
      workshop.name = 'Copy of ' + title
      workshop.created_date = datetime.datetime.now()
      workshop.modified_date = datetime.datetime.now()

      if original_workshop.image:
        try:
          source = original_workshop.image
          filecontent = ContentFile(source.file.read())
          filename = os.path.split(source.file.name)[-1]
          filename_array = filename.split('.')
          new_filename = filename_array[0] + '-' + str(workshop.id) + '.' + filename_array[1]
          workshop.image.save(new_filename, filecontent)
          workshop.save()
          source.file.close()
          original_workshop.image.save(filename, filecontent)
          original_workshop.save()
        except IOError as e:
          workshop.save()
      else:
        workshop.save()

      messages.success(request, "Workshop copied")
      return shortcuts.redirect('bcse:workshopEdit', id=workshop.id)

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


  except models.Workshop.DoesNotExist:
    messages.success(request, "Workshop not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# DELETE WORKSHOP
####################################
def workshopDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete this workshop')

    if '' != id:
      workshop = models.Workshop.objects.get(id=id)
      audience = workshop.workshop_category.audience
      if hasattr(workshop, 'registration_setting') and workshop.registration_setting.registrants.all().count() > 0:
        messages.error(request, "This workshop cannot be deleted as it has existing registrants.")
        return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
      else:
        workshop.delete()
        messages.success(request, "Workshop deleted")

    if audience == 'T':
      return shortcuts.redirect('bcse:workshops', flag='table')
    else:
      return shortcuts.redirect('bcse:studentPrograms', flag='table')

  except models.Workshop.DoesNotExist:
    messages.success(request, "Workshop not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# VIEW WORKSHOP
####################################
def workshopView(request, id=''):
  try:
    if '' != id:
      workshop = models.Workshop.objects.get(id=id)
      if workshop.status != 'A' or workshop.workshop_category.status != 'A':
        if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
          raise CustomException('You do not have the permission to view this workshop')

      registration = workshopRegistration(request, workshop.id)

      context = {'workshop': workshop, 'registration': registration}

      return render(request, 'bcse_app/WorkshopView.html', context)
    else:
      raise models.Workshop.DoesNotExist

  except models.Workshop.DoesNotExist:
    messages.error(request, 'Workshop not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

###################################################
# GET WORKSHOP REGISTRATION FOR THE LOGGED IN USER
###################################################
def workshopRegistration(request, workshop_id):

  registration = {}
  form = workshop_registration = user_message = admin_message = message_class = None
  registration_open = False

  workshop = models.Workshop.objects.get(id=workshop_id)
  registration_setting_status = workshopRegistrationSettingStatus(workshop)

  if workshop.enable_registration and workshop.registration_setting and workshop.registration_setting.registration_type:

    if workshop.registration_setting.registration_type == 'R':
      default_registration_status = 'R'
    else:
      default_registration_status = 'A'

    if request.user.is_anonymous:
      if registration_setting_status['registration_open']:
        if default_registration_status == 'R':
          user_message = 'Please <u><a href="?next=/signin">login</a></u> to register for this workshop'
        else:
          user_message = 'Please <u><a href="?next=/signin">login</a></u> to apply to this workshop'
      elif registration_setting_status['message']:
        user_message = registration_setting_status['message']

      message_class = 'info'
    else:
      if request.user.userProfile.user_role in ['A', 'S']:
        workshop_registration = models.Registration(workshop_registration_setting=workshop.registration_setting, status=default_registration_status)
      else:
        try:
          workshop_registration = models.Registration.objects.get(workshop_registration_setting=workshop.registration_setting, user=request.user.userProfile)
          registration_message = workshopRegistrationMessage(workshop_registration)
          user_message = registration_message['message']
          message_class = registration_message['message_class']
        except models.Registration.DoesNotExist:
          workshop_registration = models.Registration(workshop_registration_setting=workshop.registration_setting, user=request.user.userProfile, status=registration_setting_status['default_registration_status'])
          if registration_setting_status['message']:
            user_message = registration_setting_status['message']
            message_class = 'info'

  if request.method == 'GET':
    if workshop_registration:
      if request.user.userProfile.user_role in ['A', 'S'] or registration_setting_status['registration_open']:
        form = forms.WorkshopRegistrationForm(instance=workshop_registration, prefix='workshop-%s'%workshop.id)

    registration['form'] = form
    registration['instance'] = workshop_registration
    registration['user_message'] = user_message
    registration['message_class'] = message_class

    return registration

  elif request.method == 'POST':
    data = request.POST.copy()
    registration_id = None
    form = forms.WorkshopRegistrationForm(data, instance=workshop_registration, prefix='workshop-%s'%workshop.id)
    if form.is_valid():
      saved_registration = form.save()
      registration_id = saved_registration.id
      if request.user.userProfile.user_role in ['A', 'S']:
        workshop_registration = models.Registration(workshop_registration_setting=workshop.registration_setting, status=default_registration_status)
        form = forms.WorkshopRegistrationForm(instance=workshop_registration, prefix='workshop-%s'%workshop.id)
        admin_message = "Workshop registration for user %s saved" % saved_registration.user
        registration['admin_message'] = admin_message
        registration['form'] = form
        registration['instance'] = workshop_registration
      else:
        registration_message = workshopRegistrationMessage(saved_registration)
        user_message = registration_message['message']
        message_class = registration_message['message_class']
        registration['user_message'] = user_message
        registration['message_class'] = message_class
        registration['instance'] = saved_registration

      success = True
    else:
      print(form.errors)
      if not request.is_ajax():
        messages.success(request, "There were some errors")
      if request.user.userProfile.user_role in ['A', 'S']:
        admin_message = "Something went wrong with the workshop registration"
        registration['admin_message'] = admin_message
      else:
        registration['user_message'] = user_message

      registration['form'] = form
      registration['instance'] = workshop_registration
      registration['message_class'] = message_class
      success = False

    if request.is_ajax():
      response_data = {'success': success, 'admin_message': admin_message}
      context = {'workshop': workshop, 'registration': registration}
      response_data['html'] = render_to_string('bcse_app/WorkshopRegistration.html', context, request)
      return http.HttpResponse(json.dumps(response_data), content_type='application/json')
    else:
      print('request non ajax')
      return registration

################################################
# Check if registration is open for a workshop
# if not provide a message when registration
# will open or was closed
################################################
def workshopRegistrationSettingStatus(workshop):

  current_datetime = datetime.datetime.now()
  current_date = current_datetime.date()
  registration_open = False
  open_datetime = open_date = close_datetime = close_date = open_close = open_close_date = None
  message = default_registration_status = None

  if workshop.enable_registration and workshop.registration_setting and workshop.registration_setting.registration_type and current_date < workshop.start_date:
    #default registration status
    if workshop.registration_setting.registration_type == 'R':
      default_registration_status = 'R'
    else:
      default_registration_status = 'A'

    #check if registration open date exists
    if workshop.registration_setting.open_date:
      if workshop.registration_setting.open_time:
        open_datetime = datetime.datetime.combine(workshop.registration_setting.open_date, workshop.registration_setting.open_time)
      else:
        open_date = workshop.registration_setting.open_date

    #check if registration close date exists
    if workshop.registration_setting.close_date:
      if workshop.registration_setting.close_time:
        close_datetime = datetime.datetime.combine(workshop.registration_setting.close_date, workshop.registration_setting.close_time)
      else:
        close_date = workshop.registration_setting.close_date

    #if no open and close dates provided then registration is open
    if open_datetime is None and open_date is None and close_datetime is None and close_date is None:
      registration_open = True

    elif open_datetime is not None:
      if close_datetime is not None:
        if open_datetime <= current_datetime and current_datetime <= close_datetime:
          registration_open = True
        else:
          if current_datetime < open_datetime:
            open_close = 'opens'
            open_close_date = open_datetime
          else:
            open_close = 'closed'
            open_close_date = close_datetime

      elif close_date is not None:
        if open_datetime <= current_datetime and current_date <= close_date:
          registration_open = True
        else:
          if current_datetime < open_datetime:
            open_close = 'opens'
            open_close_date = open_datetime
          else:
            open_close = 'closed'
            open_close_date = close_date

    elif open_date is not None:
      if close_datetime is not None:
        if open_date <= current_date and current_datetime <= close_datetime:
          registration_open = True
        else:
          if current_date < open_date:
            open_close = 'opens'
            open_close_date = open_date
          else:
            open_close = 'closed'
            open_close_date = close_datetime

      elif close_date is not None:
        if open_date <= current_date and current_date <= close_date:
          registration_open = True
        else:
          if current_date < open_date:
            open_close = 'opens'
            open_close_date = open_date
          else:
            open_close = 'closed'
            open_close_date = close_date

    #check if the current date is outside the registration open dates
    if open_close and open_close_date:
      message = 'Registration %s on %s' % (open_close, open_close_date.strftime("%B %d, %Y"))
    elif registration_open:
      #check if workshop capacity has reached
      if workshop.registration_setting.registration_type == 'R' and workshop.registration_setting.capacity is not None and workshop.registration_setting.capacity >= 0:
        total_registrations = models.Registration.objects.all().filter(workshop_registration_setting=workshop.registration_setting, status='R').count()
        #capacity has reached
        if total_registrations >= workshop.registration_setting.capacity:
          #check if there is room in the waitlist
          if workshop.registration_setting.enable_waitlist:
            if workshop.registration_setting.waitlist_capacity is not None and workshop.registration_setting.waitlist_capacity >= 0:
              total_waitlisted = models.Registration.objects.all().filter(workshop_registration_setting=workshop.registration_setting, status='W').count()
              if total_waitlisted >= workshop.registration_setting.waitlist_capacity:
                registration_open = False
                message = 'We have reached capacity for this workshop'
              else:
                default_registration_status = 'W'
            else:
              default_registration_status = 'W'
          else:
            registration_open = False
            message = 'We have reached capacity for this workshop'


  return {'registration_open': registration_open, 'message': message, 'default_registration_status': default_registration_status}


################################################
# EDIT WORKSHOP REGISTRATION
################################################
def workshopRegistrationEdit(request, workshop_id='', id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit this registration')

    if '' != id:
      registration = models.Registration.objects.get(id=id)
      workshop = models.Workshop.objects.get(id=workshop_id)
      if registration.workshop_registration_setting.workshop.id != workshop.id:
        raise CustomException('Registration does not belong to the workshop')

    if request.method == 'GET':
      form = forms.WorkshopRegistrationForm(instance=registration)
      context = {'form': form, 'workshop': workshop}
      return render(request, 'bcse_app/WorkshopRegistrationModal.html', context)

    elif request.method == 'POST':
      response_data = {}
      data = request.POST.copy()
      form = forms.WorkshopRegistrationForm(data, instance=registration)
      if form.is_valid():
        savedRegistration = form.save()
        messages.success(request, "Registration saved")
        response_data['success'] = True
      else:
        print(form.errors)
        messages.error(request, 'Registration could not be saved')
        context = {'form': form, 'workshop': workshop}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/WorkshopRegistrationModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.Workshop.DoesNotExist:
    messages.success(request, "Workshop not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.Registration.DoesNotExist:
    messages.success(request, "Registration not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

################################################
# DELETE WORKSHOP REGISTRATION
################################################
def workshopRegistrationDelete(request, workshop_id='', id=''):

  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to edit this registration')
    else:
      registration = models.Registration.objects.get(id=id)
      workshop = models.Workshop.objects.get(id=workshop_id)

      if request.user.userProfile.user_role not in ['A', 'S']:
        if request.user.userProfile != registration.user:
          raise CustomException('You do not have the permission to edit this registration')

      if registration.workshop_registration_setting.workshop.id != workshop.id:
        raise CustomException('Registration does not belong to the workshop')

      registration.delete()
      messages.success(request, "Registration has been deleted")
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.Workshop.DoesNotExist:
    messages.success(request, "Workshop not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.Registration.DoesNotExist:
    messages.success(request, "Registration not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

################################################
# GET WORKSHOP REGISTRATION MESSAGE TO DISPLAY
################################################
def workshopRegistrationMessage(workshop_registration):

  message = message_class = None

  if workshop_registration.workshop_registration_setting.registration_type == 'R':
    registration_type = 'registration'
  else:
    registration_type = 'application'

  if workshop_registration.status == 'R':
    message = 'You are registered for this workshop'
    message_class = 'success'
  elif workshop_registration.status == 'A':
    message = 'You have applied to this workshop'
    message_class = 'success'
  elif workshop_registration.status == 'C':
    message = 'You %s has been accepted for this workshop' % registration_type
    message_class = 'success'
  elif workshop_registration.status == 'P':
    message = 'You %s is pending for this workshop' % registration_type
    message_class = 'warning'
  elif workshop_registration.status == 'N':
    message = 'Your %s is cancelled for this workshop' % registration_type
    message_class = 'error'
  elif workshop_registration.status == 'W':
    message = 'Your %s is waitlisted for this workshop' % registration_type
    message_class = 'warning'

  return {'message': message, 'message_class': message_class}


################################################
# WORKSHOPS BASE QUERY BEFORE APPLYING FILTERS
################################################
def workshopsBaseQuery(request, flag='list', user_id=''):

  workshops = None
  if request.user.is_authenticated:
    if user_id:
      workshops = models.Workshop.objects.all().filter(registration_setting__workshop_registrants__user__id=user_id)
    elif request.user.userProfile.user_role not in ['A', 'S']:
      if flag =='list':
        workshops = models.Workshop.objects.all().filter(status='A', workshop_category__status='A')
      else:
        workshops = models.Workshop.objects.all().filter(registration_setting__workshop_registrants__user=request.user.userProfile)
    else:
      workshops = models.Workshop.objects.all()
  else:
    workshops = models.Workshop.objects.all().filter(status='A', workshop_category__status='A')

  workshops = workshops.filter(workshop_category__audience='T')
  return workshops

def studentProgramsBaseQuery(request):
  if request.user.is_authenticated and request.user.userProfile.user_role in ['A', 'S']:
    student_programs = models.Workshop.objects.all().filter(workshop_category__audience='S')
  else:
    student_programs = models.Workshop.objects.all().filter(status='A', workshop_category__status='A', workshop_category__audience='S')

  return student_programs
################################################
# VIEW WORKSHOPS
################################################
def workshops(request, flag='list'):

  searchForm = forms.WorkshopsSearchForm(user=request.user, audience='teacher', prefix="workshop_search")
  workshop_list = workshopsList(request, flag)
  context = {'workshop_list': workshop_list, 'searchForm': searchForm, 'flag': flag}

  return render(request, 'bcse_app/WorkshopsBaseView.html', context)

################################################
# VIEW STUDENT PROGRAMS
################################################
def studentPrograms(request, flag='list'):
  student_programs = studentProgramsBaseQuery(request)
  searchForm = forms.WorkshopsSearchForm(user=request.user, audience='student', prefix="workshop_search")

  workshop_list = []
  for workshop in student_programs:
    workshop_list.append({'workshop': workshop})
  print(workshop_list)
  context = {'workshop_list': workshop_list, 'searchForm': searchForm, 'flag': flag}

  return render(request, 'bcse_app/StudentProgramsBaseView.html', context)
################################################
# UTILITY FUNCITON TO GET A LIST OF WORKSHOPS
################################################
def workshopsList(request, flag, id=''):
  workshops = workshopsBaseQuery(request, flag, id)
  workshop_list = []
  for workshop in workshops:
    registration = None
    if workshop.enable_registration and workshop.registration_setting and workshop.registration_setting.registration_type:
      registration = workshopRegistration(request, workshop.id)
    workshop_list.append({'workshop': workshop, 'registration': registration})

  return workshop_list

##########################################################
# FILTER WORKSHOP BASE QUERY BASED ON FILTER CRITERIA
##########################################################
def workshopsSearch(request, flag='list', audience='teacher'):
  if audience == 'teacher':
    workshops = workshopsBaseQuery(request, flag)
  else:
    workshops = studentProgramsBaseQuery(request)

  if request.method == 'GET':

    query_filter = Q()
    keyword_filter = None
    workshop_category_filter = None
    starts_after_filter = None
    ends_before_filter = None
    registration_filter = None
    status_filter = None

    keywords = request.GET.get('workshop_search-keywords', '')
    starts_after = request.GET.get('workshop_search-starts_after', '')
    ends_before = request.GET.get('workshop_search-ends_before', '')
    registration_open = request.GET.get('workshop_search-registration_open', '')
    workshop_category = request.GET.get('workshop_search-workshop_category', '')
    status = request.GET.get('workshop_search-status', '')
    sort_by = request.GET.get('workshop_search-sort_by', '')

    if keywords:
      keyword_filter = Q(name__icontains=keywords) | Q(sub_title__icontains=keywords)
      keyword_filter = keyword_filter | Q(workshop_category__name__icontains=keywords)
      keyword_filter = keyword_filter | Q(teacher_leader__first_name__icontains=keywords)
      keyword_filter = keyword_filter | Q(teacher_leader__last_name__icontains=keywords)
      keyword_filter = keyword_filter | Q(summary__icontains=keywords)
      keyword_filter = keyword_filter | Q(description__icontains=keywords)
      keyword_filter = keyword_filter | Q(location__icontains=keywords)

    if workshop_category:
      workshop_category_filter = Q(workshop_category__id=workshop_category)

    if status:
      status_filter = Q(status=status)

    if starts_after:
      starts_after = datetime.datetime.strptime(starts_after, '%B %d, %Y')
      starts_after_filter = Q(start_date__gte=starts_after)

    if ends_before:
      ends_before = datetime.datetime.strptime(ends_before, '%B %d, %Y')
      ends_before_filter = Q(end_date__lte=ends_before)


    if keyword_filter:
      query_filter = keyword_filter
    if status_filter:
      query_filter = query_filter & status_filter
    if workshop_category_filter:
      query_filter = query_filter & workshop_category_filter
    if starts_after_filter:
      query_filter = query_filter & starts_after_filter
    if ends_before_filter:
      query_filter = query_filter & ends_before_filter

    workshops = workshops.filter(query_filter)

    if registration_open:
      workshops_with_open_registration = []
      for workshop in workshops:
        registration_setting_status = workshopRegistrationSettingStatus(workshop)
        if registration_setting_status['registration_open']:
          workshops_with_open_registration.append(workshop.id)

      workshops = workshops.filter(id__in=workshops_with_open_registration)

    if sort_by:
      if sort_by == 'title':
        workshops = workshops.order_by('name')
      elif sort_by == 'start_date':
        workshops = workshops.order_by('start_date')

    workshop_list = []
    for workshop in workshops:
      registration = None
      if workshop.enable_registration and workshop.registration_setting and workshop.registration_setting.registration_type:
        registration = workshopRegistration(request, workshop.id)
      workshop_list.append({'workshop': workshop, 'registration': registration})

    context = {'workshop_list': workshop_list, 'tag': 'workshops'}
    response_data = {}
    response_data['success'] = True
    if audience == 'teacher':
      if flag == 'list':
        response_data['html'] = render_to_string('bcse_app/WorkshopsListView.html', context, request)
      else:
        response_data['html'] = render_to_string('bcse_app/WorkshopsTableView.html', context, request)
    else:
      if flag == 'list':
        response_data['html'] = render_to_string('bcse_app/StudentProgramsListView.html', context, request)
      else:
        response_data['html'] = render_to_string('bcse_app/StudentProgramsTableView.html', context, request)

    return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  return http.HttpResponseNotAllowed(['GET'])


##########################################################
# WORKSHOP REGISTRATION SETTING
##########################################################
def workshopRegistrationSetting(request, id=''):
  try:

    if request.user.userProfile.user_role != 'A':
      raise CustomException('You do not have the permission to access this setting')

    if '' != id:
      workshop = models.Workshop.objects.get(id=id)
      workshop_registration_setting, created = models.WorkshopRegistrationSetting.objects.get_or_create(workshop=workshop)
    else:
      messages.error(request, 'Workshop not found')
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

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
        return shortcuts.redirect('bcse:workshopRegistrationSetting', id=id)
      else:
        context = {'form': form, 'workshop': workshop}

        return render(request, 'bcse_app/WorkshopRegistrationSetting.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.Workshop.DoesNotExist:
    messages.error(request, 'Workshop not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# LIST OF WORKSHOP REGISTRANTS
##########################################################
def workshopRegistrants(request, id=''):
  try:

    if request.user.is_anonymous or request.user.userProfile.user_role not in  ['A', 'S'] :
      raise CustomException('You do not have the permission to view workshop registrants')

    if '' != id:
      workshop = models.Workshop.objects.get(id=id)
      workshop_registration_setting, created = models.WorkshopRegistrationSetting.objects.get_or_create(workshop=workshop)
      context = {'workshop': workshop}
      return render(request, 'bcse_app/WorkshopRegistrants.html', context)
    else:
      raise models.Workshop.DoesNotExist

  except models.Workshop.DoesNotExist:
    messages.error(request, 'Workshop not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# LIST OF ALL REGISTRANTS ACROSS ALL WORKSHOPS
##########################################################
def workshopsRegistrants(request):
  try:

    if request.user.is_anonymous or request.user.userProfile.user_role not in  ['A', 'S'] :
      raise CustomException('You do not have the permission to view workshop registrants')

    searchForm = forms.RegistrantsSearchForm(user=request.user, prefix="registrants_search")
    if request.method == 'GET':

      query_filter = Q()
      workshop_category_filter = None
      workshop_filter = None
      year_filter = None
      status_filter = None

      workshop_category = [int(i) for i in request.GET.getlist('registrants_search-workshop_category', '')]
      workshop = [int(i) for i in request.GET.getlist('registrants_search-workshop', '')]
      year = request.GET.get('registrants_search-year', '')
      status = request.GET.getlist('registrants_search-status', '')
      sort_by = request.GET.get('registrants_search-sort_by', '')

      if workshop_category:
        print(workshop_category)
        workshop_category_filter = Q(workshop_registration_setting__workshop__workshop_category__id__in=workshop_category)
        query_filter = query_filter & workshop_category_filter
      if workshop:
        workshop_filter = Q(workshop_registration_setting__workshop__id__in=workshop)
        query_filter = query_filter & workshop_filter
      if year:
        year_filter = Q(workshop_registration_setting__workshop__start_date__year=int(year))
        query_filter = query_filter & year_filter
      if status:
        status_filter  = Q(status__in=status)
        query_filter = query_filter & status_filter

      print(query_filter)
      registrations = models.Registration.objects.all().filter(query_filter).distinct()
      print(registrations.count())

      direction = request.GET.get('direction') or 'asc'
      ignorecase = request.GET.get('ignorecase') or 'false'

      sort_order = []
      if sort_by:
        if sort_by == 'title':
          sort_order.append({'order_by': 'workshop_registration_setting__workshop__name', 'direction': 'asc', 'ignorecase': 'true'})
        elif sort_by == 'year':
          sort_order.append({'order_by': 'workshop_registration_setting__workshop__start_date__year', 'direction': 'asc', 'ignorecase': 'true'})
        elif sort_by == 'status':
          sort_order.append({'order_by': 'status', 'direction': 'asc', 'ignorecase': 'true'})

      sort_order.append({'order_by': 'created_date', 'direction': 'asc', 'ignorecase': 'false'})

      registrations = paginate(request, registrations, sort_order, settings.DEFAULT_ITEMS_PER_PAGE)

    if request.is_ajax():
      context = {'registrations': registrations}
      response_data = {}
      response_data['success'] = True
      response_data['html'] = render_to_string('bcse_app/WorkshopsRegistrantsTableView.html', context, request)
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")
    else:
      context = {'registrations': registrations, 'searchForm': searchForm}
      return render(request, 'bcse_app/WorkshopsRegistrants.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# UPLOAD WORKSHOPS VIA AN JSON FILE
##########################################################
@login_required
def workshopsUpload(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to upload workshops')

    if request.method == 'GET':
      form = forms.WorkshopsUploadForm(user=request.user)
      context = {'form': form}
      return render(request, 'bcse_app/WorkshopsUploadModal.html', context)
    elif request.method == 'POST':
      form = forms.WorkshopsUploadForm(user=request.user, files=request.FILES, data=request.POST)
      response_data = {}

      if form.is_valid():
        if request.FILES:
          f = request.FILES['file']
          filename = f.name
          name = filename.split(".")[0]
          extension = filename.split(".")[-1]
          decoded_file = f.read() #.decode("ISO-8859-1")
          data = json.loads(decoded_file)
          total_workshops = 0
          uploaded_workshops = 0
          for row in data:
            total_workshops += 1
            nid = row['nid']
            category = row['workshop_category']
            if category:
              title = row['title']
              sub_title = row['workshop_category']
              summary = row['sub_title']
              description = row['description']
              location = row['location']
              if not location:
                location = 'TBD'

              start_date = row['start_date']
              if start_date:
                start_date = datetime.datetime.strptime(row['start_date'], '%Y-%m-%d %H:%M:%S')
              else:
                start_date = datetime.datetime.now()

              end_date = row['end_date']
              if end_date:
                end_date = datetime.datetime.strptime(row['end_date'], '%Y-%m-%d %H:%M:%S')
              else:
                end_date = start_date
              registration_type = row['registration_type']
              capacity = row['capacity']
              status = row['status']
              image_url = row['uri']
              if image_url:
                if 'storage-field-preview-image://' in image_url:
                  image_url = image_url.replace('storage-field-preview-image://', 'https://bcoe.s3.amazonaws.com/').replace(' ', '%20')
                elif 'public://' in image_url:
                  image_url = image_url.replace('public://', 'https://bcse.northwestern.edu/sites/default/files/').replace(' ', '%20')

              workshop_category = models.WorkshopCategory.objects.all().filter(name=category).first()
              workshop, created = models.Workshop.objects.get_or_create(nid=nid, workshop_category=workshop_category, name=title, sub_title=sub_title, summary=summary, description=description, start_date=start_date.date(), start_time=start_date.time(), end_date=end_date.date(), end_time=end_date.time(), location=location)
              if status == 1:
                workshop.status = 'A'
              else:
                workshop.status = 'I'

              if workshop.start_time.hour == 0 and workshop.start_time.minute == 0 and workshop.start_time.second == 0:
                workshop.start_time = None
              if workshop.end_time.hour == 0 and workshop.end_time.minute == 0 and workshop.end_time.second == 0:
                workshop.end_time = None

              workshop.save()
              if image_url:
                try:
                  filename_base, filename_ext = os.path.splitext(image_url)
                  name, _ = urlretrieve(image_url)
                  workshop.image.save('tempfile.%s'%filename_ext, File(open(name, 'rb')))
                except Exception as e:
                  print('exception occurred', e)
                  pass
                finally:
                  urlcleanup()

              if registration_type:
                if registration_type == 'register':
                  reg_type = 'R'
                else:
                  reg_type = 'A'
                workshop_registration_setting, created = models.WorkshopRegistrationSetting.objects.get_or_create(workshop=workshop)
                workshop_registration_setting.registration_type = reg_type
                if capacity:
                  workshop_registration_setting.capacity = capacity
                workshop_registration_setting.save()
              if created:
                uploaded_workshops += 1

          response_data['success'] = True
          response_data['message'] = "%s out of %s workshops were successfully uploaded. " % (uploaded_workshops, total_workshops)
        else:
          response_data['success'] = False
      else:
        print(form.errors)
        response_data['success'] = False

      context = {'form': form}
      response_data['html'] = render_to_string('bcse_app/WorkshopsUploadModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# VIEW USER PROFILE
##########################################################
def userProfileView(request, id=''):
  try:

    if '' != id:
      userProfile = models.UserProfile.objects.get(id=id)
    else:
      raise models.UserProfile.DoesNotExist

    if request.user.userProfile.user_role not in  ['A', 'S'] and request.user.id != userProfile.user.id:
      raise CustomException('You do not have the permission to view this user profile')

    if request.method == 'GET':
      workshop_list = workshopsList(request, 'table', id)
      reservations = reservationsList(request, id)
      context = {'userProfile': userProfile, 'workshop_list': workshop_list, 'reservations': reservations}

      if request.user.userProfile.user_role in  ['A', 'S']:
        return render(request, 'bcse_app/UserProfileView.html', context)
      else:
        return render(request, 'bcse_app/MyProfileView.html', context)

    return http.HttpResponseNotAllowed(['GET'])

  except models.UserProfile.DoesNotExist:
    messages.error(request, "User profile not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# EDIT USER PROFILE
####################################
@login_required
def userProfileEdit(request, id=''):
  try:
    if '' != id:
      userProfile = models.UserProfile.objects.get(id=id)
    else:
      raise models.UserProfile.DoesNotExist


    if request.user.userProfile.user_role != 'A' and request.user.id != userProfile.user.id:
      raise CustomException('You do not have the permission to edit this user profile')

    if request.method == 'GET':
      userForm = forms.UserForm(instance=userProfile.user, user=request.user, prefix="user")
      userProfileForm = forms.UserProfileForm(instance=userProfile, user=request.user, prefix="user_profile")
      context = {'userProfileForm': userProfileForm, 'userForm': userForm}
      return render(request, 'bcse_app/UserProfileEdit.html', context)

    elif request.method == 'POST':
      data = request.POST.copy()
      data.__setitem__('user_profile-user', userProfile.user.id)
      #convert email to lowercase before save
      data.__setitem__('user-email', data.__getitem__('user-email').lower())
      data.__setitem__('user-username', data.__getitem__('user-email').lower())
      data.__setitem__('user-password', userProfile.user.password)
      data.__setitem__('user-last_login', userProfile.user.last_login)
      data.__setitem__('user-date_joined', userProfile.user.date_joined)

      subscriber_hash = hashlib.md5(userProfile.user.email.lower().encode("utf-8")).hexdigest()
      subscribed = userProfile.subscribe
      old_email = userProfile.user.email
      old_first_name = userProfile.user.first_name
      old_last_name = userProfile.user.last_name
      old_phone_number = userProfile.phone_number

      userForm = forms.UserForm(data, instance=userProfile.user, user=request.user, prefix='user')
      userProfileForm = forms.UserProfileForm(data, files=request.FILES,  instance=userProfile, user=request.user, prefix="user_profile")
      print(request.FILES)
      response_data = {}

      if userForm.is_valid(userProfile.user.id) and userProfileForm.is_valid():
        userForm.save()
        savedUserProfile = userProfileForm.save()

        #user unsubscribed
        if subscribed and not savedUserProfile.subscribe:
          subscription(savedUserProfile, 'delete', subscriber_hash)
        #user subscribed
        elif not subscribed and savedUserProfile.subscribe:
          subscription(savedUserProfile, 'add')
        #user email, first name or last name changed
        elif old_email != savedUserProfile.user.email or old_first_name != savedUserProfile.user.first_name or old_last_name != savedUserProfile.user.last_name or old_phone_number != savedUserProfile.phone_number:
          subscription(savedUserProfile, 'update', subscriber_hash)

        messages.success(request, "User profile saved successfully")
        response_data['success'] = True
      else:
        print(userForm.errors)
        print(userProfileForm.errors)
        context = {'userProfileForm': userProfileForm, 'userForm': userForm}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/UserProfileEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.UserProfile.DoesNotExist:
    messages.error(request, "User profile not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# DELETE USER PROFILE
##########################################################
@login_required
def userProfileDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete this user')
    if '' != id:
      userProfile = models.UserProfile.objects.get(id=id)
      user = userProfile.user
      user.delete()
      messages.success(request, "User deleted")

    return shortcuts.redirect('bcse:users')

  except models.UserProfile.DoesNotExist:
    messages.success(request, "User not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# LIST OF HOMEPAGE BLOCKS
##########################################################
@login_required
def homepageBlocks(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view homepage blocks')

    homepage_blocks = models.HomepageBlock.objects.all()
    context = {'homepage_blocks': homepage_blocks}
    return render(request, 'bcse_app/HomepageBlocks.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# EDIT HOMEPAGE BLOCK
##########################################################
@login_required
def homepageBlockEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit homepage block')
    if '' != id:
      homepage_block = models.HomepageBlock.objects.get(id=id)
    else:
      homepage_block = models.HomepageBlock()

    if request.method == 'GET':
      form = forms.HomepageBlockForm(instance=homepage_block)
      context = {'form': form}
      return render(request, 'bcse_app/HomepageBlockEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.HomepageBlockForm(data, files=request.FILES, instance=homepage_block)
      if form.is_valid():
        savedHomepageBlock = form.save()
        messages.success(request, "Homepage Block saved")
        return shortcuts.redirect('bcse:homepageBlockEdit', id=savedHomepageBlock.id)
      else:
        print(form.errors)
        message.error(request, "Homepage Block could not be saved. Check the errors below.")
        context = {'form': form}
        return render(request, 'bcse_app/HomepageBlockEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# DELETE HOMEPAGE BLOCK
##########################################################
@login_required
def homepageBlockDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete homepage block')
    if '' != id:
      homepage_block = models.HomepageBlock.objects.get(id=id)
      homepage_block.delete()
      messages.success(request, "Homepage Block deleted")

    return shortcuts.redirect('bcse:homepageBlocks')

  except models.HomepageBlock.DoesNotExist:
    messages.success(request, "Homepage Block not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# LIST OF TEACHER LEADERS
##########################################################
@login_required
def teacherLeaders(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view teacher leaders')

    teacher_leaders = models.TeacherLeader.objects.all()
    context = {'teacher_leaders': teacher_leaders}
    return render(request, 'bcse_app/TeacherLeaders.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# EDIT TEACHER LEADERS
##########################################################
@login_required
def teacherLeaderEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit teacher leader')
    if '' != id:
      teacher_leader = models.TeacherLeader.objects.get(id=id)
    else:
      teacher_leader = models.TeacherLeader()

    if request.method == 'GET':
      form = forms.TeacherLeaderForm(instance=teacher_leader)
      context = {'form': form}
      return render(request, 'bcse_app/TeacherLeaderEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.TeacherLeaderForm(data, files=request.FILES, instance=teacher_leader)
      if form.is_valid():
        savedTeacherLeader = form.save()
        messages.success(request, "Teacher Leader saved")
        return shortcuts.redirect('bcse:teacherLeaderEdit', id=savedTeacherLeader.id)
      else:
        print(form.errors)
        message.error(request, "Teacher Leader could not be saved. Check the errors below.")
        context = {'form': form}
        return render(request, 'bcse_app/TeacherLeaderEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# DELETE TEACHER LEADER
##########################################################
@login_required
def teacherLeaderDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete teacher leader')
    if '' != id:
      teacher_leader = models.TeacherLeader.objects.get(id=id)
      teacher_leader.delete()
      messages.success(request, "Teacher Leader deleted")

    return shortcuts.redirect('bcse:teacherLeaders')

  except models.TeacherLeader.DoesNotExist:
    messages.success(request, "Teacher Leader not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# LIST OF USERS
##########################################################
@login_required
def users(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view users')

    users = models.UserProfile.objects.all()
    order_by = 'user__email'
    direction = request.GET.get('direction') or 'asc'
    ignorecase = request.GET.get('ignorecase') or 'false'
    sort_order = [{'order_by': order_by, 'direction': direction, 'ignorecase': ignorecase}]
    users = paginate(request, users, sort_order, settings.DEFAULT_ITEMS_PER_PAGE)

    searchForm = forms.UsersSearchForm(user=request.user, prefix="user_search")

    context = {'users': users, 'searchForm': searchForm}
    return render(request, 'bcse_app/Users.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################################
# FILTER USER LIST BASED ON FILTER CRITERIA
####################################################
@login_required
def usersSearch(request):

  try:

    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to search users')

    if request.method == 'GET':

      query_filter = Q()
      email_filter = None
      first_name_filter = None
      last_name_filter = None
      user_role_filter = None
      work_place_filter = None
      joined_after_filter = None
      joined_before_filter = None
      status_filter = None

      email = request.GET.get('user_search-email', '')
      first_name = request.GET.get('user_search-first_name', '')
      last_name = request.GET.get('user_search-last_name', '')
      user_role = request.GET.get('user_search-user_role', '')
      work_place = request.GET.get('user_search-work_place', '')
      joined_after = request.GET.get('user_search-joined_after', '')
      joined_before = request.GET.get('user_search-joined_before', '')
      status = request.GET.get('user_search-status', '')
      sort_by = request.GET.get('user_search-sort_by', '')

      if email:
        email_filter = Q(user__email__icontains=email)

      if first_name:
        first_name_filter = Q(user__first_name__icontains=first_name)
      if last_name:
        last_name_filter = Q(user__last_name__icontains=last_name)

      if user_role:
        user_role_filter = Q(user_role=user_role)

      if work_place:
        work_place_filter = Q(work_place=work_place)

      if joined_after:
        joined_after_filter = Q(created_date__gte=joined_after)

      if joined_before:
        joined_before_filter = Q(created_date__lte=joined_before)

      if status:
        if status == 'A':
          status_filter = Q(user__is_active=True)
        else:
          status_filter = Q(user__is_active=False)

      if email_filter:
        query_filter = email_filter
      if first_name_filter:
        query_filter = query_filter & first_name_filter
      if last_name_filter:
        query_filter = query_filter & last_name_filter
      if user_role_filter:
        query_filter = query_filter & user_role_filter

      if work_place_filter:
        query_filter = query_filter & work_place_filter

      if joined_after_filter:
        query_filter = query_filter & joined_after_filter

      if joined_before_filter:
        query_filter = query_filter & joined_before_filter

      if status_filter:
        query_filter = query_filter & status_filter



      users = models.UserProfile.objects.all().filter(query_filter)

      if sort_by:
        if sort_by == 'email':
          order_by = 'user__email'
        elif sort_by == 'first_name':
          order_by = 'user__first_name'
        elif sort_by == 'last_name':
          order_by = 'user__last_name'
        elif sort_by == 'date_joined':
          order_by = 'created_date'
      else:
        order_by = 'user__email'

      direction = request.GET.get('direction') or 'asc'
      ignorecase = request.GET.get('ignorecase') or 'false'

      sort_order = [{'order_by': order_by, 'direction': direction, 'ignorecase': ignorecase}]

      users = paginate(request, users, sort_order, settings.DEFAULT_ITEMS_PER_PAGE)

      context = {'users': users}
      response_data = {}
      response_data['success'] = True
      response_data['html'] = render_to_string('bcse_app/UsersTableView.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# UPLOAD USERS VIA AN EXCEL TEMPLATE
##########################################################
@login_required
def usersUpload(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to upload users')

    if request.method == 'GET':
      form = forms.UsersUploadForm(user=request.user)
      context = {'form': form}
      return render(request, 'bcse_app/UsersUploadModal.html', context)
    elif request.method == 'POST':
      form = forms.UsersUploadForm(user=request.user, files=request.FILES, data=request.POST)
      response_data = {}

      if form.is_valid():
        if request.FILES:
          f = request.FILES['file']
          filename = f.name
          name = filename.split(".")[0]
          extension = filename.split(".")[-1]
          decoded_file = f.read() #.decode("ISO-8859-1")
          sheet = pyexcel.get_sheet(file_type=extension, file_content=decoded_file)
          sheet.name_columns_by_row(0)
          user_roles = dict(map(reversed, models.USER_ROLE_CHOICES))
          upload_status = ["Status"]
          total_rows = 0
          new_users = 0
          for row in sheet:
            total_rows += 1
            email = row[0]
            first_name = row[1]
            last_name = row[2]
            user_role = row[3]
            phone_number = row[4]
            twitter_handle = row[5]
            instagram_handle = row[6]
            term_id = row[7]
            if email:
              if User.objects.all().filter(username=email.lower()).count() == 0:
                if first_name:
                  if last_name:
                    if user_role:
                      #all required fields available to create user
                      newUser = create_user(request, email, first_name, last_name, user_roles[user_role], phone_number, twitter_handle, instagram_handle, term_id)
                      new_users += 1
                      upload_status.append("User created")
                    else:
                      upload_status.append("User Role is missing")
                  else:
                    upload_status.append("Last Name is missing")
                else:
                  upload_status.append("First Name is missing")
              else:
                upload_status.append("Email is already used")
            else:
              upload_status.append("Email is missing")

          sheet = pyexcel.get_sheet(file_type=extension, file_content=decoded_file)
          sheet.column += upload_status
          status_filename = '%s-%s.%s' % (name, int(time.time()), extension)
          sheet.save_as('/tmp/%s' % status_filename)
          s3_client = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

          file_url = ''
          try:
            s3_client.upload_file('/tmp/%s' % status_filename, settings.AWS_STORAGE_BUCKET_NAME, 'usersUpload/{}'.format(status_filename))
            file_url = '%s/%s/%s' % ('https://s3.amazonaws.com', settings.AWS_STORAGE_BUCKET_NAME, 'usersUpload/{}'.format(status_filename))
          except ClientError as e:
            logging.error(e)

          response_data['success'] = True
          response_data['message'] = "%s out of %s users were successfully uploaded. \
          You may review you uploaded file <u><strong><a href='%s' download>here</a></strong></u>. \
          This link will not be available after you close this dialog." % (new_users, total_rows, file_url)
        else:
          response_data['success'] = False
      else:
        print(form.errors)
        response_data['success'] = False

      context = {'form': form}
      response_data['html'] = render_to_string('bcse_app/UsersUploadModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# LIST OF WORKSPLACES
##########################################################
@login_required
def workPlaces(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view work places')

    work_places = models.WorkPlace.objects.all()
    order_by = 'name'
    direction = request.GET.get('direction') or 'asc'
    ignorecase = request.GET.get('ignorecase') or 'true'
    sort_order = [{'order_by': order_by, 'direction': direction, 'ignorecase': ignorecase}]
    work_places = paginate(request, work_places, sort_order, settings.DEFAULT_ITEMS_PER_PAGE)

    searchForm = forms.WorkPlacesSearchForm(user=request.user, prefix="work_place_search")

    context = {'work_places': work_places, 'searchForm': searchForm}
    return render(request, 'bcse_app/WorkPlaces.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################################
# FILTER WORK PLACES LIST BASED ON FILTER CRITERIA
####################################################
@login_required
def workPlacesSearch(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to search work places')

    if request.method == 'GET':

      query_filter = Q()
      name_filter = None
      work_place_type_filter = None
      district_number_filter = None
      street_address_1_filter = None
      street_address_2_filter = None
      city_filter = None
      state_filter = None
      zip_code_filter = None
      status_filter = None

      name = request.GET.get('work_place_search-name', '')
      work_place_type = request.GET.get('work_place_search-work_place_type', '')
      district_number = request.GET.get('work_place_search-district_number', '')
      street_address_1 = request.GET.get('work_place_search-street_address_1', '')
      street_address_2 = request.GET.get('work_place_search-street_address_2', '')
      city = request.GET.get('work_place_search-city', '')
      state = request.GET.get('work_place_search-state', '')
      zip_code = request.GET.get('work_place_search-zip_code', '')
      status = request.GET.get('work_place_search-status', '')
      sort_by = request.GET.get('work_place_search-sort_by', '')

      if name:
        name_filter = Q(name__icontains=name)
      if work_place_type:
        work_place_type_filter = Q(work_place_type=work_place_type)
      if district_number:
        district_number_filter = Q(district_number=district_number)
      if street_address_1:
        street_address_1_filter = Q(street_address_1=street_address_1)
      if street_address_2:
        street_address_2_filter = Q(street_address_2=street_address_2)
      if city:
        city_filter = Q(city=city)
      if state:
        state_filter = Q(state=state)
      if zip_code:
        zip_code_filter = Q(zip_code=zip_code)
      if status:
        status_filter = Q(status=status)

      if name_filter:
        query_filter = name_filter
      if work_place_type_filter:
        query_filter = query_filter & work_place_type_filter
      if district_number_filter:
        query_filter = query_filter & district_number_filter
      if street_address_1_filter:
        query_filter = query_filter & street_address_1_filter
      if street_address_2_filter:
        query_filter = query_filter & street_address_2_filter
      if city_filter:
        query_filter = query_filter & city_filter
      if state_filter:
        query_filter = query_filter & state_filter
      if zip_code_filter:
        query_filter = query_filter & zip_code_filter
      if status_filter:
        query_filter = query_filter & status_filter

      work_places = models.WorkPlace.objects.all().filter(query_filter)
      ignorecase = 'false'
      if sort_by:
        if sort_by == 'name':
          order_by = 'name'
          ignorecase = 'true'
        elif sort_by == 'status':
          order_by = 'status'
        elif sort_by == 'created_date':
          order_by = 'created_date'
      else:
        order_by = 'name'

      direction = request.GET.get('direction') or 'asc'
      sort_order = [{'order_by': order_by, 'direction': direction, 'ignorecase': ignorecase}]
      work_places = paginate(request, work_places, sort_order, settings.DEFAULT_ITEMS_PER_PAGE)

      context = {'work_places': work_places}
      response_data = {}
      response_data['success'] = True
      response_data['html'] = render_to_string('bcse_app/WorkPlacesTableView.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# EDIT WORK PLACE
##########################################################
@login_required
def workPlaceEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit work place')
    if '' != id:
      work_place = models.WorkPlace.objects.get(id=id)
    else:
      work_place = models.WorkPlace()

    if request.method == 'GET':
      form = forms.WorkPlaceForm(instance=work_place)
      context = {'form': form}
      return render(request, 'bcse_app/WorkPlaceEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.WorkPlaceForm(data, instance=work_place)
      response_data = {}
      if form.is_valid():
        savedWorkPlace = form.save()
        messages.success(request, "Work place saved successfully")
        response_data['success'] = True
      else:
        print(form.errors)
        context = {'form': form, 'userForm': userForm}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/WorkPlaceEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# DELETE WORK PLACE
##########################################################
@login_required
def workPlaceDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete work place')
    if '' != id:
      work_place = models.WorkPlace.objects.get(id=id)
      work_place.delete()
      messages.success(request, "Work place deleted")

    return shortcuts.redirect('bcse:workPlaces')

  except models.WorkPlace.DoesNotExist:
    messages.success(request, "Work place not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# UPLOAD WORK PLACES VIA AN EXCEL TEMPLATE
##########################################################
@login_required
def workPlacesUpload(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to upload work places')

    if request.method == 'GET':
      form = forms.WorkPlacesUploadForm(user=request.user)
      context = {'form': form}
      return render(request, 'bcse_app/WorkPlacesUploadModal.html', context)
    elif request.method == 'POST':
      form = forms.WorkPlacesUploadForm(user=request.user, files=request.FILES, data=request.POST)
      response_data = {}

      if form.is_valid():
        if request.FILES:
          f = request.FILES['file']
          filename = f.name
          name = filename.split(".")[0]
          extension = filename.split(".")[-1]
          decoded_file = f.read() #.decode("ISO-8859-1")
          sheet = pyexcel.get_sheet(file_type=extension, file_content=decoded_file)
          sheet.name_columns_by_row(0)
          upload_status = ["Status"]
          total_rows = 0
          new_schools = 0
          work_place_types = dict(reversed(t) for t in models.WORKPLACE_CHOICES)
          for row in sheet:
            total_rows += 1
            name = row[0]
            work_place_type = row[1]
            district_number = row[2]
            street_address_1 = row[3]
            street_address_2 = row[4]
            city = row[5]
            state = row[6]
            zip_code = row[7]
            term_id = row[8]
            if name and work_place_type: # and street_address_1 and city and state and zip_code:
              if models.WorkPlace.objects.all().filter(name=name, work_place_type=work_place_types[work_place_type]).count() > 0:
                upload_status.append("Work place already exists")
              else:
                work_place = models.WorkPlace(name=name, work_place_type=work_place_types[work_place_type], district_number=district_number, street_address_1=street_address_1, street_address_2=street_address_2, city=city, state=state, zip_code=zip_code, status='A')
                if term_id:
                  work_place.term_id = term_id
                work_place.save()
                new_schools += 1
                upload_status.append("Work place created")
            else:
              upload_status.append("One of the mandatory fields is missing")

          sheet = pyexcel.get_sheet(file_type=extension, file_content=decoded_file)
          sheet.column += upload_status
          status_filename = '%s-%s.%s' % (name, int(time.time()), extension)
          sheet.save_as('/tmp/%s' % status_filename)
          s3_client = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

          file_url = ''
          try:
            s3_client.upload_file('/tmp/%s' % status_filename, settings.AWS_STORAGE_BUCKET_NAME, 'usersUpload/{}'.format(status_filename))
            file_url = '%s/%s/%s' % ('https://s3.amazonaws.com', settings.AWS_STORAGE_BUCKET_NAME, 'usersUpload/{}'.format(status_filename))
          except ClientError as e:
            logging.error(e)

          response_data['success'] = True
          response_data['message'] = "%s out of %s workplaces were successfully uploaded. \
          You may review you uploaded file <u><strong><a href='%s' download>here</a></strong></u>. \
          This link will not be available after you close this dialog." % (new_schools, total_rows, file_url)
        else:
          response_data['success'] = False
      else:
        print(form.errors)
        response_data['success'] = False

      context = {'form': form}
      response_data['html'] = render_to_string('bcse_app/WorkPlacesUploadModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# UPLOAD WORKSHOP REGISTRATIONS VIA AN EXCEL TEMPLATE
##########################################################
@login_required
def workshopRegistrantsUpload(request, id=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to upload registrants')

    workshop = models.Workshop.objects.get(id=id)

    if request.method == 'GET':
      form = forms.UsersUploadForm(user=request.user)
      context = {'form': form, 'workshop': workshop}
      return render(request, 'bcse_app/RegistrantsUploadModal.html', context)
    elif request.method == 'POST':
      form = forms.UsersUploadForm(user=request.user, files=request.FILES, data=request.POST)
      response_data = {}

      if form.is_valid():
        if request.FILES:
          f = request.FILES['file']
          filename = f.name
          name = filename.split(".")[0]
          extension = filename.split(".")[-1]
          decoded_file = f.read() #.decode("ISO-8859-1")
          sheet = pyexcel.get_sheet(file_type=extension, file_content=decoded_file)
          sheet.name_columns_by_row(0)
          user_roles = dict(map(reversed, models.USER_ROLE_CHOICES))
          upload_status = ["Status"]
          total_rows = 0
          new_registrants = 0
          for row in sheet:
            total_rows += 1
            email = row[0]
            first_name = row[1]
            last_name = row[2]
            user_role = row[3]
            phone_number = row[4]
            twitter_handle = row[5]
            instagram_handle = row[6]
            if email:
              if User.objects.all().filter(username=email.lower()).count() == 0:
                if first_name:
                  if last_name:
                    if user_role:
                      #all required fields available to create user
                      newUser = create_user(request, email, first_name, last_name, user_roles[user_role], phone_number, twitter_handle, instagram_handle)
                      created = create_registration(request, email, workshop.id)
                      if created:
                        new_registrants += 1
                        upload_status.append("User account created and user added to workshop.")
                      else:
                        upload_status.append("User already added to workshop")
                    else:
                      upload_status.append("User account does not exist and user role is missing. User not added to workshop.")
                  else:
                    upload_status.append("User account does not exist and last name is missing. User not added to workshop.")
                else:
                  upload_status.append("User account does not exist and first name is missing. User not added to workshop.")
              else:
                #register user using existing email
                created = create_registration(request, email, workshop.id)
                if created:
                  new_registrants += 1
                  upload_status.append("User added to workshop.")
                else:
                  upload_status.append("User already added to workshop")
            else:
              upload_status.append("Email is missing. User not added to workshop.")

          sheet = pyexcel.get_sheet(file_type=extension, file_content=decoded_file)
          sheet.column += upload_status
          status_filename = '%s-%s.%s' % (name, int(time.time()), extension)
          sheet.save_as('/tmp/%s' % status_filename)
          s3_client = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID, aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY)

          file_url = ''
          try:
            s3_client.upload_file('/tmp/%s' % status_filename, settings.AWS_STORAGE_BUCKET_NAME, 'registrantsUpload/{}'.format(status_filename))
            file_url = '%s/%s/%s' % ('https://s3.amazonaws.com', settings.AWS_STORAGE_BUCKET_NAME, 'registrantsUpload/{}'.format(status_filename))
          except ClientError as e:
            logging.error(e)

          response_data['success'] = True
          response_data['message'] = "%s out of %s users were successfully added to this workshop. \
          You may review you uploaded file <u><strong><a href='%s' download>here</a></strong></u>. \
          This link will not be available after you close this dialog." % (new_registrants, total_rows, file_url)
        else:
          response_data['success'] = False
      else:
        print(form.errors)
        response_data['success'] = False

      context = {'form': form, 'workshop': workshop}
      response_data['html'] = render_to_string('bcse_app/RegistrantsUploadModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.Workshop.DoesNotExist as e:
    messages.error(request, 'Workshop not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# VIEW TEAM MEMBERS
##########################################################
@login_required
def teamMembers(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view team members')

    members = models.Team.objects.all()
    context = {'members': members}
    return render(request, 'bcse_app/TeamMembers.html', context)

  except models.Team.DoesNotExist as e:
    messages.error(request, 'Team not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# EDIT TEAM MEMBER
##########################################################
@login_required
def teamMemberEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit team member')
    if '' != id:
      member = models.Team.objects.get(id=id)
    else:
      member = models.Team()

    if request.method == 'GET':
      form = forms.TeamMemberForm(instance=member)
      context = {'form': form}
      return render(request, 'bcse_app/TeamMemberEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.TeamMemberForm(data, files=request.FILES, instance=member)
      response_data = {}
      if form.is_valid():
        savedmember = form.save()
        messages.success(request, "Team member saved successfully")
        response_data['success'] = True
      else:
        print(form.errors)
        context = {'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/TeamMemberEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# DELETE TEAM MEMBER
##########################################################
@login_required
def teamMemberDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete team member')
    if '' != id:
      member = models.Team.objects.get(id=id)
      member.delete()
      messages.success(request, "Team member deleted")

    return shortcuts.redirect('bcse:teamMembers')

  except models.Team.DoesNotExist:
    messages.success(request, "Team member not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# VIEW PARTNERS
##########################################################
@login_required
def partners(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view partners')

    partners = models.Partner.objects.all()
    context = {'partners': partners}
    return render(request, 'bcse_app/Partners.html', context)

  except models.Partner.DoesNotExist as e:
    messages.error(request, 'Team not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# EDIT PARTNER
##########################################################
@login_required
def partnerEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit partner')
    if '' != id:
      partner = models.Partner.objects.get(id=id)
    else:
      partner = models.Partner()

    if request.method == 'GET':
      form = forms.PartnerForm(instance=partner)
      context = {'form': form}
      return render(request, 'bcse_app/PartnerEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.PartnerForm(data, files=request.FILES, instance=partner)
      response_data = {}
      if form.is_valid():
        savedPartner = form.save()
        messages.success(request, "Partner saved successfully")
        response_data['success'] = True
      else:
        print(form.errors)
        context = {'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/PartnerEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# DELETE PARTNER
##########################################################
@login_required
def partnerDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete partner')
    if '' != id:
      partner = models.Partner.objects.get(id=id)
      partner.delete()
      messages.success(request, "Partner deleted")

    return shortcuts.redirect('bcse:partners')

  except models.Partner.DoesNotExist:
    messages.error(request, "Partner not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################
# SURVEYS
####################################
@login_required
def surveys(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view surveys')

    surveys = models.Survey.objects.all()
    context = {'surveys': surveys}
    return render(request, 'bcse_app/Surveys.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# EDIT SURVEY
##########################################################
@login_required
def surveyEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit survey')
    surveyComponents = surveySubmissions =  None
    if '' != id:
      survey = models.Survey.objects.get(id=id)
      surveyComponents = models.SurveyComponent.objects.all().filter(survey=survey)
      surveySubmissions = models.SurveySubmission.objects.all().filter(survey=survey)

    else:
      survey = models.Survey()

    if request.method == 'GET':
      form = forms.SurveyForm(instance=survey)
      context = {'form': form, 'surveyComponents': surveyComponents}
      if surveySubmissions:
        messages.warning(request, "This survey has %s user submissions. Please be carefull with the modification." % surveySubmissions.count())
      return render(request, 'bcse_app/SurveyEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.SurveyForm(data, files=request.FILES, instance=survey)
      if form.is_valid():
        savedSurvey = form.save()
        messages.success(request, "Survey saved successfully")
        return shortcuts.redirect('bcse:surveyEdit', id=savedSurvey.id )
      else:
        print(form.errors)
        context = {'form': form, 'surveyComponents': surveyComponents}
        return render(request, 'bcse_app/SurveyEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# PREVIEW SURVEY
##########################################################
@login_required
def surveyPreview(request, id='', page_num=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to preview survey')
    survey = models.Survey.objects.get(id=id)
    surveyComponents = models.SurveyComponent.objects.all().filter(survey=survey, page=page_num).order_by('order')
    total_pages = models.SurveyComponent.objects.all().filter(survey=survey).aggregate(Max('page'))['page__max']

    context = {'survey': survey, 'surveyComponents': surveyComponents, 'page_num': page_num, 'total_pages': total_pages}
    messages.warning(request, "This is only a preview.  You cannot submit responses here.")
    return render(request, 'bcse_app/SurveyPreview.html', context)

  except models.Survey.DoesNotExist:
    messages.success(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.SurveySubmission.DoesNotExist:
    messages.success(request, "Survey submission not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# VIEW SURVEY SUBMISSIONS
##########################################################
@login_required
def surveySubmissions(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view survey submissions')

    survey = models.Survey.objects.get(id=id)
    surveySubmissions = models.SurveySubmission.objects.all().filter(survey=survey)

    if request.method == 'GET':
      context = {'survey': survey, 'surveySubmissions': surveySubmissions}
      return render(request, 'bcse_app/SurveySubmissions.html', context)

    return http.HttpResponseNotAllowed(['GET'])

  except models.Survey.DoesNotExist as ce:
    messages.error(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# EDIT SURVEY COMPONENT
##########################################################
@login_required
def surveyComponentEdit(request, survey_id='', id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit survey component')
    survey = models.Survey.objects.get(id=survey_id)
    surveySubmissions = models.SurveySubmission.objects.all().filter(survey=survey)

    if '' != id:
      surveyComponent = models.SurveyComponent.objects.get(id=id)
    else:
      surveyComponent = models.SurveyComponent(survey=survey)

    if request.method == 'GET':
      form = forms.SurveyComponentForm(instance=surveyComponent)
      context = {'form': form, 'survey': survey}
      return render(request, 'bcse_app/SurveyComponentEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.SurveyComponentForm(data, files=request.FILES, instance=surveyComponent)
      response_data = {}
      if form.is_valid():
        savedSurveyComponent = form.save()
        messages.success(request, "Survey Component saved successfully")
        response_data['success'] = True
      else:
        print(form.errors)
        context = {'form': form, 'survey': survey}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/SurveyComponentEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# DELETE SURVEY COMPONENT
##########################################################
@login_required
def surveyComponentDelete(request, survey_id='', id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete survey component')
    if '' != id:
      surveyComponent = models.SurveyComponent.objects.get(id=id)
      surveySubmissions = models.SurveySubmission.objects.all().filter(survey=surveyComponent.survey)
      surveyComponent.delete()
      messages.success(request, "Survey component deleted")

    return shortcuts.redirect('bcse:surveyEdit', id=surveyComponent.survey.id )

  except models.SurveyComponent.DoesNotExist:
    messages.success(request, "Survey Component not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# DELETE SURVEY
##########################################################
@login_required
def surveyDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete survey')
    if '' != id:
      survey = models.Survey.objects.get(id=id)
      surveySubmissions = models.SurveySubmissions.objects.all().filter(survey=survey)
      submissions = surveySubmissions.count()
      survey.delete()
      if submissions > 0:
        messages.success(request, "Survey deleted along with %s submissions" % submissions)
      else:
        messages.success(request, "Survey deleted")

    return shortcuts.redirect('bcse:surveys')

  except models.Survey.DoesNotExist:
    messages.success(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# SURVEY SUBMISSION BY USER
##########################################################
def surveySubmission(request, survey_id='', submission_uuid='', page_num=''):
  try:
    survey = models.Survey.objects.get(id=survey_id)
    total_pages = models.SurveyComponent.objects.all().filter(survey=survey).aggregate(Max('page'))['page__max']
    if request.user.is_anonymous:
      user = None
    else:
      user = request.user.userProfile

    if '' != submission_uuid:
      submission = models.SurveySubmission.objects.get(UUID=submission_uuid)
    else:
      submission = models.SurveySubmission.objects.create(UUID=uuid.uuid4(), survey=survey, user=user, ip_address=request.META['REMOTE_ADDR'])
      submission.save()
      return shortcuts.redirect('bcse:surveySubmission', survey_id=survey.id, submission_uuid=submission.UUID, page_num=1)

    if '' == page_num:
      page_num = 1

    if page_num <= total_pages:
        surveyComponents = models.SurveyComponent.objects.all().filter(survey=survey, page=page_num).order_by('order')
    else:
      raise CustomException('Survey does not have the request page number')

    for surveyComponent in surveyComponents:
      surveyResponse, created = models.SurveyResponse.objects.get_or_create(submission=submission, survey_component=surveyComponent)
      if surveyResponse.response is None:
        surveyResponse.response = ''
        surveyResponse.save()

    SurveyResponseFormSet = modelformset_factory(models.SurveyResponse, form=forms.SurveyResponseForm, can_delete=False, can_order=False, extra=0)
    if request.method == 'GET':
      formset = SurveyResponseFormSet(queryset=models.SurveyResponse.objects.filter(submission=submission, survey_component__in=surveyComponents))
      context = {'survey': survey, 'formset': formset, 'submission': submission, 'page_num': page_num, 'total_pages': total_pages}
      return render(request, 'bcse_app/SurveySubmission.html', context)

    elif request.method == 'POST':
      data = request.POST.copy()
      print(data)
      formset = SurveyResponseFormSet(data, request.FILES, queryset=models.SurveyResponse.objects.filter(submission=submission, survey_component__in=surveyComponents))
      if formset.is_valid():
        formset.save()
        if page_num < total_pages:
          messages.success(request, 'Page %s has been saved' % page_num)
          return shortcuts.redirect('bcse:surveySubmission', survey_id=survey.id, submission_uuid=submission.UUID, page_num=page_num+1)
        else:
          submission.status = 'S'
          submission.save()
          messages.success(request, 'The survey has been submitted')
          return shortcuts.redirect('bcse:home')
      else:
        messages.error(request, 'Please correct the errors below and resubmit')
        context = {'survey': survey, 'formset': formset, 'submission': submission, 'page_num': page_num, 'total_pages': total_pages}
        return render(request, 'bcse_app/SurveySubmission.html', context)
    return http.HttpResponseNotAllowed(['GET', 'POST'])
  except models.Survey.DoesNotExist:
    messages.success(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# SURVEY SUBMISSION VIEW BY ADMIN
##########################################################
@login_required
def surveySubmissionView(request, id='', submission_uuid=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view survey submission')
    survey = models.Survey.objects.get(id=id)
    submission = models.SurveySubmission.objects.get(UUID=submission_uuid, survey=survey)
    surveyResponses = models.SurveyResponse.objects.all().filter(submission=submission).order_by('survey_component__page', 'survey_component__order')
    context = {'survey': survey, 'submission': submission, 'surveyResponses': surveyResponses}
    return render(request, 'bcse_app/SurveySubmissionView.html', context)


  except models.Survey.DoesNotExist:
    messages.success(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.SurveySubmission.DoesNotExist:
    messages.success(request, "Survey submission not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# SURVEY SUBMISSION EDIT BY ADMIN TO UPDATE SUBMISSION STATUS
##########################################################
@login_required
def surveySubmissionEdit(request, id='', submission_uuid=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit survey submission')
    survey = models.Survey.objects.get(id=id)
    submission = models.SurveySubmission.objects.get(UUID=submission_uuid, survey=survey)

    if request.method == 'GET':
      form = forms.SurveySubmissionForm(instance=submission)
      context = {'survey': survey, 'submission': submission, 'form': form}
      return render(request, 'bcse_app/SurveySubmissionEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.SurveySubmissionForm(data, instance=submission)
      response_data = {}
      if form.is_valid():
        form.save()
        response_data['success'] = True
      else:
        context = {'survey': survey, 'submission': submission, 'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/SurveySubmissionEdit.html', context, request)
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  except models.Survey.DoesNotExist:
    messages.success(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.SurveySubmission.DoesNotExist:
    messages.success(request, "Survey submission not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# SURVEY SUBMISSION DELETE BY ADMIN
##########################################################
@login_required
def surveySubmissionDelete(request, id='', submission_uuid=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete survey submission')
    survey = models.Survey.objects.get(id=id)
    submission = models.SurveySubmission.objects.get(UUID=submission_uuid, survey=survey)
    UUID = submission.UUID
    submission.delete()
    messages.success(request, 'Submission %s deleted' % UUID)
    return shortcuts.redirect('bcse:surveySubmissions', id=survey.id)

  except models.Survey.DoesNotExist:
    messages.success(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.SurveySubmission.DoesNotExist:
    messages.success(request, "Survey submission not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
########################################################################
# PAGINATE THE QUERYSET BASED ON THE ITEMS PER PAGE AND SORT ORDER
########################################################################
@login_required
def paginate(request, queryset, sort_order, count=settings.DEFAULT_ITEMS_PER_PAGE):

  ordering_list = []

  if sort_order:
    for order in sort_order:
      order_by = order['order_by']
      direction = order['direction']
      ignorecase = order['ignorecase']

      ordering = order_by

      if ignorecase == 'true':
        ordering = Lower(ordering)
        if direction == 'desc':
          ordering = ordering.desc()
      else:
        if direction == 'desc':
          ordering = '-{}'.format(ordering)

      ordering_list.append(ordering)

    queryset = queryset.order_by(*ordering_list)

  paginator = Paginator(queryset, count)
  page = request.GET.get('page')
  try:
    object_list = paginator.page(page)
  except PageNotAnInteger:
    # If page is not an integer, deliver first page.
    object_list = paginator.page(1)
  except EmptyPage:
    # If page is out of range (e.g. 9999), deliver last page of results.
    object_list = paginator.page(paginator.num_pages)

  return object_list

#######################################
# UPDATE MAILING LIST SUBSCRIPTION
#######################################
def subscription(userProfile, status, subscriber_hash=None):
  api_key = settings.MAILCHIMP_API_KEY
  server = settings.MAILCHIMP_DATA_CENTER
  list_id = settings.MAILCHIMP_EMAIL_LIST_ID

  mailchimp = Client()
  mailchimp.set_config({
      "api_key": api_key,
      "server": server,
  })

  try:
    if status == 'add':
      member_info = {
        "email_address": userProfile.user.email,
        "merge_fields": {"FNAME": userProfile.user.first_name, "LNAME": userProfile.user.last_name, "PHONE": userProfile.phone_number},
        "status": "subscribed",
      }
      response = mailchimp.lists.add_list_member(list_id, member_info)

    elif status == 'delete':
      response = mailchimp.lists.delete_list_member(list_id, subscriber_hash)

    else:
      member_info = {
        "email_address": userProfile.user.email,
        "merge_fields": {"FNAME": userProfile.user.first_name, "LNAME": userProfile.user.last_name, "PHONE": userProfile.phone_number},
        "status": "subscribed",
      }
      response = mailchimp.lists.update_list_member(list_id, subscriber_hash, member_info)

    #print("response: {}".format(response))

  except ApiClientError as error:
    print("An exception occurred: {}".format(error.text))

#####################################################
# SEND A CONFIRMATION EMAIL TO ADMINS AND THE USER
# WHEN A NEW RESERVATIONIS MADE
#####################################################
def send_reservation_confirmation_email(request, reservation):
  current_site = Site.objects.get_current()
  domain = current_site.domain
  subject = 'Baxter Box Reservation Confirmed'

  context = {'reservation': reservation, 'domain': domain}
  body = get_template('bcse_app/EmailReservationConfirmation.html').render(context)
  receipients = models.UserProfile.objects.all().filter(Q(user_role__in=['A', 'S']) | Q(id=reservation.user.id)).values_list('user__email', flat=True)
  email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, receipients)
  email.content_subtype = "html"
  email.send(fail_silently=True)


#####################################################
# SEND A NOTIFICATION EMAIL TO ADMINS AND THE USER
# WHEN A NEW MESSAGE IS POSTED FOR A RESERVATION
#####################################################
def send_reservation_message_email(request, reservation_message):
  current_site = Site.objects.get_current()
  domain = current_site.domain
  subject = 'You have a new message about your Baxter Box Reservation'

  context = {'reservation_message': reservation_message, 'domain': domain}
  body = get_template('bcse_app/EmailNewMessage.html').render(context)
  receipients = models.UserProfile.objects.all().filter(Q(user_role__in=['A', 'S']) | Q(id=reservation_message.reservation.user.id)).exclude(id=reservation_message.created_by.id).values_list('user__email', flat=True)
  email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, receipients)
  email.content_subtype = "html"
  email.send(fail_silently=True)


#####################################################
# CREATE A NEW USER WITH RANDOM PASSWORD
#####################################################
def create_user(request, email, first_name, last_name, user_role, phone_number, twitter_handle, instagram_handle, term_id=None):
  #all required fields available to create user
  user = User.objects.create_user(email.lower(),
                    email.lower(),
                    User.objects.make_random_password())
  user.first_name = first_name
  user.last_name = last_name
  user.is_active = True
  user.save()
  newUser = models.UserProfile()
  newUser.user_role = user_role
  if phone_number:
    newUser.phone_number = phone_number
  if twitter_handle:
    newUser.twitter_handle = twitter_handle
  if instagram_handle:
    newUser.instagram_handle = instagram_handle
  if term_id and isinstance(term_id, int):
    work_place = models.WorkPlace.objects.all().filter(term_id=term_id).first()
    newUser.work_place = work_place
  newUser.user = user
  newUser.save()

  return newUser


#####################################################
# CREATE A WORKSHOP REGISTRATION RECORD FOR A USER
#####################################################
def create_registration(request, email, workshop_id):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to create registration')

    workshop = models.Workshop.objects.get(id=workshop_id)
    if workshop.enable_registration and workshop.registration_setting and workshop.registration_setting.registration_type:
      if workshop.registration_setting.registration_type == 'R':
        default_registration_status = 'R'
      else:
        default_registration_status = 'A'
    else:
      raise CustomException('Please enable registration and select a Registration Type for this workshop before creating registration.')

    user = models.UserProfile.objects.get(user__email=email)
    workshop_registration, created = models.Registration.objects.get_or_create(workshop_registration_setting=workshop.registration_setting, status=default_registration_status, user=user)
    if created:
      return True
    else:
      return False

  except models.Workshop.DoesNotExist as e:
    messages.error(request, 'Workshop not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
