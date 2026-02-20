from django.shortcuts import render
from bcse_app import models, forms
from bcse_app.exceptions import CustomException
from django import http, shortcuts, template
from django.contrib import auth, messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.models import User
from django.db.models import Q, F, CharField
from django.db.models.functions import Lower, Concat
from django.db.models import Sum, Window
from django.db.models.functions import Coalesce
import datetime, time
from .utils import Calendar, AdminCalendar, CalendarEquipmentSet, validateReCaptcha
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
from django.db.models import Case, Value, When
from django.core.mail import EmailMessage
import pyexcel
import boto3
from botocore.exceptions import ClientError
from django.forms import modelformset_factory, inlineformset_factory
import uuid
from urllib.request import urlretrieve, urlcleanup
from django.core.files import File
from dal import autocomplete
from django.db.models import Count
import xlwt
from PIL import ImageColor
import copy
import re
import html
from django.utils.encoding import smart_str
import pytz
import sys
from django.urls import reverse
from django.contrib.postgres.aggregates import ArrayAgg
from itertools import chain

# Create your views here.

from django.http import HttpResponse

####################################
# HOMEPAGE
####################################
def home(request):
  """
  home is called from the path 'about/home'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/Home.html' which is the home page
  """
  homepage_blocks = models.HomepageBlock.objects.all().filter(status='A').order_by('order')
  members = models.Team.objects.all().filter(status='A').exclude(former_member=True).order_by('order')
  context = {'homepage_blocks': homepage_blocks, 'members': members}
  return render(request, 'bcse_app/Home.html', context)

####################################
# ADMIN CONFIGURATION
####################################
@login_required
def adminConfiguration(request):
  """
  adminConfiguration is called from the path 'about/adminConfiguration'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/AdminConfiguration.html' which displays admin settings and options
  :raises CustomException: raises an exception and redirects users to the page they were on before the error occurs
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in 'AS':
      raise CustomException('You do not have the permission to access this configuration')

    context = {}
    return render(request, 'bcse_app/AdminConfiguration.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def aboutBCSE(request):
  """
  aboutBCSE is called from the path 'about/BCSE'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/AboutBCSE.html' which is a page about BCSE
  """
  collaborators = models.Collaborator.objects.all().filter(status='A').order_by('order')
  context = {'collaborators': collaborators}
  return render(request, 'bcse_app/AboutBCSE.html', context)

def aboutCenters(request):
  """
  aboutCenters is called from the path 'about/centers'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/AboutCenters.html' which is a page about the centers
  """
  context = {}
  return render(request, 'bcse_app/AboutCenters.html', context)

def aboutPartners(request):
  """
  aboutPartners is called from the path 'about/partners'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/AboutPartners.html', a page about school partners
  """
  partners = models.Partner.objects.all().filter(status='A').order_by('order')
  collaborators = models.Collaborator.objects.all().filter(status='A', highlight=True).order_by('order')
  context = {'partners': partners, 'collaborators': collaborators}
  return render(request, 'bcse_app/AboutPartners.html', context)

def aboutTeam(request):
  """
  aboutTeam is called from the path 'about/team'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/AboutTeam.html', a page about the BCSE team
  """
  members = models.Team.objects.all().filter(status='A').exclude(former_member=True).order_by('order')
  former_members = models.Team.objects.all().filter(status='A', former_member=True).order_by('order')
  context = {'members': members, 'former_members': former_members}
  return render(request, 'bcse_app/AboutTeam.html', context)

def aboutTeacherLeaders(request):
  """
  aboutTeacherLeaders is called from the path 'about/teacherLeaders'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/AboutTeacherLeaders.html', a page abou the BCSE teacher leaders
  """
  teacherLeaders = models.TeacherLeader.objects.all().filter(status='A', bcse_role='T', highlight=True)
  context = {'teacherLeaders': teacherLeaders}
  return render(request, 'bcse_app/AboutTeacherLeaders.html', context)

def contactUs(request):
  """
  contactUs is called from the path 'about/contactUs'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/ContactUs.html', a page with BCSE contact information
  """
  context = {}
  return render(request, 'bcse_app/ContactUs.html', context)

####################################
# BAXTER BOX INFO
####################################
def baxterBoxInfo(request):
  """
  baxterBoxInfo is called from the path 'forClassrooms/baxterBoxInfo'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/BaxterBoxInfo.html', a page about the baxter box program
  :raises CustomException: raises an exception and redirects user to page they were on before encountering error
  """
  try:
    current_date = datetime.datetime.now().date()
    #blackout_dates = models.BaxterBoxBlackoutDate.objects.all().filter(Q(start_date__gte=current_date) | Q(end_date__gte=current_date))
    blackout_messages = models.BaxterBoxMessage.objects.all().filter(status='A', message_type='B')

    activities = models.Activity.objects.all().filter(status='A').distinct()
    equipment_types = models.EquipmentType.objects.all().filter(status='A', featured=True).distinct().order_by('order')
    if request.session.get('baxter_box_search', False):
      searchForm = forms.BaxterBoxSearchForm(initials=request.session['baxter_box_search'])
    else:
      searchForm = forms.BaxterBoxSearchForm(initials=None)

    context = {'activities': activities, 'equipment_types': equipment_types, 'blackout_messages': blackout_messages, 'searchForm': searchForm}
    return render(request, 'bcse_app/BaxterBoxInfo.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def baxterBoxSearch(request):
  """
  baxterBoxSearch is called from the path 'forClassrooms/baxterBoxInfo'
  :param request: request from the browser
  :returns: redirects to user a JSON view of response_data or redirects to an error page
  :raises CustomException: raises an exception and redirects user to page they were on before encountering error
  """
  try:
    if request.method == 'GET':
      activities = models.Activity.objects.all().filter(status='A').distinct()
      tags = models.Tag.objects.all().filter(status='A')

      #set session variable
      request.session['baxter_box_search'] = {}

      for tag in tags:
        sub_tags = request.GET.getlist('tag_%s'%tag.id, '')
        request.session['baxter_box_search']['tag_'+str(tag.id)] = sub_tags
        if sub_tags:
          activities = activities.filter(tags__id__in=sub_tags)

      response_data = {}
      response_data['success'] = True
      context = {'activities': activities}
      activities_html = render_to_string('bcse_app/ActivityTiles.html', context, request)

      response_data['html'] = activities_html

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# LIST OF BLACKOUT DATES
##########################################################
@login_required
def baxterBoxSettings(request):
  """
  baxterBoxSettings is called from the path 'forClassrooms/baxterBoxSettings'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/BaxterBoxSettings.html', a page with baxter box program settings
  :raises CustomException: raises an exception and redirects user to page they were on before encountering error
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view blackout dates')

    blackout_dates = models.BaxterBoxBlackoutDate.objects.all()
    baxterbox_messages = models.BaxterBoxMessage.objects.all()
    baxterbox_emails = models.ReservationDeliveryPickupEmailTemplate.objects.all()
    reservation_settings = {}
    reservation_settings['reservation_delivery_days'] = settings.BAXTER_BOX_DELIVERY_DAYS
    reservation_settings['reservation_return_days'] = settings.BAXTER_BOX_RETURN_DAYS
    reservation_settings['reservation_min_days'] = settings.BAXTER_BOX_MIN_RESERVATION_DAYS
    reservation_settings['reservation_max_days'] = settings.BAXTER_BOX_MAX_RESERVATION_DAYS
    reservation_settings['reservation_min_advance_days'] = settings.BAXTER_BOX_MIN_ADVANCE_RESERVATION_DAYS
    reservation_settings['reservation_max_advance_days'] = settings.BAXTER_BOX_MAX_ADVANCE_RESERVATION_DAYS
    reservation_settings['reservation_reminder_days'] = settings.BAXTER_BOX_RESERVATION_REMINDER_DAYS


    context = {'blackout_dates': blackout_dates, 'baxterbox_messages': baxterbox_messages, 'reservation_settings': reservation_settings, 'baxterbox_emails': baxterbox_emails}
    return render(request, 'bcse_app/BaxterBoxSettings.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# EDIT BLACKOUT DATES
##########################################################
@login_required
def blackoutDateEdit(request, id=''):
  """
  blackoutDateEdit is called from the path 'blackoutDates'
  :param request: request from the browser
  :param id='': id of blackout date to edit
  :returns: rendered template 'bcse_app/BaxterBoxBlackoutDateEdit.html' with view of message, redirect to JSON view of application or error status of blackout date message
  :returns: redirect to blackoutDates page
  :raises models.BaxterBoxBlackoutDate.DoesNotExist: redirects user to home page due to blackout date id not existing
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit blackout dates')
    if '' != id:
      blackout_date = models.BaxterBoxBlackoutDate.objects.get(id=id)
    else:
      blackout_date = models.BaxterBoxBlackoutDate()

    if request.method == 'GET':
      form = forms.BaxterBoxBlackoutDateForm(instance=blackout_date)
      context = {'form': form}
      return render(request, 'bcse_app/BaxterBoxBlackoutDateEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.BaxterBoxBlackoutDateForm(data, instance=blackout_date)
      response_data = {}
      if form.is_valid():
        savedBaxterBoxBlackoutDate = form.save()
        messages.success(request, "Blackout date saved")
        response_data['success'] = True
      else:
        print(form.errors)
        messages.error(request, "Blackout date could not be saved. Check the errors below.")
        context = {'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/BaxterBoxBlackoutDateEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# DELETE BLACKOUT DATES
##########################################################
@login_required
def blackoutDateDelete(request, id=''):
  """
  blackoutDateDelete is called from the path 'blackoutDates'
  :param request: request from the browser
  :param id='': id of blackout date to delete
  :returns: redirect to blackoutDates page
  :raises models.BaxterBoxBlackoutDate.DoesNotExist: redirects user to home page due to blackout date id not existing
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete blackout date')
    if '' != id:
      blackout_date = models.BaxterBoxBlackoutDate.objects.get(id=id)
      blackout_date.delete()
      messages.success(request, "Blackout Date deleted")

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.BaxterBoxBlackoutDate.DoesNotExist:
    messages.success(request, "Blackout Date not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# EDIT BLACKOUT MESSAGE
##########################################################
@login_required
def baxterBoxMessageEdit(request, id=''):
  """
  baxterBoxMessageEdit is called from the path 'forClassrooms/baxterBoxSettings'
  :param request: request from the browser
  :param id='': id of the baxter box message
  :returns: rendered template 'bcse_app/BaxterBoxMessageEdit.html' with view of message, redirect to JSON view of application or error status of baxter box message
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises models.BaxterBoxMessage.DoesNotExist: raises an exception and redirects user to page they were on before encountering error due to message not existing
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit baxter box message')

    if ''!= id:
      baxterbox_message = models.BaxterBoxMessage.objects.get(id=id)
    else:
      baxterbox_message = models.BaxterBoxMessage()

    if request.method == 'GET':
      form = forms.BaxterBoxMessageForm(instance=baxterbox_message)
      context = {'form': form}
      return render(request, 'bcse_app/BaxterBoxMessageEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.BaxterBoxMessageForm(data, instance=baxterbox_message)
      response_data = {}
      if form.is_valid():
        savedBaxterBoxMessage = form.save()
        messages.success(request, "Baxter Box message saved")
        response_data['success'] = True
      else:
        print(form.errors)
        messages.error(request, "Baxter Box message could not be saved. Check the errors below.")
        context = {'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/BaxterBoxMessageEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.BaxterBoxMessage.DoesNotExist:
    messages.success(request, "Baxter Box message not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# DELETE BLACKOUT MESSAGE
##########################################################
@login_required
def baxterBoxMessageDelete(request, id=''):
  """
  baxterBoxMessageDelete is called from the path '/adminConfiguration/baxter_box/settings/'
  :param request: request from the browser
  :param id='': id of the baxter box message
  :returns: rendered template 'bcse_app/BaxterBoxMessageEdit.html' with baxter box message with id deleted
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises models.BaxterBoxMessage.DoesNotExist: raises an exception and redirects user to page they were on before encountering error due to message not existing
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete baxter box message')

    if ''!= id:
      baxterbox_message = models.BaxterBoxMessage.objects.get(id=id)
      baxterbox_message.delete()

      messages.success(request, "Baxter Box message deleted")
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.BaxterBoxMessage.DoesNotExist:
    messages.success(request, "Baxter Box message not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# LIST OF BAXTER BOX COLORS
##########################################################
@login_required
def reservationColors(request):
  """
  reservationColors is called from the path 'adminConfiguration/reservationColors'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/ReservationColors.html'
  :raises CustomException: raises an exception and redirects user to page they were on before encountering error
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view Baxter Box colors')

    colors = models.ReservationColor.objects.all()
    context = {'colors': colors}
    return render(request, 'bcse_app/ReservationColors.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# EDIT BAXTER BOX COLOR
##########################################################
@login_required
def reservationColorEdit(request, id=''):
  """
  reservationColorEdit is called from the path 'adminConfiguration/reservationColors'
  :param request: request from the browser
  :param id='': id of the reservation color to edit
  :returns: JSON view of 'bcse_app/ReservationColorEdit.html' or error page
  :raises CustomException: raises an exception and redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit Baxter Box color')
    if '' != id:
      color = models.ReservationColor.objects.get(id=id)
    else:
      color = models.ReservationColor()

    if request.method == 'GET':
      form = forms.ReservationColorForm(instance=color)
      context = {'form': form}
      return render(request, 'bcse_app/ReservationColorEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.ReservationColorForm(data, instance=color)
      response_data = {}
      if form.is_valid():
        savedReservationColor = form.save()
        messages.success(request, "Baxter Box color saved")
        response_data['success'] = True
      else:
        print(form.errors)
        messages.error(request, "Baxter Box  color could not be saved. Check the errors below.")
        context = {'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/ReservationColorEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# DELETE RESERVATION COLOR
##########################################################
@login_required
def reservationColorDelete(request, id=''):
  """
  reservationColorDelete is called from the path 'adminConfiguration/reservationColors'
  :param request: request from the browser
  :param id='': id of the reservation color to delete
  :returns: redirect to reservationColors page
  :raises CustomException: raises an exception and redirects user to page they were on before encountering error due to lack of permissions
  :raises models.ReservationColor.DoesNotExist: raises an exception and redirects user to page they were on before encountering error due to reservation color not existing
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete Baxter Box Color')
    if '' != id:
      color = models.ReservationColor.objects.get(id=id)
      color.delete()
      messages.success(request, "Baxter Box color deleted")

    return shortcuts.redirect('bcse:reservationColors')

  except models.ReservationColor.DoesNotExist:
    messages.success(request, "Baxter Box color not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################
# USER LOGIN
####################################
def userSignin(request, user_email=''):
  """
  userSignin is called from the home page
  :param request: request from the browser
  :param user_email='': email of the user that wants to sign in
  :returns: rendered template 'bcse_app/SignInModal.html' with view of message, redirect to JSON view of application or error status of sign in message
  """
  email = password = ''
  print(request.method)
  redirect_url = request.GET.get('next', '')
  if request.method == 'POST':
    data = request.POST.copy()
    recaptcha_token = data.get("recaptchaToken")
    recaptcha_passed = validateReCaptcha(recaptcha_token, 'login')
    form = forms.SignInForm(data)
    response_data = {}
    if recaptcha_passed and form.is_valid():
      #email = form.cleaned_data['email'].lower()
      #password = form.cleaned_data['password']
      #user = authenticate(username=email, password=password)
      user = form.user
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
      if not recaptcha_passed:
        messages.error(request, 'reCAPTCHA validation failed')
      else:
        messages.error(request, 'Your credentials are invalid')
      context = {'form': form, 'redirect_url': redirect_url}
      response_data['success'] = False
      response_data['html'] = render_to_string('bcse_app/SignInModal.html', context, request)

    return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  elif request.method == 'GET':
    logout(request)
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
  """
  userSignout logs user out
  :param request: request from the browser
  :returns: redirect to home page
  """
  logout(request)
  messages.success(request, "You have signed out")
  return shortcuts.redirect('bcse:home')

####################################
# REGISTER
####################################
def userSignup(request):
  """
  userSignup is called from the home page
  :param request: request from the browser
  :returns: rendered template 'bcse_app/SignUpModal.html', which is the sign up page, redirect to JSON view of response_data, or redirect to error page
  :raises CustomException: raises an exception and does not allow user to create another user account
  """
  work_place = models.WorkPlace()
  redirect_url = request.GET.get('next', '')
  ########### GET ###################
  if request.method == 'GET':

    if request.user.is_anonymous or request.user.userProfile.user_role in ['A', 'S']:
      form = forms.SignUpForm(user=request.user)
      work_place_form = forms.WorkPlaceForm(instance=work_place, user=request.user, prefix='work_place')
      context = {'form': form, 'work_place_form': work_place_form}
      return render(request, 'bcse_app/SignUpModal.html', context)
    else:
      raise CustomException('You cannot create another user account')


  elif request.method == 'POST':

    recaptcha_token = request.POST.get("recaptchaToken")
    recaptcha_passed = validateReCaptcha(recaptcha_token, 'signup')

    new_work_place = None
    response_data = {}

    form = forms.SignUpForm(user=request.user, files=request.FILES, data=request.POST)
    work_place_form = forms.WorkPlaceForm(data=request.POST, instance=work_place, user=request.user, prefix='work_place')

    if recaptcha_passed and form.is_valid():
      user = User.objects.create_user(form.cleaned_data['email'].lower(),
                                      form.cleaned_data['email'].lower(),
                                      form.cleaned_data['password1'])
      user.first_name = form.cleaned_data['first_name']
      user.last_name = form.cleaned_data['last_name']
      user.is_active = True
      user.save()

      role = ''
      newUser = models.UserProfile()
      newUser.name_pronounciation = form.cleaned_data['name_pronounciation']
      newUser.user_role = form.cleaned_data['user_role']
      newUser.iein = form.cleaned_data['iein']
      newUser.grades_taught = form.cleaned_data['grades_taught']
      newUser.phone_number = form.cleaned_data['phone_number']
      newUser.twitter_handle = form.cleaned_data['twitter_handle']
      newUser.instagram_handle = form.cleaned_data['instagram_handle']
      newUser.secondary_email = form.cleaned_data['secondary_email']
      if request.FILES:
        newUser.image = request.FILES['image']
      if form.cleaned_data['subscribe']:
        newUser.subscribe = True

      if form.cleaned_data['user_role'] in ['A', 'S', 'T','P', 'D']:

        if form.cleaned_data['user_role'] in ['T','P']:
          newUser.validation_code = get_random_string(length=5)

        #get the workplace id
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
        #user selects existing workplace
        else:
          newUser.work_place = form.cleaned_data['work_place']

        newUser.user = user
        newUser.save()

      if form.cleaned_data['subscribe']:
        userDetails = {'email_address': newUser.user.email, 'first_name': newUser.user.first_name, 'last_name': newUser.user.last_name}
        if newUser.phone_number:
          userDetails['phone_number'] = newUser.phone_number
        subscription(userDetails, 'add')

        if newUser.secondary_email:
          userSecondaryDetails = {'email_address': newUser.secondary_email, 'first_name': newUser.user.first_name, 'last_name': newUser.user.last_name}
          if newUser.phone_number:
            userSecondaryDetails['phone_number'] = newUser.phone_number
          #adding a separate contact with secondary email
          subscription(userSecondaryDetails, 'add')


      domain = request.get_host()

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
      if not recaptcha_passed:
        messages.error(request, 'reCAPTCHA validation failed')
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
  """
  signinRedirect is called from the home page
  :param request: request from the browser
  :returns: redirect to home page
  """
  messages.success(request, "You have signed in")
  return shortcuts.redirect('bcse:home')

####################################
# ACTIVITIES
####################################
@login_required
def activities(request):
  """
  activities is called from the path 'forTeachers/activities'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/Activities.html', which is a page with workshops
  :raises CustomException: redirects user to page they were on before encountering error
  """
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
  """
  activityEdit is called from the path 'forTeachers/activities'
  :param request: request from the browser
  :param id='': id of the activity to edit
  :returns: rendered template 'bcse_app/ActivityEdit.html', redirect to page to activityEdit after edits saved, or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit activity')
    if '' != id:
      activity = models.Activity.objects.get(id=id)
    else:
      activity = models.Activity()

    tags = models.SubTag.objects.all().filter(status='A')
    InventoryInlineFormset = inlineformset_factory(models.Activity, models.ActivityInventory, form=forms.ActivityInventoryForm, extra=1, can_delete=True)

    if request.method == 'GET':
      form = forms.ActivityForm(instance=activity)
      formset = InventoryInlineFormset(instance=activity)
      context = {'form': form, 'formset': formset, 'tags': tags}
      return render(request, 'bcse_app/ActivityEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.ActivityForm(data, files=request.FILES, instance=activity)
      formset = InventoryInlineFormset(data, instance=activity)
      if form.is_valid() and formset.is_valid():
        savedActivity = form.save()
        formset.save()
        messages.success(request, "Activity saved")
        return shortcuts.redirect('bcse:activityEdit', id=savedActivity.id)
      else:
        print(form.errors)
        print(formset.errors)
        messages.error(request, "Activity could not be saved. Check the errors below.")
        context = {'form': form, 'formset': formset, 'tags': tags}
        return render(request, 'bcse_app/ActivityEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

###################################################
# UPDATE ACTIVITY
###################################################
@login_required
def activityUpdate(request, id='', reservation_id=''):
  """
  activityUpdate is called from the path 'forTeachers/activities'
  :param request: request from the browser
  :param id='': id of the activity to update
  :param reservationid='': id of the reservation the activity is selected for
  :returns: rendered template 'bcse_app/ActivityUpdateModal.html', redirect to JSON view of ActivityUpdateModel, or error page
  :raises CustomException: raises an exception and redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to update activity')

    activity = models.Activity.objects.get(id=id)
    ConsumableFormSet = modelformset_factory(models.Consumable, form=forms.ConsumableUpdateForm, can_delete=False, can_order=False, extra=0)
    InventoryInlineFormset = inlineformset_factory(models.Activity, models.ActivityInventory, form=forms.ActivityInventoryForm, extra=1, can_delete=True)
    ConsumableInventoryInlineFormset = inlineformset_factory(models.Consumable, models.ConsumableInventory, form=forms.ConsumableInventoryForm, extra=1, can_delete=True)


    if request.method == 'GET':
      form = forms.ActivityUpdateForm(instance=activity, prefix="activity")
      inventory_formset = InventoryInlineFormset(instance=activity)
      if '' != reservation_id:
        reservation = models.Reservation.objects.get(id=reservation_id)
        formset = ConsumableFormSet(queryset=reservation.consumables.all(), prefix="consumables")
      else:
        formset = ConsumableFormSet(queryset=activity.consumables.all(), prefix="consumables")

      consumable_inventory_formsets = [ConsumableInventoryInlineFormset(instance=ci_form.instance, prefix=f'ci-{i}') for i, ci_form in enumerate(formset.forms)]
      context = {'activity': activity, 'form': form, 'formset': formset, 'inventory_formset': inventory_formset, 'consumable_inventory_formsets': consumable_inventory_formsets}
      return render(request, 'bcse_app/ActivityUpdateModal.html', context)

    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.ActivityUpdateForm(data, instance=activity, prefix="activity")
      inventory_formset = InventoryInlineFormset(data, instance=activity)
      if '' != reservation_id:
        reservation = models.Reservation.objects.get(id=reservation_id)
        formset = ConsumableFormSet(data, queryset=reservation.consumables.all(), prefix="consumables")
      else:
        formset = ConsumableFormSet(data, queryset=activity.consumables.all(), prefix="consumables")

      consumable_inventory_formsets = []
      for i, ci_form in enumerate(formset.forms):
        prefix = f'ci-{i}'
        instance = ci_form.instance
        consumable_inventory_formset = ConsumableInventoryInlineFormset(data, instance=instance, prefix=prefix)
        consumable_inventory_formsets.append(consumable_inventory_formset)

      response_data = {}
      if form.is_valid() and formset.is_valid() and inventory_formset.is_valid() and all([cifs.is_valid() for cifs in consumable_inventory_formsets]):
        form.save()
        formset.save()
        inventory_formset.save()
        for cifs in consumable_inventory_formsets:
          cifs.save()
        response_data['success'] = True
        messages.success(request, 'Activity %s updated' % id)
      else:
        print('form errors', form.errors)
        print('formset errors', formset.errors)
        print('inventory formset errors', inventory_formset.errors)
        response_data['success'] = False
        context = {'activity': activity, 'form': form, 'formset': formset, 'inventory_formset': inventory_formset, 'consumable_inventory_formsets': consumable_inventory_formsets}
        response_data['html'] = render_to_string('bcse_app/ActivityUpdateModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except models.Activity.DoesNotExist as e:
    messages.error(request, 'Activity does not exists')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# VIEW ACTIVITY
####################################
def activityView(request, id=''):
  """
  activityUpdate is called from the path 'forTeachers/activities'
  :param request: request from the browser
  :param id='': id of the activity to view
  :returns: rendered template 'bcse_app/ActivityBaseView.html', rendered template ActivityView
  :raises CustomException: redirects user to page they were on before encountering error due to activity not existing
  """

  try:
    if '' != id:
      activity = models.Activity.objects.get(id=id)
    else:
      raise CustomException('Activity does not exist')

    if request.method == 'GET':

      if request.is_ajax():
        context = {'activity': activity}
        if 'reservation' in request.META.get('HTTP_REFERER'):
          if 'edit' in request.META.get('HTTP_REFERER') or 'new' in request.META.get('HTTP_REFERER'):
            response_data = {}
            response_data['success'] = True
            response_data['kit_name'] = activity.kit_name
            response_data['materials_equipment'] = activity.materials_equipment
            response_data['manuals_resources'] = activity.manuals_resources
            response_data['equipment_mapping'] = list(activity.equipment_mapping.all().values_list('name', flat=True))
            is_low_stock = is_activity_low_in_stock(id)
            if is_low_stock:
              low_stock_message = get_low_stock_message(id)
              response_data['low_stock_message'] = low_stock_message
              context['low_stock_message'] = low_stock_message

            response_data['is_low_stock'] = is_low_stock
            context['is_low_stock'] = is_low_stock

            response_data['html'] = render_to_string('bcse_app/ActivityView.html', context, request)
            response_data['equipment_options'] = load_equipment_options(request, activity.id)

            if request.user.is_authenticated and request.user.userProfile.user_role in ['A', 'S']:
              response_data['consumable_options'] = load_consumable_options(request, activity.id)
              response_data['consumable_mapping'] = list(activity.consumables.all().filter(status='A').distinct().values_list('id', flat=True))
            return http.HttpResponse(json.dumps(response_data), content_type="application/json")

        context = {'title': activity.kit_name, 'kit': activity, 'type': 'activity'}
        return render(request, 'bcse_app/BaxterBoxKitModal.html', context)
      else:
        context = {'activity': activity}
        return render(request, 'bcse_app/ActivityBaseView.html', context)

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def get_low_stock_message(id=''):
  try:
    if '' != id:
      activity = models.Activity.objects.get(id=id)
      rank = sys.maxsize
      low_stock_message = None
      if activity.color and activity.color.low_stock and activity.color.low_stock_message and activity.color.rank:
        rank = activity.color.rank
        low_stock_message = activity.color.low_stock_message
      for consumable in activity.consumables.all():
        if consumable.color and consumable.color.low_stock and consumable.color.low_stock_message and consumable.color.rank:
          if consumable.color.rank < rank:
            rank = consumable.color.rank
            low_stock_message = consumable.color.low_stock_message
      return low_stock_message
    else:
      raise CustomException('Activity does not exist')
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def is_activity_low_in_stock(id=''):
  try:
    if '' != id:
      activity = models.Activity.objects.get(id=id)
      is_low_stock = False
      if activity.color and activity.color.low_stock:
        return True
      for consumable in activity.consumables.all():
        if consumable.color and consumable.color.low_stock:
          is_low_stock = True
          break
      return is_low_stock
    else:
      raise CustomException('Activity does not exist')
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# CONSUMABLES
####################################
@login_required
def consumables(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view consumables')

    consumables = models.Consumable.objects.all()
    context = {'consumables': consumables}
    return render(request, 'bcse_app/Consumables.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

###################################
# EDIT CONSUMABLE
####################################
@login_required
def consumableEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit consumable')
    if '' != id:
      consumable = models.Consumable.objects.get(id=id)
    else:
      consumable = models.Consumable()

    InventoryInlineFormset = inlineformset_factory(models.Consumable, models.ConsumableInventory, form=forms.ConsumableInventoryForm, extra=1, can_delete=True)

    if request.method == 'GET':
      form = forms.ConsumableForm(instance=consumable)
      formset = InventoryInlineFormset(instance=consumable)
      context = {'form': form, 'formset': formset}
      return render(request, 'bcse_app/ConsumableEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.ConsumableForm(data, files=request.FILES, instance=consumable)
      formset = InventoryInlineFormset(data, instance=consumable)
      if form.is_valid() and formset.is_valid():
        savedConsumable = form.save()
        formset.save()
        messages.success(request, "Consumable saved")
        return shortcuts.redirect('bcse:consumableEdit', id=savedConsumable.id)
      else:
        print(form.errors)
        print(formset.errors)
        messages.error(request, "Consumable could not be saved. Check the errors below.")
        context = {'form': form, 'formset': formset}
        return render(request, 'bcse_app/ConsumableEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

###################################################
# UPDATE CONSUMABLE
###################################################
@login_required
def consumableUpdate(request, id=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to update consumable')

    consumable = models.Consumable.objects.get(id=id)
    InventoryInlineFormset = inlineformset_factory(models.Consumable, models.ConsumableInventory, form=forms.ConsumableInventoryForm, extra=1, can_delete=True)

    if request.method == 'GET':
      form = forms.ConsumableUpdateForm(instance=consumable)
      formset = InventoryInlineFormset(instance=consumable)
      context = {'form': form, 'formset': formset, 'consumable': consumable}
      return render(request, 'bcse_app/ConsumableUpdateModal.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.ConsumableUpdateForm(data, instance=consumable)
      formset = InventoryInlineFormset(data, instance=consumable)
      response_data = {}
      if form.is_valid() and formset.is_valid():
        form.save()
        formset.save()
        response_data['success'] = True
        messages.success(request, 'Consumable %s updated' % id)
      else:
        print(form.errors)
        print(formset.errors)
        response_data['success'] = False
        context = {'form': form, 'formset': formset, 'consumable': consumable}
        response_data['html'] = render_to_string('bcse_app/ConsumableUpdateModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except models.Consumable.DoesNotExist as e:
    messages.error(request, 'Consumable does not exists')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

###################################
# DELETE CONSUMABLE
####################################
@login_required
def consumableDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete consumable')
    if '' != id:
      consumable = models.Consumable.objects.get(id=id)
      consumable.delete()
      messages.success(request, "Consumable deleted")

    return shortcuts.redirect('bcse:consumables')

  except models.Consumable.DoesNotExist:
    messages.success(request, "Consumable not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# EQUIPMENT CATEGORIES
####################################
@login_required
def equipmentTypes(request):
  """
  equipmentTypes is called from the path 'forTeachers/equipment'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/EquipmentTypes.html' which is a page to view all equipment categories
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view equipment categories')

    equipment_types = models.EquipmentType.objects.all().order_by('order')
    context = {'equipment_types': equipment_types}
    return render(request, 'bcse_app/EquipmentTypes.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# EDIT EQUIPMENT CATEGORY
####################################
@login_required
def equipmentTypeEdit(request, id=''):
  """
  equipmentTypeEdit is called from the path 'forTeachers/equipment'
  :param request: request from the browser
  :param id='': id of the equipment category to edit
  :returns: rendered template 'bcse_app/EquipmentTypeEdit.html', redirect to equipment category edit page after updates are saved, or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit equipment category')
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
        messages.success(request, "Equipment Category saved")
        return shortcuts.redirect('bcse:equipmentTypeEdit', id=savedEquipmentType.id)
      else:
        print(form.errors)
        messages.error(request, "Equipment Category could not be saved. Check the errors below.")
        context = {'form': form}
        return render(request, 'bcse_app/EquipmentTypeEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# DELETE EQUIPMENT CATEGORY
####################################
@login_required
def equipmentTypeDelete(request, id=''):
  """
  equipmentTypeDelete is called from the path 'forTeachers/equipment'
  :param request: request from the browser
  :param id='': id of the equipment category to delete
  :returns: redirect to equipment category edit page after deleting
  :raises models.EquipmentType.DoesNotExist: redirects user to page they were on before encountering error due to equipment category not being found
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete equipment category')
    if '' != id:
      equipment_type = models.EquipmentType.objects.get(id=id)
      equipment_type.delete()
      messages.success(request, "Equipment Category deleted")

    return shortcuts.redirect('bcse:equipmentTypes')

  except models.EquipmentType.DoesNotExist:
    messages.success(request, "Equipment Category not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# VIEW EQUIPMENT CATEGORY
####################################
def equipmentTypeView(request, id=''):
  """
  equipmentTypeView is called from the path 'forTeachers/equipment'
  :param request: request from the browser
  :param id='': id of the equipment category to view
  :returns: rendered template 'bcse_app/BaxterBoxKitModal.html' where all equipments are or redirect to error page
  :raises CustomException: redirects user to page they were on before encountering error due to equipment not exisitng
  """
  try:
    if '' != id:
      equipment_type = models.EquipmentType.objects.get(id=id)
    else:
      raise CustomException('Equipment does not exist')

    if request.method == 'GET':
      if request.is_ajax():
        context = {'title': equipment_type.name, 'kit': equipment_type, 'type': 'equipment'}
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
  """
    equipments is called from the path 'forClassrooms/equipments'
    :param request: request from the browser
    :returns: rendered template 'bcse_app/Equipments.html', which is a page with available lab equipment
    :raises CustomException: redirects user to page they were on before encountering error
    """
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
  """
  equipmentEdit is called from the path 'forTeachers/equipments'
  :param request: request from the browser
  :param id='': id of the equipment to edit
  :returns: rendered template 'bcse_app/EquipmentEdit.html' where all equipments are if equipment cannot be saved, redirect to original equipmentEdit page if saved, or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
# DELETE EQUIPMENT CATEGORY
####################################
@login_required
def equipmentDelete(request, id=''):
  """
  equipmentDelete is called from the path 'forTeachers/equipments'
  :param request: request from the browser
  :param id='': id of the equipment to delete
  :returns: redirects to equipments page if equipment successfully deleted
  :raises models.Equipment.DoesNotExist: redirects user to page they were on before encountering error due to equipment id not existing
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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


@login_required
def equipmentOverbookedReservations(request, id='', reservation_id=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view equipment overbooked schedule')
    equipment = models.Equipment.objects.get(id=id)
    current_reservation = models.Reservation.objects.get(id=reservation_id)
    overbooked_reservations = models.Reservation.objects.all().filter(Q(equipment=equipment), ~Q(status='N'), Q(Q(delivery_date__range=(current_reservation.delivery_date, current_reservation.return_date)) | Q(return_date__range=(current_reservation.delivery_date, current_reservation.return_date)))).exclude(id=current_reservation.id).distinct()
    available_equipment = equipmentAvailableForReservation(request, id, reservation_id)
    context = {'equipment': equipment, 'current_reservation': current_reservation, 'overbooked_reservations': overbooked_reservations, 'available_equipment': available_equipment}
    return render(request, 'bcse_app/EquipmentOverbookedReservations.html', context)
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@login_required
def equipmentAvailableForReservation(request, id='', reservation_id=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view equipment availability')

    equipment = models.Equipment.objects.get(id=id)
    current_reservation = models.Reservation.objects.get(id=reservation_id)
    other_equipment_sets = models.Equipment.objects.all().filter(equipment_type=equipment.equipment_type, status='A').exclude(id=equipment.id)
    available_equipment_sets = []
    for other_equipment_set in other_equipment_sets:
      overbooked_reservations = models.Reservation.objects.all().filter(Q(equipment=other_equipment_set), ~Q(status='N'), Q(Q(delivery_date__range=(current_reservation.delivery_date, current_reservation.return_date)) | Q(return_date__range=(current_reservation.delivery_date, current_reservation.return_date)))).distinct().count()
      if overbooked_reservations == 0:
        available_equipment_sets.append(other_equipment_set)
    return available_equipment_sets
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# DELETE ACTIVITY
####################################
@login_required
def activityDelete(request, id=''):
  """
  activityDelete is called from the path 'activities'
  :param request: request from the browser
  :param id='': id of the activity to delete
  :returns: redirects to activities page if activity successfully deleted
  :raises models.Activity.DoesNotExist: redirects user to page they were on before encountering error due to activity id not existing
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
  """
  reservations is called from the path 'reservations'
  :param request: request from the browser
  :returns: list of reservations as rendered template 'bcse_app/UserReservatons.html' for admins or 'bcse_app/Reservations.html' for non-admins
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permission to view reservations
  """
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to view reservations')

    #reservations = reservationsList(request)

    #sort_order = [{'order_by': 'delivery_date', 'direction': 'desc', 'ignorecase': 'false'}]
    #reservations = paginate(request, reservations, sort_order, settings.DEFAULT_ITEMS_PER_PAGE)

    if request.session.get('reservations_search', False):
      searchForm = forms.ReservationsSearchForm(user=request.user, initials=request.session['reservations_search'], prefix="reservation_search")
      page = request.session['reservations_search']['page']
    else:
      searchForm = forms.ReservationsSearchForm(user=request.user, initials=None, prefix="reservation_search")
      page = 1

    context = {'searchForm': searchForm, 'page': page}
    if request.user.userProfile.user_role in ['A', 'S']:
      return render(request, 'bcse_app/UserReservations.html', context)
    else:
      return render(request, 'bcse_app/Reservations.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def reservationsList(request, user_id=''):
  """
  reservationsList is called from the path 'reservations'
  :param request: request from the browser
  :param user_id='': user
  :returns: list of reservations for a user
  """
  reservations = None
  if request.user.is_authenticated:
    if request.user.userProfile.user_role not in ['A', 'S']:
      reservations = models.Reservation.objects.all().filter(user__user=request.user)
    elif user_id:
      reservations = models.Reservation.objects.all().filter(user__id=user_id)
    else:
      reservations = models.Reservation.objects.all()

    reservations = reservations.order_by('delivery_date')

  return reservations

####################################
# EDIT RESERVATION
####################################
@login_required
def reservationEdit(request, id=''):
  """
  reservationEdit is called from the path 'reservations'
  :param request: request from the browser
  :param id='': id of reservation
  :returns: rendered template 'bcse_app/ReservationEdit.html' if errors present, redirect to reservationView if reservation successfully edited, or error page
  :raises models.Reservation.DoesNotExist: redirects user to page they were on before encountering error due to reservation id not existing
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions or reservation already having happened
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role == 'D':
      raise CustomException('You do not have the permission to create/edit a reservation')

    original_status = None
    current_date = datetime.datetime.now().date()

    if '' != id:
      reservation = models.Reservation.objects.get(id=id)
      original_status = reservation.status
    else:
      reservation = models.Reservation(created_by=request.user.userProfile)

    current_date = datetime.datetime.now().date()
    if request.user.userProfile.user_role in ['T', 'P'] and reservation.id:
      if reservation.user != request.user.userProfile:
        raise CustomException('You do not have the permission to edit this reservation')
      elif reservation.status in ['R', 'N', 'O', 'I']:
        raise CustomException('This reservation is %s and cannot be modified' % reservation.get_status_display())
      elif reservation.delivery_date and reservation.delivery_date < current_date:
        raise CustomException('This reservation is in the past and cannot be modified')

    reservation_settings = {}
    reservation_settings['reservation_delivery_days'] = settings.BAXTER_BOX_DELIVERY_DAYS
    reservation_settings['reservation_return_days'] = settings.BAXTER_BOX_RETURN_DAYS
    reservation_settings['reservation_min_days'] = settings.BAXTER_BOX_MIN_RESERVATION_DAYS
    reservation_settings['reservation_max_days'] = settings.BAXTER_BOX_MAX_RESERVATION_DAYS
    reservation_settings['reservation_min_advance_days'] = settings.BAXTER_BOX_MIN_ADVANCE_RESERVATION_DAYS
    reservation_settings['reservation_max_advance_days'] = settings.BAXTER_BOX_MAX_ADVANCE_RESERVATION_DAYS
    reservation_settings['reservation_reminder_days'] = settings.BAXTER_BOX_RESERVATION_REMINDER_DAYS


    blackout_dates = models.BaxterBoxBlackoutDate.objects.all().filter(Q(start_date__gte=current_date) | Q(end_date__gte=current_date))
    if blackout_dates.count() > 0:
      reservation_settings['reservation_blackout_dates'] = blackout_dates
      reservation_settings['reservation_blackout_timestamps'] = []
      for blackout_date in blackout_dates:
        reservation_settings['reservation_blackout_timestamps'].append([time.mktime(blackout_date.start_date.timetuple()), time.mktime(blackout_date.end_date.timetuple())])

    reservation_rule_messages = models.BaxterBoxMessage.objects.all().filter(status='A').order_by('-message_type')
    if reservation_rule_messages:
      reservation_settings['reservation_rule_messages'] = reservation_rule_messages

    if request.method == 'GET':
      if request.user.userProfile.user_role in ['T', 'P']:
        form = forms.ReservationForm(instance=reservation, user=request.user.userProfile, initial={'user': request.user.userProfile})
      else:
        form = forms.ReservationForm(instance=reservation, user=request.user.userProfile)

      context = {'form': form, 'reservation_settings': reservation_settings}

      return render(request, 'bcse_app/ReservationEdit.html', context)

    elif request.method == 'POST':

      data = request.POST.copy()
      form = forms.ReservationForm(data, instance=reservation, user=request.user.userProfile)

      recaptcha_token = data.get("recaptchaToken")
      recaptcha_passed = validateReCaptcha(recaptcha_token, 'reservation')

      if recaptcha_passed and form.is_valid():

        savedReservation = None


        if 'equipment_types' in form.cleaned_data and form.cleaned_data['equipment_types']:
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

          else:
            messages.error(request, "Selected equipment is unavailable for the selected dates. Please revise your dates and try making reservation again.")
            context = {'form': form, 'is_available': is_available, 'availability_calendar': availability_calendar, 'reservation_settings': reservation_settings }
            return render(request, 'bcse_app/ReservationEdit.html', context)
        elif 'equipment' in form.cleaned_data:
          savedReservation = form.save()
        else:
          savedReservation = form.save()
          savedReservation.equipment.clear()
          savedReservation.save()

        # when teacher makes/edits a reservation, save the mapped consumables on the reservation
        if savedReservation.activity_kit_not_needed:
          savedReservation.consumables.clear()
          savedReservation.save()
        elif request.user.userProfile.user_role in ['T', 'P'] and savedReservation.activity and savedReservation.activity.consumables:
          savedReservation.consumables.clear()
          savedReservation.consumables.add(*savedReservation.activity.consumables.all())
          savedReservation.save()

        if '' != id:
          messages.success(request, "Reservation saved")
          if current_date <= savedReservation.delivery_date:
            if original_status == 'U' and savedReservation.status == 'R':
              reservationConfirmationEmailSend(request, savedReservation.id)
            if original_status in ['U', 'R'] and savedReservation.status == 'N':
              reservationCancellationEmailSend(request, savedReservation.id)

        #new reservations
        else:
          messages.success(request, "Reservation request received")

          reservationWorkplaceUpdate(request, savedReservation.id, savedReservation.user.work_place.id)

          if current_date <= savedReservation.delivery_date:
            if savedReservation.status == 'U':
              reservationReceiptEmailSend(request, savedReservation.id)
            elif savedReservation.status == 'R':
              reservationConfirmationEmailSend(request, savedReservation.id)
            elif savedReservation.status == 'N':
              reservationCancellationEmailSend(request, savedReservation.id)


        return shortcuts.redirect('bcse:reservationView', id=savedReservation.id)

      else:
        if not recaptcha_passed:
          messages.error(request, "reCAPTCHA validation failed")
        else:
          print(form.errors)
          messages.error(request, "Please correct the errors below and click Save again")
        context = {'form': form, 'reservation_settings': reservation_settings}
        return render(request, 'bcse_app/ReservationEdit.html', context)
    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.Reservation.DoesNotExist as e:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, 'Reservation not found')
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % 'Reservation not found')
  except CustomException as ce:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, ce)
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % ce)

####################################
# UPDATE RESERVATION WORKPLACE ASSOCIATION
####################################
def reservationWorkplaceUpdate(request, reservation_id, work_place_id):
  try:

    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to update a reservation')

    reservation = models.Reservation.objects.get(id=reservation_id)
    work_place = models.WorkPlace.objects.get(id=work_place_id)
    user = reservation.user

    if request.user.userProfile.user_role in ['T', 'P'] and request.user.userProfile != user:
      raise CustomException('You do not have the permission to update this reservation')

    try:
      reservation_work_place = models.ReservationWorkPlace.objects.get(reservation=reservation)
      reservation_work_place.work_place = work_place
      reservation_work_place.save()
    except models.ReservationWorkPlace.DoesNotExist as e:
      reservation_work_place = models.ReservationWorkPlace.objects.create(reservation=reservation, work_place=work_place)

    if reservation.status == 'U':
      user.work_place = work_place
      user.save()

  except CustomException as ce:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, ce)
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % ce)


####################################
# UPDATE RESERVATION WORKPLACE ASSOCIATION
####################################
def reservationWorkPlaceEdit(request, id):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to update a reservation')

    reservation = models.Reservation.objects.get(id=id)
    if hasattr(reservation, 'reservation_to_work_place'):
      reservation_to_work_place = reservation.reservation_to_work_place
    else:
      reservation_to_work_place = models.ReservationWorkPlace(reservation=reservation)

    if request.method == 'GET':
      form = forms.ReservationWorkPlaceForm(instance=reservation_to_work_place)
      context = {'form': form, 'reservation_id': id}
      return render(request, 'bcse_app/ReservationWorkPlaceModal.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.ReservationWorkPlaceForm(data, instance=reservation_to_work_place)
      response_data = {}
      if form.is_valid():
        savedWorkplaceAssociation = form.save()
        messages.success(request, "Workplace association has been updated")
        response_data['success'] = True
        context = {'name': savedWorkplaceAssociation.work_place.name, 'delivery_address': savedWorkplaceAssociation.work_place}
        response_data['workplace'] = render_to_string('bcse_app/DeliveryAddress.html', context, request)
      else:
        print(form.errors)
        response_data['success'] = False
        context = {'form': form, 'reservation_id': id}
        response_data['html'] = render_to_string('bcse_app/ReservationWorkPlaceModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, ce)
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % ce)
####################################
# VIEW RESERVATION
####################################
def reservationView(request, id=''):
  """
  reservationView is called from the path 'reservations'
  :param request: request from the browser
  :param id='': id of reservation
  :returns: rendered template 'bcse_app/ReservationView.html'
  :raises models.Reservation.DoesNotExist: redirects user to home page due to reservation id not existing
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous:
      next1 = "?next=/signin"
      next2 = "?next=/reservation/%s/view" % id
      raise CustomException('Please <u><a href="%s%s">login</a></u> to view the reservation'%(next1, next2))

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
    return shortcuts.redirect('bcse:home')
  except CustomException as ce:
    messages.error(request, ce)
    return shortcuts.redirect('bcse:home')


####################################
# CREATE RESERVATION MESSAGE
####################################
def reservationMessage(request, id=''):
  """
  reservationView is called from the path 'reservations'
  :param request: request from the browser
  :param id='': id of reservation
  :returns: newly created reservation message, redirect to JSON view of application or error status of reservation message
  :raises models.Reservation.DoesNotExist: redirects user to home page due to reservation id not existing
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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


def reservationMessageDismiss(request, id=''):
  """
  reservationMessageDismiss is called from the path 'reservations'
  :param request: request from the browser
  :param id='': id of reservation
  :returns: redirects to page user was on before
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role in ['T', 'P']:
      raise CustomException('You do not have the permission to dismiss reservation messages')

    if '' != id:
      reservation = models.Reservation.objects.get(id=id)
      reservation_messages = models.ReservationMessage.objects.all().filter(reservation=reservation)
    else:
      reservation_messages = models.ReservationMessage.objects.all()

    message_count = 0
    for reservation_message in reservation_messages:
      if request.user.userProfile not in reservation_message.viewed_by.all() and request.user.userProfile != reservation_message.created_by:
        reservation_message.viewed_by.add(request.user.userProfile)
        message_count += 1

    if message_count > 0:
      if '' != id:
        messages.success(request, "Messages for reservation id %s dismissed" % id)
      else:
        messages.success(request, "All reservation messages dismissed")
    else:
      messages.warning(request, "No new messages to dismiss")

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.Reservation.DoesNotExist:
    messages.error(request, 'Reservation not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# DELETE RESERVATION
####################################
@login_required
def reservationDelete(request, id=''):
  """
  reservationDelete is called from the path 'reservations'
  :param request: request from the browser
  :param id='': id of reservation
  :returns: redirects to page with remaining reservations
  :raises CustomException: redirects user to page they were on before encountering error due to no permission for viewing reservations
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete reservation')

    if '' != id:
      reservation = models.Reservation.objects.get(id=id)

      #reservations that are checked out or completed cannot be deleted
      if reservation.status in ['O', 'I']:
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

####################################
# CANCEL RESERVATION
####################################
@login_required
def reservationCancel(request, id=''):
  """
  reservationCancel is called from the path 'reservations'
  :param request: request from the browser
  :param id='': id of reservation
  :returns: redirects to page with remaining reservations
  :raises CustomException: redirects user to page they were on before encountering error due to no permission for viewing reservations
  """
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to cancel reservation')

    if '' != id:
      reservation = models.Reservation.objects.get(id=id)

      #non admin/staff users cannot cancel reservations that they do not own
      if request.user.userProfile.user_role not in ['A', 'S'] and reservation.user.user != request.user:
        raise CustomException('You do not have the permission to cancel this reservation')
      #reservations that are checked out or completed cannot be cancelled
      if request.user.userProfile.user_role not in ['A', 'S'] and reservation.status in ['O', 'I']:
        raise CustomException('This reservation is %s and cannot be cancelled' % reservation.get_status_display())

      original_status = reservation.status
      reservation.status = 'N'
      reservation.save()

      current_date = datetime.datetime.now().date()
      if current_date <= reservation.delivery_date and original_status in ['U', 'R']:
        reservationCancellationEmailSend(request, reservation.id)
      messages.success(request, "Reservation cancelled")

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
def reservationsSearch(request, display='table'):
  """
  reservationsSearch is called from the path 'reservations/search'
  :param request: request from the browser
  :returns: list of reservations that match search criteria in the template 'bcse_app/ReservationsTableView.html' or error page
  :raises CustomException: redirects user to page they were on before encountering error due to no permission for viewing reservations
  """
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to view reservations')
    elif request.user.is_authenticated and request.user.userProfile.user_role not in ['A', 'S', 'D']:
      reservations = models.Reservation.objects.all().filter(user__user=request.user)
    else:
      reservations = models.Reservation.objects.all()

    if request.method == 'GET':

      query_filter = Q()
      keyword_filter = None
      user_filter = None
      workplace_filter = None
      activity_filter = None
      consumable_filter = None
      equipment_filter = None
      delivery_after_filter = None
      return_before_filter = None
      status_filter = None
      assignee_filter = None
      color_filter = None
      feedback_status_filter = None

      keywords = request.GET.get('reservation_search-keywords', '')
      user = request.GET.get('reservation_search-user', '')
      work_place = request.GET.get('reservation_search-work_place', '')
      assignee = request.GET.get('reservation_search-assignee', '')
      pickup_assignee = request.GET.get('reservation_search-pickup_assignee', '')
      activity = request.GET.getlist('reservation_search-activity', '')
      consumable = request.GET.getlist('reservation_search-consumable', '')
      equipment = request.GET.getlist('reservation_search-equipment', '')
      delivery_after = request.GET.get('reservation_search-delivery_after', '')
      return_before = request.GET.get('reservation_search-return_before', '')
      status = request.GET.getlist('reservation_search-status', '')
      color = request.GET.getlist('reservation_search-color', '')

      sort_by = request.GET.get('reservation_search-sort_by', '')
      columns = request.GET.getlist('reservation_search-columns', '')
      rows_per_page = request.GET.get('reservation_search-rows_per_page', settings.DEFAULT_ITEMS_PER_PAGE)
      feedback_status = request.GET.get('reservation_search-feedback_status', '')
      page = request.GET.get('page', '')

      if display == 'table':
        #set session variable
        request.session['reservations_search'] = {
          'keywords': keywords,
          'user': user,
          'work_place': work_place,
          'assignee': assignee,
          'pickup_assignee': pickup_assignee,
          'activity': activity,
          'consumable': consumable,
          'equipment': equipment,
          'delivery_after': delivery_after,
          'return_before': return_before,
          'status': status,
          'color': color,
          'sort_by': sort_by,
          'columns': columns,
          'rows_per_page': rows_per_page,
          'feedback_status': feedback_status,
          'page': page
        }
      else:
        current_view = start_date = ''
        if 'reservations_search_calendar' in request.session:
          if 'current_view' in request.session['reservations_search_calendar']:
            current_view = request.session['reservations_search_calendar']['current_view']

          if 'start_date' in request.session['reservations_search_calendar']:
            start_date = request.session['reservations_search_calendar']['start_date']

        #set session variable
        request.session['reservations_search_calendar'] = {
          'keywords': keywords,
          'user': user,
          'work_place': work_place,
          'assignee': assignee,
          'pickup_assignee': pickup_assignee,
          'activity': activity,
          'consumable': consumable,
          'equipment': equipment,
          'delivery_after': delivery_after,
          'return_before': return_before,
          'status': status,
          'color': color,
          'current_view': current_view,
          'start_date': start_date
        }

      if keywords:
        keyword_filter = Q(activity__name__icontains=keywords) | Q(other_activity_name__icontains=keywords)
        keyword_filter = keyword_filter | Q(user__user__first_name__icontains=keywords)
        keyword_filter = keyword_filter | Q(user__user__last_name__icontains=keywords)
        keyword_filter = keyword_filter | Q(notes__icontains=keywords)
        if request.user.is_authenticated and request.user.userProfile.user_role in ['A', 'S']:
          keyword_filter = keyword_filter | Q(admin_notes__icontains=keywords)

      if user:
        user_filter = Q(user=user)

      if work_place:
        workplace_filter = Q(reservation_to_work_place__work_place=work_place)

      if display == 'table':
        if assignee and pickup_assignee:
          assignee_filter = Q(assignee=assignee) & Q(pickup_assignee=pickup_assignee)
        elif assignee:
          assignee_filter = Q(assignee=assignee)
        elif pickup_assignee:
          assignee_filter = Q(pickup_assignee=pickup_assignee)
      else:
        if assignee and pickup_assignee:
          assignee_filter = Q(assignee=assignee) | Q(pickup_assignee=pickup_assignee)
        elif assignee:
          assignee_filter = Q(assignee=assignee)
        elif pickup_assignee:
          assignee_filter = Q(pickup_assignee=pickup_assignee)

      if activity:
        activity_filter = Q(activity__in=activity)

      if consumable:
        consumable_filter = Q(consumables__in=consumable)

      if status:
        status_filter = Q(status__in=status)

      if delivery_after:
        delivery_after = datetime.datetime.strptime(delivery_after, '%B %d, %Y')
        delivery_after_filter = Q(delivery_date__gte=delivery_after)

      if return_before:
        return_before = datetime.datetime.strptime(return_before, '%B %d, %Y')
        return_before_filter = Q(delivery_date__lte=return_before)
        return_before_filter = return_before_filter & Q(Q(return_date__lte=return_before) | Q(return_date__isnull=True))

      if color:
        color_filter = Q(color__id__in=color)

      if feedback_status:
        feedback_status_filter = Q(feedback_status=feedback_status)

      if equipment:
        equipment_filter = Q(equipment__equipment_type__id__in=equipment)


      if keyword_filter:
        query_filter = keyword_filter

      if user_filter:
        query_filter = query_filter & user_filter
      if workplace_filter:
        query_filter = query_filter & workplace_filter

      if assignee_filter:
        query_filter = query_filter & assignee_filter

      if activity_filter:
        query_filter = query_filter & activity_filter
      if consumable_filter:
        query_filter = query_filter & consumable_filter
      if equipment_filter:
        query_filter = query_filter & equipment_filter

      if status_filter:
        query_filter = query_filter & status_filter
      if delivery_after_filter:
        query_filter = query_filter & delivery_after_filter
      if return_before_filter:
        query_filter = query_filter & return_before_filter

      if color_filter:
        query_filter = query_filter & color_filter

      if feedback_status_filter:
        query_filter = query_filter & feedback_status_filter

      if equipment_filter:
        query_filter = query_filter & equipment_filter


      reservations = reservations.filter(query_filter)

      reservations = reservations.distinct()

      if display == 'table':
        reservations = reservations.annotate(new_messages=Count('reservation_messages', filter=Q(~Q(reservation_messages__created_by=request.user.userProfile) & ~Q(reservation_messages__viewed_by=request.user.userProfile))))
        reservations = reservations.annotate(primary_date=Case(When(status='O', then=('return_date')), When(status__in=['N', 'I', 'R', 'U'], then=('delivery_date'))))
        reservations = reservations.annotate(secondary_date=Case(When(status='O', then=('delivery_date')), When(status__in=['N', 'I', 'R', 'U'], then=('return_date'))))

        direction = request.GET.get('direction') or 'asc'
        ignorecase = request.GET.get('ignorecase') or 'false'

        sort_order = []
        if sort_by:
          if sort_by == 'user':
            sort_order.append({'order_by': 'user__user__last_name', 'direction': 'asc', 'ignorecase': 'true'})
            sort_order.append({'order_by': 'user__user__first_name', 'direction': 'asc', 'ignorecase': 'true'})
          elif sort_by == 'activity':
            sort_order.append({'order_by': 'activity__name', 'direction': 'asc', 'ignorecase': 'true'})
            sort_order.append({'order_by': 'other_activity_name', 'direction': 'asc', 'ignorecase': 'true'})

          elif sort_by == 'delivery_date_asc':
            sort_order.append({'order_by': 'delivery_date', 'direction': 'asc', 'ignorecase': 'false'})
            sort_order.append({'order_by': 'return_date', 'direction': 'asc', 'ignorecase': 'false'})
          elif sort_by == 'delivery_date_desc':
            sort_order.append({'order_by': 'delivery_date', 'direction': 'desc', 'ignorecase': 'false'})
            sort_order.append({'order_by': 'return_date', 'direction': 'desc', 'ignorecase': 'false'})
          elif sort_by == 'return_date_asc':
            sort_order.append({'order_by': 'return_date', 'direction': 'asc', 'ignorecase': 'false'})
          elif sort_by == 'return_date_desc':
            sort_order.append({'order_by': 'return_date', 'direction': 'desc', 'ignorecase': 'false'})

          elif sort_by == 'created_date_asc':
            sort_order.append({'order_by': 'created_date', 'direction': 'asc', 'ignorecase': 'false'})
          elif sort_by == 'created_date_desc':
            sort_order.append({'order_by': 'created_date', 'direction': 'desc', 'ignorecase': 'false'})

          elif sort_by == 'status':
            sort_order.append({'order_by': 'status', 'direction': 'asc', 'ignorecase': 'true'})
          elif sort_by == 'new_messages':
            sort_order.append({'order_by': 'new_messages', 'direction': 'desc', 'ignorecase': 'false'})
        else:
          sort_order.append({'order_by': 'primary_date', 'direction': 'desc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'secondary_date', 'direction': 'desc', 'ignorecase': 'false'})

        reservations = paginate(request, reservations, sort_order, rows_per_page, page)

        context = {'reservations': reservations, 'tag': 'reservations', 'columns': columns}
        response_data = {}
        response_data['success'] = True
        response_data['html'] = render_to_string('bcse_app/ReservationsTableView.html', context, request)
      else:
        reservations = reservations.order_by('delivery_date')
        reservation_schedule_matrix = []
        for reservation in reservations:
          schedule = {}
          if hasattr(reservation, 'reservation_to_work_place'):
            schedule['title'] = '%s - %s' % (reservation.reservation_to_work_place.work_place.name, reservation.user.user.get_full_name())
          else:
            schedule['title'] = '%s - %s' % ('No Workplace', reservation.user.user.get_full_name())
          schedule['start'] = reservation.delivery_date.strftime('%Y-%m-%d')
          schedule['url'] = '/reservation/%s/view'%reservation.id
          schedule['display'] = 'block'
          schedule['allDay'] = 'true'
          schedule['textColor'] = 'black'
          schedule['delivery_assignee'] = reservation.assignee.initials if reservation.assignee else ''
          schedule['pickup_assignee'] = reservation.pickup_assignee.initials if reservation.pickup_assignee else ''
          if reservation.color:
            schedule['color'] = reservation.color.color
          else:
            schedule['color'] = '#cccccc' #default mid gray


          if reservation.return_date:
            return_date = reservation.return_date + datetime.timedelta(days=1)
            schedule['end'] = return_date.strftime('%Y-%m-%d')
          else:
            schedule['dropoff_only'] = True

          reservation_schedule_matrix.append(schedule)

        context = {'events': json.dumps(reservation_schedule_matrix)}

        if request.session.get('reservations_search_calendar', False):
          context['start_date'] = request.session['reservations_search_calendar']['start_date']
          context['current_view'] = request.session['reservations_search_calendar']['current_view']

        response_data = {}
        response_data['success'] = True
        response_data['html'] = render_to_string('bcse_app/ReservationsCalendarView.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# GET EQUIPMENT AVAILABILITY
####################################
def getAvailabilityData(request, id=''):
  data = request.POST.copy()

  delivery_date = datetime.datetime.strptime(request.POST.get('delivery_date'), '%B %d, %Y').date()
  return_date = datetime.datetime.strptime(request.POST.get('return_date'), '%B %d, %Y').date()

  start_date = delivery_date.replace(day=1)
  end_date = return_date.replace(day=calendar.monthrange(return_date.year, return_date.month)[1])
  equipment_availability_matrix = None
  calender_type = None
  is_available = False

  if request.POST.getlist('equipment_types'):
    equipment_types = models.EquipmentType.objects.all().filter(id__in=request.POST.getlist('equipment_types', ''))
    equipment_availability_matrix = checkAvailability(request, id, equipment_types, start_date, end_date, delivery_date, return_date)
    is_available = all([equipment_type['is_available'] for equipment_type in equipment_availability_matrix.values()])
    calender_type = 'ET'

  elif request.POST.getlist('equipment'):
    equipment_sets = models.Equipment.objects.all().filter(id__in=request.POST.getlist('equipment', ''))
    equipment_availability_matrix = checkEquipmentSetAvailability(request, id, equipment_sets, delivery_date, return_date)
    is_available = all([equipment_set['is_available'] for equipment_set in equipment_availability_matrix.values()])
    calender_type = 'ES'

  availability_calendar = []
  index_date = start_date
  while index_date <= end_date:
    if calender_type == 'ET':
      cal = Calendar(index_date.year, index_date.month)
    else:
      cal = CalendarEquipmentSet(index_date.year, index_date.month)
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

########################################################################
# CHECK EQUIPMENT AVAILABILITY FOR SELECTED EQUIPMENT TYPES
########################################################################
def checkAvailability(request, current_reservation_id, equipment_types, start_date, end_date, delivery_date, return_date):
  equipment_availability_matrix = {}
  delta = return_date - delivery_date
  reservation_days = delta.days + 1

  oneday = datetime.timedelta(days=1)

  #iterate each equipment category selected
  for equipment_type in equipment_types:
    equipment_availability_matrix[equipment_type] = {}
    equipment_availability_matrix[equipment_type]['most_available_equip'] = None
    equipment_availability_matrix[equipment_type]['most_available_days'] = None
    equipment_availability_matrix[equipment_type]['availability_dates'] = {}
    equipment_availability_matrix[equipment_type]['is_available'] = False

    #get all active equipment of the equipment category
    equipment = models.Equipment.objects.all().filter(equipment_type__id=equipment_type.id, status='A')
    #check if each copy of the equipment category is available on the selected dates
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


########################################################################
# CHECK EQUIPMENT AVAILABILITY FOR SELECTED EQUIPMENT SETS
########################################################################
def checkEquipmentSetAvailability(request, current_reservation_id, equipment_sets, delivery_date, return_date):
  equipment_availability_matrix = {}
  delta = return_date - delivery_date
  reservation_days = delta.days + 1

  oneday = datetime.timedelta(days=1)

  #iterate each equipment set selected
  for equipment in equipment_sets:
    equipment_availability_matrix[equipment] = {}
    equipment_availability_matrix[equipment]['availability_dates'] = {}

    index_date = delivery_date

    while index_date <= return_date:
      reservations = models.Reservation.objects.all().filter(equipment=equipment, delivery_date__lte=index_date, return_date__gte=index_date).exclude(status='N')
      if current_reservation_id != '':
        reservations = reservations.exclude(id=current_reservation_id)
      reservation_count = reservations.count()
      if reservation_count > 0:
        locations = reservations.values_list('reservation_to_work_place__work_place__name', flat=True)
        equipment_availability_matrix[equipment]['availability_dates'][index_date] = {'available': False, 'locations': locations}
      else:
        equipment_availability_matrix[equipment]['availability_dates'][index_date] = {'available': True}

      index_date += oneday

    equipment_availability_matrix[equipment]['is_available'] = all(availability['available'] for idx_date, availability in equipment_availability_matrix[equipment]['availability_dates'].items())

  return equipment_availability_matrix


####################################
# GET EQUIPMENT AVAILABILITY
####################################
def adminAvailabilityCalendar(request):
  """
  adminAvailabilityCalendar is called from the path 'adminConfiguration'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/AdminAvailabilityCalender.html', availability_data, or error page
  :raises CustomException: redirects user to page they were on before encountering error due to no permission to view availability calender
  """
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to view availability calendar')
    elif request.user.is_authenticated and request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view availability calendar')

    if request.method == 'GET':
      equipment_types = models.EquipmentType.objects.all().filter(id__in=request.GET.getlist('equipment_types', ''))

      if equipment_types:
        selected_month = datetime.datetime.strptime(request.GET.get('selected_month'), '%B %Y').date()
        start_date = selected_month.replace(day=1)
        equipment_availability_matrix = checkAvailabilityForAdmin(request, equipment_types, start_date)

        availability_calendar = []
        cal = AdminCalendar(start_date.year, start_date.month)
        cal.setfirstweekday(6)
        availability_calendar.append(cal.formatmonth(withyear=True, availability_matrix=equipment_availability_matrix))

        if request.is_ajax():
          response_data = {}
          response_data['success'] = True
          context = {'availability_calendar': availability_calendar}
          response_data['html'] = render_to_string('bcse_app/AdminAvailabilityCalendarView.html', context, request)
          return http.HttpResponse(json.dumps(response_data), content_type="application/json")
        else:
          availability_data = {'equipment_availability_matrix': equipment_availability_matrix,
                             'availability_calendar': availability_calendar}
        return availability_data
      else:
        searchForm = forms.EquipmentAvailabilityForm()
        context = {'searchForm': searchForm}
        return render(request, 'bcse_app/AdminAvailabilityCalendar.html', context)
    return http.HttpResponseNotAllowed(['GET'])
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# CHECK EQUIPMENT AVAILABILITY
####################################

def checkAvailabilityForAdmin(request, equipment_types, selected_month):
  equipment_availability_matrix = {}

  oneday = datetime.timedelta(days=1)
  start_date = selected_month.replace(day=1)
  end_date = selected_month.replace(day=calendar.monthrange(selected_month.year, selected_month.month)[1])

  #iterate each equipment category selected
  for equipment_type in equipment_types:
    equipment_availability_matrix[equipment_type] = {}

    #get all active equipment of the equipment category
    equipment = models.Equipment.objects.all().filter(equipment_type__id=equipment_type.id, status='A').order_by('name')

    index_date = start_date
    while index_date <= end_date:
      equipment_availability_matrix[equipment_type][index_date] = {}
      #check if each copy of the equipment category is available on the selected dates
      for equip in equipment:
        reservations = models.Reservation.objects.all().filter(equipment=equip, delivery_date__lte=index_date, return_date__gte=index_date).exclude(status='N')
        reservation_count = reservations.count()
        if reservation_count > 0:
          locations = reservations.values_list('reservation_to_work_place__work_place__name', flat=True)
          equipment_availability_matrix[equipment_type][index_date][equip] = {'available': False, 'locations': locations}
        else:
          equipment_availability_matrix[equipment_type][index_date][equip] = {'available': True}

      index_date += oneday


  return equipment_availability_matrix

####################################
# RESERVATION SCHEDULE
####################################

def adminReservationCalendar(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S', 'D']:
      raise CustomException('You do not have the permission to view reservation calendar')

    if request.session.get('reservations_search_calendar', False):
      searchForm = forms.ReservationsSearchForm(user=request.user, initials=request.session['reservations_search_calendar'], prefix="reservation_search")
    else:
      searchForm = forms.ReservationsSearchForm(user=request.user, initials=None, prefix="reservation_search")

    context = {'searchForm': searchForm}

    if request.user.userProfile.user_role in ['A', 'S']:
      return render(request, 'bcse_app/AdminReservationCalendar.html', context)
    else:
      return render(request, 'bcse_app/ReservationCalendar.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


#############################################################################
# UPDATE THE SESSION VARIABLE WITH THE DATE AND VIEW OF THE RESERVATION CALENDAR
#############################################################################
def adminReservationCalendarUpdate(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S', 'D']:
      raise CustomException('You do not have the permission to update reservation calendar')

    if request.method == 'POST':
      if request.session.get('reservations_search_calendar', False):
        reservations_search_calendar_vars = request.session['reservations_search_calendar']
        reservations_search_calendar_vars['start_date'] = request.POST.get('start_date')
        reservations_search_calendar_vars['current_view'] = request.POST.get('current_view')
        request.session['reservations_search_calendar'] = reservations_search_calendar_vars
        response_data = {'success': True}
      else:
        print('session var does not exist')
        response_data = {'success': False}

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

###################################################
# UPDATE ASSIGNED RESERVATION COLOR AND STATUS
###################################################
@login_required
def reservationUpdate(request, reservation_id):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S', 'D']:
      raise CustomException('You do not have the permission to update reservation')

    reservation = models.Reservation.objects.get(id=reservation_id)
    current_date = datetime.datetime.now().date()
    original_status = reservation.status

    if request.method == 'GET':
      form = forms.ReservationUpdateForm(instance=reservation)
      context = {'form': form, 'reservation_id': reservation_id}
      return render(request, 'bcse_app/ReservationUpdateModal.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.ReservationUpdateForm(data, instance=reservation)
      response_data = {}
      if form.is_valid():
        savedReservation = form.save()
        response_data['success'] = True
        messages.success(request, 'Reservation %s updated' % reservation_id)
        if current_date <= savedReservation.delivery_date:
          if original_status == 'U' and savedReservation.status == 'R':
            reservationConfirmationEmailSend(request, reservation_id)
          if original_status in ['U', 'R'] and savedReservation.status == 'N':
            reservationCancellationEmailSend(request, savedReservation.id)
      else:
        print(form.errors)
        response_data['success'] = False
        context = {'form': form, 'reservation_id': reservation_id}
        response_data['html'] = render_to_string('bcse_app/ReservationUpdateModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except models.Reservation.DoesNotExist as e:
    messages.error(request, 'Reservation does not exists')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# UPDATE RESERVATION DELIVERY ADDRESS
####################################
@login_required
def reservationDeliveryAddressEdit(request, reservation_id):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to update delivery address')

    reservation = models.Reservation.objects.get(id=reservation_id)
    if hasattr(reservation, 'delivery_address') and reservation.delivery_address:
      delivery_address = models.ReservationDeliveryAddress.objects.get(reservation=reservation)
    else:
      delivery_address = models.ReservationDeliveryAddress(reservation=reservation)

    if request.method == 'GET':
      form = forms.ReservationDeliveryAddressForm(instance=delivery_address)
      context = {'form': form, 'reservation_id': reservation_id}
      return render(request, 'bcse_app/ReservationDeliveryAddressModal.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.ReservationDeliveryAddressForm(data, instance=delivery_address)
      response_data = {}
      if form.is_valid():
        savedDeliveryAddress = form.save()
        response_data['success'] = True
        context = {'delivery_address': savedDeliveryAddress, 'warning': True}
        response_data['address'] = render_to_string('bcse_app/DeliveryAddress.html', context, request)
      else:
        print(form.errors)
        response_data['success'] = False
        context = {'form': form, 'reservation_id': reservation_id}
        response_data['html'] = render_to_string('bcse_app/ReservationDeliveryAddressModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.Reservation.DoesNotExist as e:
    messages.error(request, 'Reservation does not exists')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# DELETE RESERVATION DELIVERY ADDRESS
####################################
@login_required
def reservationDeliveryAddressDelete(request, reservation_id):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete delivery address')

    reservation = models.Reservation.objects.get(id=reservation_id)
    delivery_address = models.ReservationDeliveryAddress.objects.get(reservation=reservation)
    delivery_address.delete()

    messages.success(request, 'Reservation delivery address deleted')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.Reservation.DoesNotExist as e:
    messages.error(request, 'Reservation does not exists')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# GENERATE BAXTER BOX USAGE REPORT
####################################
@login_required
def baxterBoxUsageReport(request):
  """
  baxterBoxUsageReport is called from the path 'adminConfiguration'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/BaxterBoxUsageReport.html' with view of baxter box report, or error page
  :raises CustomException: redirects user to page they were on before encountering error due to no permission to view baxter box report
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view Baxter Box Report')

    if request.method == 'GET':
      if request.session.get('baxter_box_usage_search', False):
        searchForm = forms.BaxterBoxUsageSearchForm(user=request.user, initials=request.session['baxter_box_usage_search'], prefix="usage")
      else:
        searchForm = forms.BaxterBoxUsageSearchForm(user=request.user, initials=None, prefix="usage")

      context = {'searchForm': searchForm}
      return render(request, 'bcse_app/BaxterBoxUsageReport.html', context)

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################
# BAXTER BOX USAGE SEARCH
####################################
@login_required
def baxterBoxUsageReportSearch(request):
  """
  baxterBoxUsageReportSearch is called from the path 'adminConfiguration'
  :param request: request from the browser
  :returns: JSON view of baxter box usage report search or error page
  :raises CustomException: redirects user to page they were on before encountering error due to no permission to view baxter box report
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view Baxter Box Report')

    if request.method == 'GET':
      reservations = models.Reservation.objects.all().exclude(status='N')
      equipment_types = models.EquipmentType.objects.all().order_by('order')
      activities = models.Activity.objects.all().order_by('name')
      consumables = models.Consumable.objects.all().order_by('name')
      workplaces = models.WorkPlace.objects.all().order_by('name')
      users = models.UserProfile.objects.all()

      equipment_usage = {}
      kit_usage = {}
      consumable_usage = {}
      workplace_usage = {}
      user_usage = {}
      total_usage = {'reservations': 0, 'total_equipment_cost': 0.0, 'kits': 0, 'total_kit_cost': 0.0, 'consumables': 0, 'total_consumables_cost': 0.0, 'teachers': [], 'teacher_count': 0, 'workplaces': [], 'workplace_count': 0, 'classes': 0, 'students': 0}

      for equipment_type in equipment_types:
        equipment_usage[equipment_type.id] = {'name': equipment_type.name, 'unit_cost': equipment_type.unit_cost,'reservations': 0, 'total_cost': 0.0, 'teachers': [], 'teacher_count': 0, 'workplaces': [], 'workplace_count': 0, 'classes': 0, 'students': 0}
      for activity in activities:
        kit_usage[activity.id] = {'name': activity.kit_name, 'unit_cost': activity.kit_unit_cost, 'reservations': 0, 'count': 0, 'total_cost': 0.0, 'teachers': [], 'teacher_count': 0, 'workplaces': [], 'workplace_count': 0, 'classes': 0, 'students': 0}
      for consumable in consumables:
        consumable_usage[consumable.id] = {'name': consumable.name, 'unit_cost': consumable.unit_cost, 'reservations': 0, 'count': 0, 'total_cost': 0.0, 'teachers': [], 'teacher_count': 0, 'workplaces': [], 'workplace_count': 0, 'classes': 0, 'students': 0}
      for workplace in workplaces:
        workplace_usage[workplace.id] = {'name': workplace.name, 'reservations': 0, 'equipment': 0, 'total_equipment_cost': 0.0,  'kits': 0, 'total_kit_cost': 0.0, 'consumables': 0, 'total_consumables_cost': 0.0, 'total_cost': 0.0, 'teachers': [], 'teacher_count': 0, 'classes': 0, 'students': 0}
      for user in users:
        user_usage[user.id] = {'name': '%s, %s' % (user.user.last_name, user.user.first_name), 'email': user.user.email, 'secondary_email': user.secondary_email, 'current_workplace': user.work_place.name, 'associated_workplaces': [], 'reservations': 0, 'equipment': 0, 'total_equipment_cost': 0.0,  'kits': 0, 'total_kit_cost': 0.0, 'consumables': 0, 'total_consumables_cost': 0.0, 'total_cost': 0.0, 'classes': 0, 'students': 0}


      query_filter = Q()
      filter_selected = False

      from_date = request.GET.get('usage-from_date', '')
      to_date = request.GET.get('usage-to_date', '')
      work_place = request.GET.getlist('usage-work_place', '')
      user = request.GET.getlist('usage-user', '')
      activity = request.GET.getlist('usage-activity', '')
      consumable = request.GET.getlist('usage-consumable', '')
      equipment = request.GET.getlist('usage-equipment', '')
      status = request.GET.getlist('usage-status', '')
      sort_by = request.GET.get('usage-sort_by', '')
      rows_per_page = request.GET.get('usage-rows_per_page', settings.DEFAULT_ITEMS_PER_PAGE)
      page = request.GET.get('page', '')

       #set session variable
      request.session['baxter_box_usage_search'] = baxter_box_usage_search_vars = {
        'from_date': from_date,
        'to_date': to_date,
        'work_place': work_place,
        'user': user,
        'activity': activity,
        'consumable': consumable,
        'equipment': equipment,
        'status': status,
        'sort_by': sort_by,
        'rows_per_page': rows_per_page,
        'page': page
      }

      tags = []
      for tag in models.Tag.objects.all().filter(status='A'):
        sub_tags = request.GET.getlist('usage-tag_%s'%tag.id, '')
        if sub_tags:
          baxter_box_usage_search_vars['tag_'+str(tag.id)] = sub_tags
          tags.append(sub_tags)


      if from_date:
        from_date = datetime.datetime.strptime(from_date, '%B %d, %Y')
        query_filter = query_filter & Q(delivery_date__gte=from_date)
        filter_selected = True

      if to_date:
        to_date = datetime.datetime.strptime(to_date, '%B %d, %Y')
        query_filter = query_filter & Q(delivery_date__lte=to_date)
        query_filter = query_filter & Q(Q(return_date__lte=to_date) | Q(return_date__isnull=True))
        filter_selected = True

      if work_place:
        query_filter = query_filter & Q(reservation_to_work_place__work_place__in=work_place)
        filter_selected = True

      if user:
        query_filter = query_filter & Q(user__in=user)
        filter_selected = True

      if activity:
        query_filter = query_filter & Q(activity__in=activity)
        filter_selected = True

      if consumable:
        query_filter = query_filter & Q(consumables__in=consumable)
        filter_selected = True

      if status:
        query_filter = query_filter & Q(status__in=status)
        filter_selected = True

      if equipment:
        query_filter = query_filter & Q(equipment__equipment_type__id__in=equipment)
        filter_selected = True

      if tags:
        tags_filter = Q()
        for sub_tags in tags:
          tags_filter = tags_filter & Q(Q(equipment__equipment_type__tags__id__in=sub_tags) | Q(activity__tags__id__in=sub_tags))

        query_filter = query_filter & tags_filter

        filter_selected = True

      reservations = reservations.filter(query_filter).distinct()

      for reservation in reservations:
        reservation_user = reservation.user
        reservation_work_place = reservation.reservation_to_work_place.work_place

        if reservation.more_num_of_classes:
          reservation_classes = int(reservation.more_num_of_classes)
        elif reservation.num_of_classes:
          reservation_classes = int(reservation.num_of_classes)
        else:
          reservation_classes = 0

        if reservation.num_of_students:
          reservation_students = int(reservation.num_of_students)
        else:
          reservation_students = 0


        workplace_usage[reservation_work_place.id]['reservations'] += 1
        workplace_usage[reservation_work_place.id]['classes'] += reservation_classes
        workplace_usage[reservation_work_place.id]['students'] += reservation_students

        user_usage[reservation_user.id]['reservations'] += 1
        user_usage[reservation_user.id]['classes'] += reservation_classes
        user_usage[reservation_user.id]['students'] += reservation_students
        if reservation_work_place not in user_usage[reservation_user.id]['associated_workplaces']:
          user_usage[reservation_user.id]['associated_workplaces'].append(reservation_work_place)

        if reservation_user not in workplace_usage[reservation_work_place.id]['teachers']:
          workplace_usage[reservation_work_place.id]['teachers'].append(reservation_user)
          workplace_usage[reservation_work_place.id]['teacher_count'] += 1

        if reservation.equipment:
          for equipment in reservation.equipment.all():
            equipment_usage[equipment.equipment_type.id]['reservations'] += 1
            if reservation_user not in equipment_usage[equipment.equipment_type.id]['teachers']:
              equipment_usage[equipment.equipment_type.id]['teachers'].append(reservation_user)
              equipment_usage[equipment.equipment_type.id]['teacher_count'] += 1

            if reservation_work_place not in equipment_usage[equipment.equipment_type.id]['workplaces']:
              equipment_usage[equipment.equipment_type.id]['workplaces'].append(reservation_work_place)
              equipment_usage[equipment.equipment_type.id]['workplace_count'] += 1

            equipment_usage[equipment.equipment_type.id]['classes'] += reservation_classes
            equipment_usage[equipment.equipment_type.id]['students'] += reservation_students
            workplace_usage[reservation_work_place.id]['equipment'] += 1
            user_usage[reservation_user.id]['equipment'] += 1

            if equipment.equipment_type.unit_cost:
              equipment_usage[equipment.equipment_type.id]['total_cost'] += equipment.equipment_type.unit_cost
              total_usage['total_equipment_cost'] += equipment.equipment_type.unit_cost
              workplace_usage[reservation_work_place.id]['total_equipment_cost'] += equipment.equipment_type.unit_cost
              user_usage[reservation_user.id]['total_equipment_cost'] += equipment.equipment_type.unit_cost

        if reservation.activity:
          if not reservation.activity_kit_not_needed:
            kit_usage[reservation.activity.id]['reservations'] += 1
            kit_usage[reservation.activity.id]['count'] += reservation_classes
            total_usage['kits'] += reservation_classes
            workplace_usage[reservation_work_place.id]['kits'] += reservation_classes
            user_usage[reservation_user.id]['kits'] += reservation_classes

            if reservation.activity.kit_unit_cost:
              kit_usage[reservation.activity.id]['total_cost'] += reservation.activity.kit_unit_cost * reservation_classes
              total_usage['total_kit_cost'] += reservation.activity.kit_unit_cost * reservation_classes
              workplace_usage[reservation_work_place.id]['total_kit_cost'] += reservation.activity.kit_unit_cost * reservation_classes
              user_usage[reservation_user.id]['total_kit_cost'] += reservation.activity.kit_unit_cost * reservation_classes

            for reservation_consumable in reservation.consumables.all():
              consumable_usage[reservation_consumable.id]['reservations'] += 1
              consumable_usage[reservation_consumable.id]['count'] += reservation_classes
              consumable_usage[reservation_consumable.id]['classes'] += reservation_classes
              consumable_usage[reservation_consumable.id]['students'] += reservation_students
              workplace_usage[reservation_work_place.id]['consumables'] += reservation_classes
              user_usage[reservation_user.id]['consumables'] += reservation_classes

              if reservation_user not in consumable_usage[reservation_consumable.id]['teachers']:
                consumable_usage[reservation_consumable.id]['teachers'].append(reservation_user)
                consumable_usage[reservation_consumable.id]['teacher_count'] += 1


              if reservation_work_place not in consumable_usage[reservation_consumable.id]['workplaces']:
                consumable_usage[reservation_consumable.id]['workplaces'].append(reservation_work_place)
                consumable_usage[reservation_consumable.id]['workplace_count'] += 1

              total_usage['consumables'] += reservation_classes
              if reservation_consumable.unit_cost:
                consumable_usage[reservation_consumable.id]['total_cost'] += reservation_consumable.unit_cost * reservation_classes
                total_usage['total_consumables_cost'] += reservation_consumable.unit_cost * reservation_classes
                workplace_usage[reservation_work_place.id]['total_consumables_cost'] += reservation_consumable.unit_cost * reservation_classes
                user_usage[reservation_user.id]['total_consumables_cost'] += reservation_consumable.unit_cost * reservation_classes


          kit_usage[reservation.activity.id]['classes'] += reservation_classes
          kit_usage[reservation.activity.id]['students'] += reservation_students

          if reservation_user not in kit_usage[reservation.activity.id]['teachers']:
            kit_usage[reservation.activity.id]['teachers'].append(reservation_user)
            kit_usage[reservation.activity.id]['teacher_count'] += 1
          if reservation_work_place not in kit_usage[reservation.activity.id]['workplaces']:
            kit_usage[reservation.activity.id]['workplaces'].append(reservation_work_place)
            kit_usage[reservation.activity.id]['workplace_count'] += 1


        if reservation.user not in total_usage['teachers']:
          total_usage['teachers'].append(reservation_user)
          total_usage['teacher_count'] += 1
        if reservation_work_place not in total_usage['workplaces']:
          total_usage['workplaces'].append(reservation_work_place)
          total_usage['workplace_count'] += 1

        total_usage['reservations'] += 1
        total_usage['classes'] += reservation_classes
        total_usage['students'] += reservation_students


      if filter_selected:
        remove_equipment = []
        remove_kit = []
        remove_consumable = []
        remove_workplaces = []
        remove_users = []

        for workplace_id, usage in workplace_usage.items():
          if usage['reservations'] == 0 and usage['teacher_count'] == 0 and usage['classes'] == 0 and usage['students'] == 0:
            remove_workplaces.append(workplace_id)

        for equipment_type_id, usage in equipment_usage.items():
          if usage['reservations'] == 0 and usage['teacher_count'] == 0 and usage['workplace_count'] == 0 and usage['classes'] == 0 and usage['students'] == 0:
           remove_equipment.append(equipment_type_id)

        for activity_id, usage in kit_usage.items():
          if usage['count'] == 0 and usage['teacher_count'] == 0 and usage['workplace_count'] == 0  and usage['classes'] == 0 and usage['students'] == 0:
            remove_kit.append(activity_id)

        for consumable_id, usage in consumable_usage.items():
          if usage['count'] == 0 and usage['teacher_count'] == 0 and usage['workplace_count'] == 0 and usage['classes'] == 0 and usage['students'] == 0:
            remove_consumable.append(consumable_id)

        for user_id, usage in user_usage.items():
          if usage['reservations'] == 0 and usage['classes'] == 0 and usage['students'] == 0:
            remove_users.append(user_id)

        for workplace_id in remove_workplaces:
          del workplace_usage[workplace_id]

        for equipment_type_id in remove_equipment:
          del equipment_usage[equipment_type_id]

        for activity_id in remove_kit:
          del kit_usage[activity_id]

        for consumable_id in remove_consumable:
          del consumable_usage[consumable_id]

        for user_id in remove_users:
          del user_usage[user_id]

      for workplace_id, usage in workplace_usage.items():
        workplace_usage[workplace_id]['total_cost'] = workplace_usage[workplace_id]['total_equipment_cost']  + workplace_usage[workplace_id]['total_kit_cost'] + workplace_usage[workplace_id]['total_consumables_cost']

      for user_id, usage in user_usage.items():
        user_usage[user_id]['total_cost'] = user_usage[user_id]['total_equipment_cost']  + user_usage[user_id]['total_kit_cost'] + user_usage[user_id]['total_consumables_cost']

      equipment_sort_order = []
      kit_sort_order = []
      consumable_sort_order = []
      workplace_sort_order = []
      user_sort_order = []

      if sort_by == 'name':
        equipment_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
        kit_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
        consumable_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
        workplace_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
        user_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
      elif sort_by == 'reservations':
        equipment_sort_order.append({'order_by': 'reservations', 'direction': 'desc', 'ignorecase': 'false'})
        kit_sort_order.append({'order_by': 'reservations', 'direction': 'desc', 'ignorecase': 'false'})
        consumable_sort_order.append({'order_by': 'reservations', 'direction': 'desc', 'ignorecase': 'false'})
        workplace_sort_order.append({'order_by': 'reservations', 'direction': 'desc', 'ignorecase': 'false'})
        user_sort_order.append({'order_by': 'reservations', 'direction': 'desc', 'ignorecase': 'false'})
      elif sort_by == 'kits':
        equipment_sort_order.append({'order_by': 'reservations', 'direction': 'desc', 'ignorecase': 'false'})
        kit_sort_order.append({'order_by': 'count', 'direction': 'desc', 'ignorecase': 'false'})
        consumable_sort_order.append({'order_by': 'count', 'direction': 'desc', 'ignorecase': 'false'})
        workplace_sort_order.append({'order_by': 'kits', 'direction': 'desc', 'ignorecase': 'false'})
        user_sort_order.append({'order_by': 'kits', 'direction': 'desc', 'ignorecase': 'false'})
      elif sort_by == 'consumables':
        equipment_sort_order.append({'order_by': 'reservations', 'direction': 'desc', 'ignorecase': 'false'})
        kit_sort_order.append({'order_by': 'count', 'direction': 'desc', 'ignorecase': 'false'})
        consumable_sort_order.append({'order_by': 'count', 'direction': 'desc', 'ignorecase': 'false'})
        workplace_sort_order.append({'order_by': 'consumables', 'direction': 'desc', 'ignorecase': 'false'})
        user_sort_order.append({'order_by': 'consumables', 'direction': 'desc', 'ignorecase': 'false'})
      elif sort_by == 'total_cost':
        equipment_sort_order.append({'order_by': 'total_cost', 'direction': 'desc', 'ignorecase': 'false'})
        kit_sort_order.append({'order_by': 'total_cost', 'direction': 'desc', 'ignorecase': 'false'})
        consumable_sort_order.append({'order_by': 'total_cost', 'direction': 'desc', 'ignorecase': 'false'})
        workplace_sort_order.append({'order_by': 'total_cost', 'direction': 'desc', 'ignorecase': 'false'})
        user_sort_order.append({'order_by': 'total_cost', 'direction': 'desc', 'ignorecase': 'false'})
      elif sort_by == 'teachers':
        equipment_sort_order.append({'order_by': 'teacher_count', 'direction': 'desc', 'ignorecase': 'false'})
        kit_sort_order.append({'order_by': 'teacher_count', 'direction': 'desc', 'ignorecase': 'false'})
        consumable_sort_order.append({'order_by': 'teacher_count', 'direction': 'desc', 'ignorecase': 'false'})
        workplace_sort_order.append({'order_by': 'teacher_count', 'direction': 'desc', 'ignorecase': 'false'})
        user_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
      elif sort_by == 'workplaces':
        equipment_sort_order.append({'order_by': 'workplace_count', 'direction': 'desc', 'ignorecase': 'false'})
        kit_sort_order.append({'order_by': 'workplace_count', 'direction': 'desc', 'ignorecase': 'false'})
        consumable_sort_order.append({'order_by': 'workplace_count', 'direction': 'desc', 'ignorecase': 'false'})
        workplace_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
        user_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
      elif sort_by == 'classes':
        equipment_sort_order.append({'order_by': 'classes', 'direction': 'desc', 'ignorecase': 'false'})
        kit_sort_order.append({'order_by': 'classes', 'direction': 'desc', 'ignorecase': 'false'})
        consumable_sort_order.append({'order_by': 'classes', 'direction': 'desc', 'ignorecase': 'false'})
        workplace_sort_order.append({'order_by': 'classes', 'direction': 'desc', 'ignorecase': 'false'})
        user_sort_order.append({'order_by': 'classes', 'direction': 'desc', 'ignorecase': 'false'})
      elif sort_by == 'students':
        equipment_sort_order.append({'order_by': 'students', 'direction': 'desc', 'ignorecase': 'false'})
        kit_sort_order.append({'order_by': 'students', 'direction': 'desc', 'ignorecase': 'false'})
        consumable_sort_order.append({'order_by': 'students', 'direction': 'desc', 'ignorecase': 'false'})
        workplace_sort_order.append({'order_by': 'students', 'direction': 'desc', 'ignorecase': 'false'})
        user_sort_order.append({'order_by': 'students', 'direction': 'desc', 'ignorecase': 'false'})

      equipment_usage = paginate(request, list(equipment_usage.values()), equipment_sort_order, rows_per_page, page)
      kit_usage = paginate(request, list(kit_usage.values()), kit_sort_order, rows_per_page, page)
      consumable_usage = paginate(request, list(consumable_usage.values()), consumable_sort_order, rows_per_page, page)
      workplace_usage = paginate(request, list(workplace_usage.values()), workplace_sort_order, rows_per_page, page)
      user_usage = paginate(request, list(user_usage.values()), user_sort_order, rows_per_page, page)


      response_data = {}
      response_data['success'] = True
      context = {'equipment_usage': equipment_usage, 'kit_usage': kit_usage, 'consumable_usage': consumable_usage, 'user_usage': user_usage, 'total_usage': total_usage, 'from_date': from_date, 'to_date': to_date, 'workplace_usage': workplace_usage, 'sort_by': sort_by}
      response_data['html'] = render_to_string('bcse_app/BaxterBoxUsageTableView.html', context, request)
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################################
# BAXTER BOX INVENTORY TABLE VIEW
####################################################
@login_required
def baxterBoxInventory(request):
  """
  baxterBoxInventory is called from the path 'adminConfiguration'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/BaxterBoxInventory.html', which is a table view of inventories of lab kits and consumables
  :raises CustomException: redirects user to page they were on before encountering error
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view baxter box inventory')

    if request.session.get('box_inventory_search', False):
      searchForm = forms.BaxterBoxInventorySearchForm(initials=request.session['box_inventory_search'], prefix="box_inventory_search")
      page = request.session['box_inventory_search']['page']
    else:
      searchForm = forms.BaxterBoxInventorySearchForm(initials=None, prefix="box_inventory_search")
      page = 1

    context = {'searchForm': searchForm, 'page': page}
    return render(request, 'bcse_app/BaxterBoxInventory.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# FILTER BAXTER BOX INVENTORY BASED ON FILTER CRITERIA
##########################################################
def baxterBoxInventorySearch(request):
  """
  baxterBoxInventorySearch is called from the path 'baxterBoxInventory'
  :param request: request from the browser
  :returns: list of inventory that match search criteria in the template 'bcse_app/BaxterBoxInventoryTableView.html' or error page
  :raises CustomException: redirects user to page they were on before encountering error due to no permission for viewing reservations
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view baxter box inventory')
    else:

      activity_no_inventory = (models.Activity.objects.filter(activityinventory__isnull=True)
                                                      .annotate(
                                                          parent_id=F("id"),
                                                          color_hex=F("color__color"),
                                                          color_description=F("color__description"),
                                                          inventory_type=Value("A", output_field=CharField()),
                                                          count=Value("0", output_field=CharField()),
                                                          total_count=Value("0", output_field=CharField()),
                                                          expiration_date=Value(None, output_field=CharField()),
                                                          storage_location=Value("", output_field=CharField()),
                                                          inventory_notes=Value("", output_field=CharField()),
                                                          image_url=Case(
                                                              When(image="", then=Value("")),
                                                              default=Concat(
                                                                  Value(settings.MEDIA_URL),
                                                                  F("image"),
                                                              ),
                                                              output_field=CharField(),
                                                          ),
                                                      )
                                                      .values(
                                                          "id",
                                                          "name",
                                                          "image_url",
                                                          "parent_id",
                                                          "color_hex",
                                                          "color_description",
                                                          "count",
                                                          "expiration_date",
                                                          "storage_location",
                                                          "inventory_type",
                                                          "total_count",
                                                          "inventory_notes",
                                                      ))
      consumable_no_inventory = (models.Consumable.objects.filter(consumableinventory__isnull=True)
                                                         .annotate(
                                                            parent_id=F("id"),
                                                            color_hex=F("color__color"),
                                                            color_description=F("color__description"),
                                                            inventory_type=Value("C", output_field=CharField()),
                                                            count=Value("0", output_field=CharField()),
                                                            total_count=Value("0", output_field=CharField()),
                                                            expiration_date=Value(None, output_field=CharField()),
                                                            storage_location=Value("", output_field=CharField()),
                                                            inventory_notes=Value("", output_field=CharField()),
                                                            image_url=Case(
                                                                When(image="", then=Value("")),
                                                                default=Concat(
                                                                    Value(settings.MEDIA_URL),
                                                                    F("image"),
                                                                ),
                                                                output_field=CharField(),
                                                            ),
                                                        )
                                                        .values(
                                                            "id",
                                                            "name",
                                                            "image_url",
                                                            "parent_id",
                                                            "color_hex",
                                                            "color_description",
                                                            "count",
                                                            "expiration_date",
                                                            "storage_location",
                                                            "inventory_type",
                                                            "total_count",
                                                            "inventory_notes",
                                                        ))
      activity_inventory = (models.ActivityInventory.objects.annotate(
                                                            name=F("activity__name"),
                                                            parent_id=F("activity_id"),
                                                            color_hex=F("activity__color__color"),
                                                            color_description=F("activity__color__description"),
                                                            inventory_type=Value("A", output_field=CharField()),
                                                            inventory_notes=F("notes"),
                                                            total_count=Window(
                                                                expression=Sum("count"),
                                                                partition_by=[
                                                                    F("activity"),
                                                                    F("storage_location"),
                                                                ],
                                                            ),
                                                            image_url=Case(
                                                                When(activity__image="", then=Value("")),
                                                                default=Concat(
                                                                    Value(settings.MEDIA_URL),
                                                                    F("activity__image"),
                                                                ),
                                                                output_field=CharField(),
                                                            ),
                                                        )
                                                        .values(
                                                            "id",
                                                            "name",
                                                            "image_url",
                                                            "parent_id",
                                                            "color_hex",
                                                            "color_description",
                                                            "count",
                                                            "expiration_date",
                                                            "storage_location",
                                                            "inventory_type",
                                                            "total_count",
                                                            "inventory_notes",
                                                        ))
      consumable_inventory = (models.ConsumableInventory.objects.annotate(
                                                                  name=F("consumable__name"),
                                                                  parent_id=F("consumable_id"),
                                                                  color_hex=F("consumable__color__color"),
                                                                  color_description=F("consumable__color__description"),
                                                                  inventory_type=Value("C", output_field=CharField()),
                                                                  inventory_notes=F("notes"),
                                                                  total_count=Window(
                                                                      expression=Sum("count"),
                                                                      partition_by=[
                                                                          F("consumable"),
                                                                          F("storage_location"),
                                                                      ],
                                                                  ),
                                                                  image_url=Case(
                                                                      When(consumable__image="", then=Value("")),
                                                                      default=Concat(
                                                                          Value(settings.MEDIA_URL),
                                                                          F("consumable__image"),
                                                                      ),
                                                                      output_field=CharField(),
                                                                  ),
                                                              )
                                                              .values(
                                                                  "id",
                                                                  "name",
                                                                  "image_url",
                                                                  "parent_id",
                                                                  "color_hex",
                                                                  "color_description",
                                                                  "count",
                                                                  "expiration_date",
                                                                  "storage_location",
                                                                  "inventory_type",
                                                                  "total_count",
                                                                  "inventory_notes",
                                                              ))
    if request.method == 'GET':

      activity_query_filter = Q()
      consumable_query_filter = Q()

      activities = request.GET.getlist('box_inventory_search-activities', '')
      consumables = request.GET.getlist('box_inventory_search-consumables', '')
      storage_locations = request.GET.getlist('box_inventory_search-storage_locations', '')
      expiration_date = request.GET.get('box_inventory_search-expiration_date_after', '')
      color = request.GET.getlist('box_inventory_search-color', '')
      inventory_type = request.GET.get('box_inventory_search-inventory_type', '')

      sort_by = request.GET.get('box_inventory_search-sort_by', '')
      rows_per_page = request.GET.get('box_inventory_search-rows_per_page', settings.DEFAULT_ITEMS_PER_PAGE)
      page = request.GET.get('page', '')

     #set session variable
      request.session['box_inventory_search'] = {
        'activities': activities,
        'consumables': consumables,
        'expiration_date_after': expiration_date,
        'storage_locations': storage_locations,
        'color': color,
        'inventory_type': inventory_type,
        'sort_by': sort_by,
        'rows_per_page': rows_per_page,
        'page': page
      }

      if expiration_date:
        expiration_date = datetime.datetime.strptime(expiration_date, '%B %d, %Y')
        expiration_date_filter = Q(Q(expiration_date__gte=expiration_date) | Q(expiration_date__isnull=True))

      if activities or inventory_type == 'kit':
        if activities:
          activity_query_filter = Q(activity__in=activities)
          activity_no_inventory = activity_no_inventory.filter(id__in=activities)
        if expiration_date:
          activity_query_filter = activity_query_filter & expiration_date_filter
        if color:
          activity_query_filter = activity_query_filter & Q(activity__color__id__in=color)
          activity_no_inventory = activity_no_inventory.filter(color__id__in=color)

        if storage_locations:
          activity_query_filter = activity_query_filter & Q(storage_location__in=storage_locations)

        inventory = activity_inventory.filter(activity_query_filter).union(activity_no_inventory)



      elif consumables or inventory_type == 'consumable':
        if consumables:
          consumable_query_filter = Q(consumable__in=consumables)
          consumable_no_inventory = consumable_no_inventory.filter(id__in=consumables)
        if expiration_date:
          consumable_query_filter = consumable_query_filter & expiration_date_filter
        if color:
          consumable_query_filter = consumable_query_filter & Q(consumable__color__id__in=color)
          consumable_no_inventory = consumable_no_inventory.filter(color__id__in=color)
        if storage_locations:
          consumable_query_filter = consumable_query_filter & Q(storage_location__in=storage_locations)

        inventory = consumable_inventory.filter(consumable_query_filter).union(consumable_no_inventory)

      else:

        if expiration_date:
          activity_query_filter = activity_query_filter & expiration_date_filter
          consumable_query_filter = consumable_query_filter & expiration_date_filter

        if color:
          activity_color_filter = Q(activity__color__id__in=color)
          consumable_color_filter =  Q(consumable__color__id__in=color)
          activity_no_inventory = activity_no_inventory.filter(color__id__in=color)
          consumable_no_inventory = consumable_no_inventory.filter(color__id__in=color)

          activity_query_filter = activity_query_filter & activity_color_filter
          consumable_query_filter = consumable_query_filter & consumable_color_filter

        if storage_locations:
          activity_query_filter = activity_query_filter & Q(storage_location__in=storage_locations)
          consumable_query_filter = consumable_query_filter & Q(storage_location__in=storage_locations)

        activity_inventory = activity_inventory.filter(activity_query_filter)
        consumable_inventory = consumable_inventory.filter(consumable_query_filter)

        inventory = activity_inventory.union(consumable_inventory).union(activity_no_inventory).union(consumable_no_inventory)

      direction = request.GET.get('direction') or 'asc'
      ignorecase = request.GET.get('ignorecase') or 'false'

      sort_order = []
      if sort_by:
        if sort_by == 'name':
          sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'storage_location', 'direction': 'asc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'expiration_date', 'direction': 'asc', 'ignorecase': 'false'})
        elif sort_by == 'expiration_date_asc':
          sort_order.append({'order_by': 'expiration_date', 'direction': 'asc', 'ignorecase': 'false'})
        elif sort_by == 'expiration_date_desc':
          sort_order.append({'order_by': 'expiration_date', 'direction': 'desc', 'ignorecase': 'false'})
        elif sort_by == 'count_asc':
          sort_order.append({'order_by': 'count', 'direction': 'asc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'storage_location', 'direction': 'asc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'expiration_date', 'direction': 'asc', 'ignorecase': 'false'})
        elif sort_by == 'count_desc':
          sort_order.append({'order_by': 'count', 'direction': 'desc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'storage_location', 'direction': 'asc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'expiration_date', 'direction': 'asc', 'ignorecase': 'false'})
        elif sort_by == 'total_count_asc':
          sort_order.append({'order_by': 'total_count', 'direction': 'asc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'storage_location', 'direction': 'asc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'expiration_date', 'direction': 'asc', 'ignorecase': 'false'})
        elif sort_by == 'total_count_desc':
          sort_order.append({'order_by': 'total_count', 'direction': 'desc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'storage_location', 'direction': 'asc', 'ignorecase': 'false'})
          sort_order.append({'order_by': 'expiration_date', 'direction': 'asc', 'ignorecase': 'false'})

      inventory = paginate(request, inventory, sort_order, rows_per_page, page)

      context = {'inventory': inventory}
      response_data = {}
      response_data['success'] = True
      response_data['html'] = render_to_string('bcse_app/BaxterBoxInventoryTableView.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################################
# INVENTORY CREATE
####################################################
@login_required
def inventoryCreate(request):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to create inventory')

    form = forms.InventoryForm()
    context = {'form': form}
    return render(request, 'bcse_app/InventoryCreate.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################################
# INVENTORY EDIT
####################################################
@login_required
def inventoryEdit(request, id='', inventory_type='A'):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit inventory')

    if inventory_type == 'A':
      if id != '':
        inventory = models.ActivityInventory.objects.get(id=id)
      else:
        inventory = models.ActivityInventory()
    else:
      if id != '':
        inventory = models.ConsumableInventory.objects.get(id=id)
      else:
        inventory = models.ConsumableInventory()

    if request.method == 'GET':
      if inventory_type == 'A':
        form = forms.ActivityInventoryForm(instance=inventory)
      else:
        form = forms.ConsumableInventoryForm(instance=inventory)

      context = {'form': form, 'inventory_type': inventory_type}
      return render(request, 'bcse_app/InventoryEdit.html', context)

    elif request.method == 'POST':

      data = request.POST.copy()
      if inventory_type == 'A':
        form = forms.ActivityInventoryForm(data, instance=inventory)
      else:
        form = forms.ConsumableInventoryForm(data, instance=inventory)
      response_data = {}
      if form.is_valid():
        saved_inventory = form.save()
        messages.success(request, "Inventory saved")
        response_data['success'] = True
      else:
        print(form.errors)
        messages.error(request, "Inventory could not be saved. Check the errors below.")
        context = {'form': form, 'inventory_type': inventory_type}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/InventoryEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.ActivityInventory.DoesNotExist:
    messages.success(request, "Activity Inventory not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.ConsumableInventory.DoesNotExist:
    messages.success(request, "Consumable Inventory not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################################
# INVENTORY DELETE
####################################################
@login_required
def inventoryDelete(request, id='', inventory_type='A'):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete inventory')

    if inventory_type == 'A':
      if id != '':
        inventory = models.ActivityInventory.objects.get(id=id)
    else:
      if id != '':
        inventory = models.ConsumableInventory.objects.get(id=id)

    if inventory:
      inventory.delete()
      messages.success(request, "Inventory deleted")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.ActivityInventory.DoesNotExist:
    messages.success(request, "Activity Inventory not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.ConsumableInventory.DoesNotExist:
    messages.success(request, "Consumable Inventory not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################################
# RESERVATION DELIVERY/PICKUP EMAIL TEMPLATE
####################################################
@login_required
def reservationDeliveryPickupEmailTemplateEdit(request, id=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit reservation delivery/pickup email template')

    if id != '':
      email_template = models.ReservationDeliveryPickupEmailTemplate.objects.get(id=id)
    else:
      email_template = models.ReservationDeliveryPickupEmailTemplate()

    if request.method == 'GET':
      form = forms.ReservationDeliveryPickupEmailTemplateForm(instance=email_template)
      context = {'form': form}
      return render(request, 'bcse_app/ReservationDeliveryPickupEmailTemplateEdit.html', context)

    elif request.method == 'POST':
      data = request.POST.copy()
      response_data = {}
      form = forms.ReservationDeliveryPickupEmailTemplateForm(data, instance=email_template)
      if form.is_valid():
        saved_email_template = form.save()
        messages.success(request, "Reservation delivery/pickup email template saved")
        response_data['success'] = True
      else:
        print(form.errors)
        messages.error(request, "Reservation delivery/pickup email template could not be saved. Check the errors below.")
        context = {'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/ReservationDeliveryPickupEmailTemplateEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])


  except models.ReservationDeliveryPickupEmailTemplate.DoesNotExist:
    messages.success(request, "Reservation delivery/pickup email template not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

#################################################################
# RESERVATION DELIVERY/PICKUP EMAIL FOR INDIVIDUAL RESERVATIONS
#################################################################
@login_required
def reservationDeliveryPickupEmailEdit(request, reservation_id=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S', 'D']:
      raise CustomException('You do not have the permission to edit reservation delivery/pickup email')

    reservation = models.Reservation.objects.get(id=reservation_id)
    delivery_email_template = models.ReservationDeliveryPickupEmailTemplate.objects.get(delivery_or_pickup='D')
    pickup_email_template = models.ReservationDeliveryPickupEmailTemplate.objects.get(delivery_or_pickup='P')

    try:
      delivery_email = models.ReservationDeliveryPickupEmail.objects.get(reservation=reservation, delivery_or_pickup='D')
    except models.ReservationDeliveryPickupEmail.DoesNotExist:
      delivery_email = models.ReservationDeliveryPickupEmail(reservation=reservation, delivery_or_pickup='D', email_subject=delivery_email_template.email_subject, email_message=delivery_email_template.email_message)
    try:
      pickup_email = models.ReservationDeliveryPickupEmail.objects.get(reservation=reservation, delivery_or_pickup='P')
    except models.ReservationDeliveryPickupEmail.DoesNotExist:
      pickup_email = models.ReservationDeliveryPickupEmail(reservation=reservation, delivery_or_pickup='P', email_subject=pickup_email_template.email_subject, email_message=pickup_email_template.email_message)


    if request.method == 'GET':
      delivery_form = forms.ReservationDeliveryPickupEmailForm(instance=delivery_email, prefix="delivery")
      pickup_form = forms.ReservationDeliveryPickupEmailForm(instance=pickup_email, prefix="pickup")
      context = {'reservation': reservation, 'delivery_form': delivery_form, 'pickup_form': pickup_form}
      return render(request, 'bcse_app/ReservationDeliveryPickupEmailEdit.html', context)

    elif request.method == 'POST':
      data = request.POST.copy()
      response_data = {}
      delivery_form = forms.ReservationDeliveryPickupEmailForm(data, instance=delivery_email, prefix="delivery")
      pickup_form = forms.ReservationDeliveryPickupEmailForm(data, instance=pickup_email, prefix="pickup")
      if delivery_form.is_valid() and pickup_form.is_valid():
        delivery_form.save()
        pickup_form.save()
        response_data['message'] =  "Reservation delivery/pickup email saved"
        response_data['success'] = True
      else:
        print(form.errors)
        messages.error(request, "Reservation delivery/pickup email could not be saved. Check the errors below.")
        context = {'reservation': reservation, 'delivery_form': delivery_form, 'pickup_form': pickup_form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/ReservationDeliveryPickupEmailEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.Reservation.DoesNotExist:
    messages.error(request, "Reservation not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.ReservationDeliveryPickupEmailTemplate.DoesNotExist:
    messages.error(request, "Reservation Delivery/Pickup EmailTemplate does not exist")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################################
# WORKSHOP REGISTRATION CONFIRMATION MESSAGES
####################################################
@login_required
def registrationEmailMessages(request):
  """
  registrationEmailMessages is called from the path 'adminConfiguration'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/RegistrationEmailMessages.html', which is a page with automatic emails sent after registration
  :raises CustomException: redirects user to page they were on before encountering error
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view registration messages')

    registration_messages = get_registration_emails(request)

    context = {'registration_messages': registration_messages}
    return render(request, 'bcse_app/RegistrationEmailMessages.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

@login_required
def get_registration_emails(request):
  """
  get_registration_emails is called from the path 'registrationEmailMessages'
  :param request: request from the browser
  :returns: a queryset of generic registration emails
  :raises CustomException: redirects user to page they were on before encountering error
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view registration messages')

    registration_messages = models.RegistrationEmailMessage.objects.all().annotate(
      trigger=Case(
          When(registration_status='R', then=Value('When a user registers for a workshop scheduled for a future date and the workshop has capacity.')),
          When(registration_status='A', then=Value('When a user applies to a workshop scheduled for a future date.')),
          When(registration_status='C', then=Value('When a user\'s application is accepted by an admin and the workshop is scheduled for a future date.')),
          When(registration_status='D', then=Value('When a user\'s application is denied by an admin and the workshop is scheduled for a future date.')),
          When(registration_status='N', then=Value('When a user\'s application or registration is denied by an admin and the workshop is scheduled for a future date.')),
          When(registration_status='W', then=Value('When a user attempts to register for a workshop that is full or when an admin moves an existing registration to waitlist.  In both cases the workshop is scheduled for a future date ')),
          When(registration_status='P', then=Value('When an admin moves an existing registration or application to pending status and the workshop is scheduled for a future date. ')),
          default=Value('Registration email should not be created for this status'),
          output_field=CharField(),
        ))

    return registration_messages

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


################################################
# PREVIEW WORKSHOP REGISTRATION EMAIL
################################################
def registrationEmailMessagePreview(request, id='', workshop_id=''):
  """
  registrationEmailMessagePreview is called from the path 'workshop/<workshop_id>/registration_emails/'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :param id='': id of registration email
  :returns: rendered template 'bcse_app/WorkshopRegistrationEmailPreview.html
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to registrant not belonging to workshop
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to preview workshop registration email')

    if '' != id:
      workshop_registration_email = models.RegistrationEmailMessage.objects.get(id=id)
      workshop = models.Workshop.objects.get(id=workshop_id)

      domain = request.get_host()

      subject = workshop_registration_email.email_subject
      subject = models.replace_workshop_tokens(subject, workshop)

      if domain != 'bcse.northwestern.edu':
        subject = '***** TEST **** '+ subject + ' ***** TEST **** '

      email_body = workshop_registration_email.email_message
      email_body = models.replace_workshop_tokens(email_body, workshop)

      context = {'email_body': email_body, 'subject': subject}

      return render(request, 'bcse_app/WorkshopEmailView.html', context)

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.WorkshopRegistrationEmail.DoesNotExist:
    messages.success(request, "Workshop Registration Email not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.Workshop.DoesNotExist:
    messages.success(request, "Workshop not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))



####################################
# EDIT TAG
####################################
@login_required
def tagEdit(request, id=''):
  """
  tagEdit is called from the path 'tags'
  :param request: request from the browser
  :param id='': id of tag
  :returns: JSON view of all tags or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit a tag')
    if '' != id:
      tag = models.Tag.objects.get(id=id)
    else:
      tag = models.Tag()

    if request.method == 'GET':
      form = forms.TagForm(instance=tag)
      context = {'form': form}
      return render(request, 'bcse_app/TagEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.TagForm(data, files=request.FILES, instance=tag)
      response_data = {}
      if form.is_valid():
        savedCategory = form.save()
        messages.success(request, "Tag saved")
        response_data['success'] = True
      else:
        print(form.errors)
        messages.error(request, "Tag could not be saved. Check the errors below.")
        context = {'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/TagEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# DELETE TAG
####################################
@login_required
def tagDelete(request, id=''):
  """
  tagDelete is called from the path 'tags'
  :param request: request from the browser
  :param id='': id of Tag
  :returns: redirects to page to view all remaining Tags
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete a tag')
    if '' != id:
      tag = models.Tag.objects.get(id=id)
      tag.delete()
      messages.success(request, "Tag deleted")

    return shortcuts.redirect('bcse:tags')

  except models.Tag.DoesNotExist:
    messages.success(request, "Tag not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# TAGS
####################################
@login_required
def tags(request):
  """
  tags is called from the path 'adminConfiguration'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/Tags.html', a page to view tags
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view tags')

    tags = models.Tag.objects.all().order_by('order')
    context = {'tags': tags}
    return render(request, 'bcse_app/Tags.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################
# SUBTAGS
####################################
@login_required
def subTags(request):
  """
  subTags is called from the path 'tags'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/SubTags.html', a page to view all sub tags
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view Sub Tags')

    sub_tags = models.SubTag.objects.all()
    context = {'sub_tags': sub_tags}
    return render(request, 'bcse_app/SubTags.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# EDIT SUB TAG
####################################
@login_required
def subTagEdit(request, id=''):
  """
  subTagEdit is called from the path 'subTags'
  :param request: request from the browser
  :param id='': id of sub tag
  :returns: JSON view of all sub tags or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit a sub tag')
    if '' != id:
      sub_tag = models.SubTag.objects.get(id=id)
    else:
      if request.GET.get('tag'):
        print(request.GET)
        tag = models.Tag.objects.get(id=request.GET.get('tag'))
        sub_tag = models.SubTag(tag=tag)
      else:
        sub_tag = models.SubTag()

    if request.method == 'GET':
      form = forms.SubTagForm(instance=sub_tag)
      context = {'form': form}
      return render(request, 'bcse_app/SubTagEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.SubTagForm(data, files=request.FILES, instance=sub_tag)
      response_data = {}
      if form.is_valid():
        savedCategory = form.save()
        messages.success(request, "Sub Tag saved")
        response_data['success'] = True
      else:
        print(form.errors)
        messages.error(request, "Sub Tag could not be saved. Check the errors below.")
        context = {'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/SubTagEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# DELETE SUB TAG
####################################
@login_required
def subTagDelete(request, id=''):
  """
  subTagDelete is called from the path 'SubTags'
  :param request: request from the browser
  :param id='': id of sub tag
  :returns: redirects to page to view all remaining sub tags
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete a Sub Tag')
    if '' != id:
      sub_tag = models.SubTag.objects.get(id=id)
      sub_tag.delete()
      messages.success(request, "Sub Tag deleted")

    return shortcuts.redirect('bcse:subTags')

  except models.SubTag.DoesNotExist:
    messages.success(request, "Baxter Sub Tag not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))



####################################
# EDIT WORKSHOP CATEGORY
####################################
@login_required
def workshopCategoryEdit(request, id=''):
  """
  workshopCategoryEdit is called from the path 'workshopCategories'
  :param request: request from the browser
  :param id='': id of workshop category
  :returns: rendered template 'bcse_app/WorkshopCategoryEdit.html', redirects to page to filtered view of all workshops of the specified category, or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
  """
  workshopCategoryDelete is called from the path 'workshopCategories'
  :param request: request from the browser
  :param id='': id of workshop category
  :returns: redirects to page view of all remaining workshop categories
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
  """
  workshopCategories is called from the path 'adminConfiguration/workshopCategories/'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/WorkshopCategories.html', a page to view all categories of workshops
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view workshop categories')

    if request.session.get('workshop_categories_search', False):
      searchForm = forms.WorkshopCategoriesSearchForm(user=request.user, initials=request.session['workshop_categories_search'], prefix="workshop_category_search")
      page = request.session['workshop_categories_search']['page']
    else:
      searchForm = forms.WorkshopCategoriesSearchForm(user=request.user, initials=None, prefix="workshop_category_search")
      page = 1

    context = {'searchForm': searchForm, 'page': page}
    return render(request, 'bcse_app/WorkshopCategories.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# FILTER WORKSHOP CATEGORIES BASED ON FILTER CRITERIA
##########################################################
def workshopCategoriesSearch(request):
  """
  workshopCatgoriesSearch is called from the path 'workshopCategories'
  :param request: request from the browser
  :returns: JSON object with a rendered template of search results
  """

  if request.method == 'GET':

    query_filter = Q()
    name_filter = None
    workshop_type_filter = None
    keyword_filter = None
    status_filter = None

    name = request.GET.get('workshop_category_search-name', '')
    keywords = request.GET.get('workshop_category_search-keywords', '')
    workshop_types = request.GET.getlist('workshop_category_search-workshop_type', '')
    status = request.GET.get('workshop_category_search-status', '')
    sort_by = request.GET.get('workshop_category_search-sort_by', '')
    rows_per_page = request.GET.get('workshop_category_search-rows_per_page', settings.DEFAULT_ITEMS_PER_PAGE)
    page = request.GET.get('page', '')

    #set session variable
    workshop_category_search_vars = {
      'name': name,
      'keywords': keywords,
      'workshop_types': workshop_types,
      'status': status,
      'sort_by': sort_by,
      'rows_per_page': rows_per_page,
      'page': page
    }

    request.session['workshop_categories_search'] = workshop_category_search_vars

    if keywords:
      keyword_filter = Q(name__icontains=keywords)
      keyword_filter = keyword_filter | Q(description__icontains=keywords)

    if name:
      name_filter = Q(name__icontains=name)

    if status:
      status_filter = Q(status=status)

    if workshop_types:
      workshop_type_filter = Q(workshop_type__in=workshop_types)

    if keyword_filter:
      query_filter = keyword_filter
    if status_filter:
      query_filter = query_filter & status_filter
    if name_filter:
      query_filter = query_filter & name_filter
    if workshop_type_filter:
      query_filter = query_filter & workshop_type_filter


    workshop_categories = models.WorkshopCategory.objects.all().filter(query_filter).distinct()

    order_by = 'name'
    direction = request.GET.get('direction') or 'desc'
    ignorecase = request.GET.get('ignorecase') or 'false'
    if sort_by:
      if sort_by == 'name':
        order_by = 'name'
        direction = 'asc'
        ignorecase = 'true'
      elif sort_by == 'type':
        order_by = 'workshop_type'
        direction = 'desc'
        ignorecase = 'false'


    sort_order = [{'order_by': order_by, 'direction': direction, 'ignorecase': ignorecase}]
    workshop_categories = paginate(request, workshop_categories, sort_order, rows_per_page, page)

    context = {'workshop_categories': workshop_categories}
    response_data = {}
    response_data['success'] = True
    response_data['html'] = render_to_string('bcse_app/WorkshopCategoriesTableView.html', context, request)

    return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  return http.HttpResponseNotAllowed(['GET'])



####################################
# GET WORKSHOP CATEGORY DETAILS
####################################
@login_required
def getWorkshopCategoryDetails(request, id=''):
  """
  getWorkshopCategoryDetails is called from the path 'workshopCategories'
  :param request: request from the browser
  :param id='': id of workshop category
  :returns: JSON view of all categories of workshops
  :raises CustomException: sets response_data success to false, indicating inability to get category details due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view workshop category')

    workshop_category = models.WorkshopCategory.objects.get(id=id)
    response_data = {'success': True, 'name': workshop_category.name, 'workshop_type': workshop_category.workshop_type, 'description': workshop_category.description}
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
  """
  workshopEdit is called from the path 'workshops/edit'
  :param request: request from the browser
  :param id='': id of workshop
  :returns: rendered template 'bcse_app/WorkshopEdit.html', redirects to page with specified workshop, or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
  """
  workshopCopy is called from the path 'workshops/edit'
  :param request: request from the browser
  :param id='': id of workshop
  :returns: redirects to page with specified workshop or page user was on before
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
      workshop.featured = False
      workshop.cancelled = False
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
  """
  workshopDelete is called from the path 'workshops/edit'
  :param request: request from the browser
  :param id='': id of workshop
  :returns: redirects to page view of remaining workshops or page user was on before since workshop already has registrants
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete this workshop')

    if '' != id:
      workshop = models.Workshop.objects.get(id=id)
      if hasattr(workshop, 'registration_setting') and workshop.registration_setting.registrants.all().count() > 0:
        messages.error(request, "This workshop cannot be deleted as it has existing registrants.")
        return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
      else:
        workshop.delete()
        messages.success(request, "Workshop deleted")

    return shortcuts.redirect('bcse:workshops', flag='table')

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
  """
  workshopView is called from the path 'workshops/edit'
  :param request: request from the browser
  :param id='': id of workshop
  :returns: rendered template 'bcse_app/WorkshopAdminView.html' or rendered template 'bcse_app/WorkshopPublicView.html'
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises models.Workshop.DoesNotExist: redirects user to page they were on before encountering error due to workshop not existing
  """
  try:
    if '' != id:
      workshop = models.Workshop.objects.get(id=id)
      if workshop.status != 'A' or workshop.workshop_category.status != 'A':
        if request.user.is_anonymous:
          raise CustomException('You do not have the permission to view this workshop')
        elif request.user.userProfile.user_role not in ['A', 'S'] and models.TeacherLeader.objects.all().filter(teacher=request.user.userProfile, id__in=workshop.teacher_leaders.all()).count() == 0:
          raise CustomException('You do not have the permission to view this workshop')

      registration = workshopRegistration(request, workshop.id)

      context = {'workshop': workshop, 'registration': registration}

      if request.user.is_authenticated and request.user.userProfile.user_role in ['A', 'S']:
        return render(request, 'bcse_app/WorkshopAdminView.html', context)
      else:
        return render(request, 'bcse_app/WorkshopPublicView.html', context)
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
  """
  workshopRegistration is called from the path 'workshops/list'
  :param request: request from the browser
  :param workshop_id: id of workshop
  :returns: JSON view of workshops user is registered for or successful registration information
  """
  registration = {}
  form = workshop_registration = user_message = admin_message = message_class = current_status = None
  registration_open = False

  workshop = models.Workshop.objects.get(id=workshop_id)
  if workshop.cancelled:
    registration['user_message'] = 'This workshop has been cancelled'
    registration['message_class'] = 'warning'
    return registration
  else:
    registration_setting_status = workshopRegistrationSettingStatus(workshop)

    if workshop.enable_registration and workshop.registration_setting and workshop.registration_setting.registration_type:

      if workshop.registration_setting.registration_type in ['R', 'E']:
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
        if workshop.registration_setting.registration_type == 'E':
          if registration_setting_status['registration_open']:
            if workshop.registration_setting.external_registration_link:
              if workshop.registration_setting.external_link_label:
                user_message = '<a class="btn" href="%s" target="_blank">%s</a>' % (workshop.registration_setting.external_registration_link, workshop.registration_setting.external_link_label)
              else:
                user_message = '<a class="btn" href="%s" target="_blank">%s</a>' % (workshop.registration_setting.external_registration_link, "Click here to register for this workshop")
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
              current_status = workshop_registration.status
              # if registration is cancelled, allow users to re-register or re-apply
              if current_status == 'N':
                workshop_registration.status = registration_setting_status['default_registration_status']
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
      registration['current_status'] = current_status

      return registration

    elif request.method == 'POST':
      data = request.POST.copy()
      recaptcha_token = data.get("recaptchaToken")
      recaptcha_passed = validateReCaptcha(recaptcha_token, 'workshop_registration')

      registration_id = None
      form = forms.WorkshopRegistrationForm(data, instance=workshop_registration, prefix='workshop-%s'%workshop.id)
      if recaptcha_passed and form.is_valid():
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
          registration['current_status'] = saved_registration.status

        #create registration - workplace association
        if saved_registration.user.work_place:
          try:
            registration_work_place = models.RegistrationWorkPlace.objects.get(registration=saved_registration)
            registration_work_place.work_place = saved_registration.user.work_place
            registration_work_place.save()
          except models.RegistrationWorkPlace.DoesNotExist:
            registration_work_place = models.RegistrationWorkPlace(registration=saved_registration, work_place=saved_registration.user.work_place)
            registration_work_place.save()

        success = True
      else:
        print(form.errors)
        if not request.is_ajax():
          if not recaptcha_passed:
            messages.error(request, "reCAPTCHA validation failed")
          else:
            messages.error(request, "There were some errors")
        if request.user.userProfile.user_role in ['A', 'S']:
          if not recaptcha_passed:
            admin_message = "reCAPTCHA validation failed"
          else:
            try:
              registration_user = data.get("workshop-%s-user"%workshop.id, "")
              if registration_user:
                reg = userRegistration(request, workshop.id, registration_user)
                admin_message = "Workshop registration for user <b>%s</b> already exists. If you need to update the registration status for this user, please use the Registrants tab" % reg.user

            except CustomException as ce:
              admin_message = "Something went wrong with the workshop registration"

          registration['admin_message'] = admin_message
        else:
          if not recaptcha_passed:
            user_message = "reCAPTCHA validation failed"
          registration['user_message'] = user_message

        registration['form'] = form
        registration['instance'] = workshop_registration
        registration['message_class'] = message_class
        registration['current_status'] = current_status
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
  """
  workshopRegistrationSettingStatus is called from the path 'workshops/edit'
  :param workshop: workshop to edit
  :param id='': id of workshop
  :returns: status of the workshop

  """
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
  """
  workshopRegistrationEdit is called from the path 'workshops/edit'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :param id='': id of registrant
  :returns: rendered template 'bcse_app/WorkshopRegistrationModal.html, JSON view of workshops or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to registrant not belonging to workshop
  """

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
        work_place = form.cleaned_data['work_place']
        savedRegistration = form.save()
        if hasattr(savedRegistration, 'registration_to_work_place'):
          savedRegistration.registration_to_work_place.work_place = work_place
          savedRegistration.registration_to_work_place.save()
        else:
          registration_work_place = models.RegistrationWorkPlace(registration=savedRegistration, work_place=work_place)
          registration_work_place.save()

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
  """
  workshopRegistrationDelete is called from the path 'workshops/edit'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :param id='': id of registrant
  :returns: redirect to page user was on before
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to registrant not belonging to workshop
  """

  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to edit this registration')
    else:
      registration = models.Registration.objects.get(id=id)
      workshop = models.Workshop.objects.get(id=workshop_id)

      if request.user.userProfile.user_role not in ['A', 'S']:
        raise CustomException('You do not have the permission to edit this registration')

      if registration.workshop_registration_setting.workshop.id != workshop.id:
        raise CustomException('Registration does not belong to the workshop')

      #delete associated workshop application
      workshop_applications = models.WorkshopApplication.objects.all().filter(registration=registration)
      for workshop_application in workshop_applications:
        workshop_application.application.delete()
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
# CANCEL WORKSHOP REGISTRATION
################################################
def workshopRegistrationCancel(request, workshop_id='', id=''):
  """
  workshopRegistrationCancel is called from the path 'workshops/edit'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :param id='': id of registrant
  :returns: redirect to page user was on before
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to registrant not belonging to workshop
  """

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

      registration.status = 'N'
      registration.save()
      messages.success(request, "Registration has been cancelled")
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
# WORKSHOP REGISTRATION QUESTIONNAIRE
################################################
def workshopRegistrationQuestionnaire(request, workshop_id=''):
  """
  workshopRegistrationQuestionnaire is called from the path 'workshops/edit'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :returns: rendered template 'bcse_app/WorkshopRegistrationQuestionnaireModal.html', JSON view of workshop or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to questionairre not being available
  :raises CustomException: redirects user to page they were on before encountering error due to registration not being enabled
  :raises models.Workshop.DoesNotExist: redirects user to page they were on before encountering error due to workshop not being found
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['T', 'P']:
      raise CustomException('You do not have the permission to submit registration questionnaire')

    if '' != workshop_id:
      workshop = models.Workshop.objects.get(id=workshop_id)
      if not workshop.enable_registration:
        raise CustomException('Workshop registration is not enabled')
      elif not workshop.registration_setting or workshop.registration_setting.registration_type != 'R':
        raise CustomException('Workshop registration questionnaire is not available for this workshop')
    else:
      raise models.Workshop.DoesNotExist

    if request.method == 'GET':
      form = forms.WorkshopRegistrationQuestionnaireForm(instance=request.user.userProfile)
      context = {'form': form, 'workshop': workshop, 'photo_release_url': settings.PHOTO_RELEASE_URL}
      return render(request, 'bcse_app/WorkshopRegistrationQuestionnaireModal.html', context)

    elif request.method == 'POST':
      response_data = {}
      data = request.POST.copy()
      form = forms.WorkshopRegistrationQuestionnaireForm(data, instance=request.user.userProfile)
      if form.is_valid():
        savedQuestionnaire = form.save()
        messages.success(request, "Registration questionnaire saved")
        response_data['success'] = True
      else:
        print(form.errors)
        messages.error(request, 'Registration questionnaire could not be saved')
        context = {'form': form, 'workshop': workshop, 'photo_release_url': settings.PHOTO_RELEASE_URL}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/WorkshopRegistrationQuestionnaireModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.Workshop.DoesNotExist:
    messages.success(request, "Workshop not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

################################################
# GET WORKSHOP REGISTRATION MESSAGE TO DISPLAY
################################################
def workshopRegistrationMessage(workshop_registration):
  """
  workshopRegistrationQuestionnaire is called from the path 'workshops/edit'
  :param workshop_registration: workshop registration status to edit
  :returns: updated registration status
  """
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
  #elif workshop_registration.status == 'N':
  #  message = 'Your %s is cancelled for this workshop' % registration_type
  #  message_class = 'error'
  elif workshop_registration.status == 'W':
    message = 'Your %s is waitlisted for this workshop' % registration_type
    message_class = 'warning'

  return {'message': message, 'message_class': message_class}

################################################
# EDIT WORKSHOP EMAILS
################################################
def workshopEmailEdit(request, workshop_id='', id=''):
  """
  workshopEmailEdit is called from the path 'workshop/<id>/edit'
  :param request: request from the browser
  :param id='': id of workshop email
  :returns: rendered template 'bcse_app/WorkshopEmailModal.html, JSON view of workshops or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to registrant not belonging to workshop
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit workshop email')

    if '' != id:
      workshop_email = models.WorkshopEmail.objects.get(id=id)
      workshop = models.Workshop.objects.get(id=workshop_id)
      if workshop_email.workshop.id != workshop.id:
        raise CustomException('The workshop email does not belong to the workshop')
    else:
      workshop = models.Workshop.objects.get(id=workshop_id)
      workshop_email = models.WorkshopEmail(workshop=workshop)

    if request.method == 'GET':
      form = forms.WorkshopEmailForm(instance=workshop_email)
      context = {'form': form, 'workshop': workshop}
      return render(request, 'bcse_app/WorkshopEmailEdit.html', context)

    elif request.method == 'POST':
      response_data = {}
      data = request.POST.copy()
      send_email = False
      if data['send'][0] == '1':
        send_email = True
      form = forms.WorkshopEmailForm(data, instance=workshop_email)
      if form.is_valid():
        selected_status = form.cleaned_data['registration_statuses']
        selected_sub_status = form.cleaned_data['registration_sub_statuses']
        savedWorkshopEmail = form.save(commit=False)
        savedWorkshopEmail.set_registration_status(selected_status)
        savedWorkshopEmail.set_registration_sub_status(selected_sub_status)
        if savedWorkshopEmail.scheduled_date and not savedWorkshopEmail.scheduled_time:
          savedWorkshopEmail.scheduled_time = '00:00:00'
        elif not savedWorkshopEmail.scheduled_date and savedWorkshopEmail.scheduled_time:
          savedWorkshopEmail.scheduled_time = None
        savedWorkshopEmail.save()

        if send_email:
          workshopEmailSend(request, workshop_id, savedWorkshopEmail.id)
        else:
          if savedWorkshopEmail.scheduled_date:
            if savedWorkshopEmail.scheduled_time:
              messages.success(request, "Workshop Email scheduled for %s %s CST" % (savedWorkshopEmail.scheduled_date.strftime('%b %d, %Y'), savedWorkshopEmail.scheduled_time.strftime('%I:%M %p')))
            else:
              messages.success(request, "Workshop Email scheduled for %s 12:00 AM CST" % (savedWorkshopEmail.scheduled_date))
          else:
            messages.success(request, "Workshop Email saved")

        response_data['success'] = True
      else:
        print(form.errors)
        messages.error(request, 'Workshop Email could not be saved')
        context = {'form': form, 'workshop': workshop}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/WorkshopEmailEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.Workshop.DoesNotExist:
    messages.success(request, "Workshop not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.WorkshopEmail.DoesNotExist:
    messages.success(request, "Workshop Email not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

################################################
# DELETE WORKSHOP EMAILS
################################################
def workshopEmailDelete(request, workshop_id='', id=''):
  """
  workshopEmailDelete is called from the path 'workshop/<id>/emails'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :param id='': id of workshop email
  :returns: rendered template 'bcse_app/WorkshopEmails.html with remaining workshop emails
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to registrant not belonging to workshop
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete workshop email')

    if '' != id:
      workshop_email = models.WorkshopEmail.objects.get(id=id)
      if workshop_email.email_status == 'D':
        workshop_email.delete()
        messages.success(request, 'Workshop Email with id %s deleted' % id)
      else:
        messages.error(request, 'Workshop Email has already been sent and cannot be deleted')

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.WorkshopEmail.DoesNotExist:
    messages.success(request, "Workshop Email not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

################################################
# PREVIEW WORKSHOP EMAIL TODO
################################################
def workshopEmailPreview(request, workshop_id='', id=''):
  """
  workshopEmailPreview is called from the path 'workshop/<id>/emails'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :param id='': id of workshop email
  :returns: rendered template 'bcse_app/WorkshopEmails.html with remaining workshop emails
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to registrant not belonging to workshop
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to preview workshop email')

    if '' != id:
      workshop_email = models.WorkshopEmail.objects.get(id=id)
      workshop = models.Workshop.objects.get(id=workshop_id)
      if workshop_email.workshop.id != workshop.id:
        raise CustomException('The workshop email does not belong to the workshop')

      domain = request.get_host()

      subject = workshop_email.email_subject
      subject = models.replace_workshop_tokens(subject, workshop)

      if domain != 'bcse.northwestern.edu':
        subject = '***** TEST **** '+ subject + ' ***** TEST **** '

      email_body = workshop_email.email_message
      email_body = models.replace_workshop_tokens(email_body, workshop)

      context = {'email_body': email_body, 'subject': subject}

      return render(request, 'bcse_app/WorkshopEmailView.html', context)

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.WorkshopEmail.DoesNotExist:
    messages.success(request, "Workshop Email not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))



################################################
# SEND WORKSHOP EMAIL
################################################
def workshopEmailSend(request, workshop_id='', id=''):
  """
  workshopEmailSend is called from the path 'workshop/<id>/emails'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :param id='': id of workshop email
  :returns: rendered template 'bcse_app/WorkshopEmails.html with remaining workshop emails
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to registrant not belonging to workshop
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to preview workshop email')

    if '' != id:
      workshop_email = models.WorkshopEmail.objects.get(id=id)
      workshop = models.Workshop.objects.get(id=workshop_id)
      if workshop_email.workshop.id != workshop.id:
        raise CustomException('The workshop email does not belong to the workshop')

      message = send_workshop_email(id, False)
      if message[0]:
        messages.success(request, message[1])
      else:
        messages.error(request, message[1])

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.WorkshopEmail.DoesNotExist:
    messages.success(request, "Workshop Email not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


################################################
# COPY WORKSHOP EMAIL TODO
################################################
def workshopEmailCopy(request, workshop_id='', id=''):
  """
  workshopEmailCopy is called from the path 'workshop/<id>/emails'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :param id='': id of workshop email
  :returns: rendered template 'bcse_app/WorkshopEmails.html with remaining workshop emails
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to registrant not belonging to workshop
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to preview workshop email')

    if '' != id:
      workshop_email = models.WorkshopEmail.objects.get(id=id)
      workshop_email.pk = None
      workshop_email.id = None
      workshop_email.email_status = 'D'
      workshop_email.scheduled_date = None
      workshop_email.scheduled_time = None
      workshop_email.sent_date = None
      workshop_email.registration_email_addresses = None
      workshop_email.created_date = datetime.datetime.now()
      workshop_email.modified_date = datetime.datetime.now()
      workshop_email.save()

      messages.success(request, "Workshop Email with id %s copied" % id)

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.WorkshopEmail.DoesNotExist:
    messages.success(request, "Workshop Email not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

################################################
# WORKSHOP EMAILS
################################################
def workshopEmails(request, workshop_id=''):
  """
  workshopEmails is called from the path 'workshop/edit'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :param id='': id of workshop email
  :returns: rendered template 'bcse_app/WorkshopEmails.html, HTML view of workshop emails or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to registrant not belonging to workshop
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view workshop email')

    if request.method == 'GET':
      workshop = models.Workshop.objects.get(id=workshop_id)
      workshop_emails = models.WorkshopEmail.objects.all().filter(workshop__id=workshop_id)
      context = {'workshop': workshop, 'workshop_emails': workshop_emails}
      return render(request, 'bcse_app/WorkshopEmails.html', context)

    return http.HttpResponseNotAllowed(['GET'])

  except models.Workshop.DoesNotExist:
    messages.success(request, "Workshop not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.WorkshopEmail.DoesNotExist:
    messages.success(request, "Workshop Email not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

################################################
# WORKSHOP REGISTRATION EMAILS
################################################
def workshopRegistrationEmails(request, workshop_id=''):
  """
  workshopRegistrationEmails is called from the path 'workshop/edit'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :returns: rendered template 'bcse_app/WorkshopRegistrationEmails.html, HTML view of workshop emails or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to registrant not belonging to workshop
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view workshop email')

    if request.method == 'GET':
      workshop = models.Workshop.objects.get(id=workshop_id)
      registration_emails = models.WorkshopRegistrationEmail.objects.all().filter(workshop__id=workshop_id).annotate(
        trigger=Case(
            When(registration_status='R', then=Value('When a user registers for a workshop scheduled for a future date and the workshop has capacity.')),
            When(registration_status='A', then=Value('When a user applies to a workshop scheduled for a future date.')),
            When(registration_status='C', then=Value('When a user\'s application is accepted by an admin and the workshop is scheduled for a future date.')),
            When(registration_status='D', then=Value('When a user\'s application is denied by an admin and the workshop is scheduled for a future date.')),
            When(registration_status='N', then=Value('When a user\'s application or registration is denied by an admin and the workshop is scheduled for a future date.')),
            When(registration_status='W', then=Value('When a user attempts to register for a workshop that is full or when an admin moves an existing registration to waitlist.  In both cases the workshop is scheduled for a future date ')),
            When(registration_status='P', then=Value('When an admin moves an existing registration or application to pending status and the workshop is scheduled for a future date. ')),
            default=Value('Registration email should not be created for this status'),
            output_field=CharField(),
          ))

      generic_registration_emails = get_registration_emails(request)
      context = {'workshop': workshop, 'registration_emails': registration_emails, 'generic_registration_emails': generic_registration_emails}
      messages.success(request, 'These automated registration emails are sent when users apply/register to/for this workshop. <br> You can only create one email message per registration status.')
      return render(request, 'bcse_app/WorkshopRegistrationEmails.html', context)

    return http.HttpResponseNotAllowed(['GET'])

  except models.Workshop.DoesNotExist:
    messages.success(request, "Workshop not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.WorkshopRegistrationEmail.DoesNotExist:
    messages.success(request, "Workshop Registration Email not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################################
# EDIT WORKSHOP REGISTRATION EMAIL
####################################################
@login_required
def workshopRegistrationEmailEdit(request, id='', workshop_id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit workshop registration email')

    workshop = models.Workshop.objects.get(id=workshop_id)

    if '' != id:
      registration_email = models.WorkshopRegistrationEmail.objects.get(id=id)
    else:
      registration_email = models.WorkshopRegistrationEmail(workshop=workshop)

    if request.method == 'GET':
      form = forms.WorkshopRegistrationEmailForm(instance=registration_email)
      context = {'form': form, 'workshop': workshop}
      return render(request, 'bcse_app/WorkshopRegistrationEmailEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.WorkshopRegistrationEmailForm(data, files=request.FILES, instance=registration_email)
      response_data = {}
      if form.is_valid():
        savedMessage = form.save()
        messages.success(request, "Workshop Registration email saved")
        response_data['success'] = True
      else:
        print(form.errors)
        messages.error(request, "Workshop Registration email could not be saved. Check the errors below.")
        context = {'form': form, 'workshop': workshop}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/WorkshopRegistrationEmailEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.Workshop.DoesNotExist:
    messages.error(request, 'Workshop does not exist')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.WorkshopRegistrationEmail.DoesNotExist:
    messages.error(request, 'Workshop Registration Email does not exist')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################################
# DELETE WORKSHOP REGISTRATION EMAIL
####################################################
@login_required
def workshopRegistrationEmailDelete(request, id='', workshop_id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete workshop registration email')
    if '' != id:
      registration_email = models.WorkshopRegistrationEmail.objects.get(id=id)
      if registration_email.workshop.id != workshop_id:
        raise CustomException('This email id does not belong to the workshop')

      registration_email.delete()
      messages.success(request, "Workshop Registration email with id %s deleted" % id)

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except WorkshopRegistrationEmail.DoesNotExist:
    messages.error(request, 'Workshop Registration Email not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


################################################
# PREVIEW WORKSHOP REGISTRATION EMAIL
################################################
def workshopRegistrationEmailPreview(request, id='', workshop_id=''):
  """
  workshopRegistrationEmailPreview is called from the path 'workshop/<workshop_id>/emails/'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :param id='': id of workshop registration email
  :returns: rendered template 'bcse_app/WorkshopRegistrationEmailPreview.html
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises CustomException: redirects user to page they were on before encountering error due to registrant not belonging to workshop
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to preview workshop registration email')

    if '' != id:
      workshop_registration_email = models.WorkshopRegistrationEmail.objects.get(id=id)
      workshop = models.Workshop.objects.get(id=workshop_id)
      if workshop_registration_email.workshop.id != workshop.id:
        raise CustomException('The workshop registration email does not belong to the workshop')

      domain = request.get_host()

      subject = workshop_registration_email.email_subject
      subject = models.replace_workshop_tokens(subject, workshop)

      if domain != 'bcse.northwestern.edu':
        subject = '***** TEST **** '+ subject + ' ***** TEST **** '

      email_body = workshop_registration_email.email_message
      email_body = models.replace_workshop_tokens(email_body, workshop)

      context = {'email_body': email_body, 'subject': subject}

      return render(request, 'bcse_app/WorkshopEmailView.html', context)

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.WorkshopRegistrationEmail.DoesNotExist:
    messages.success(request, "Workshop Registration Email not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except models.Workshop.DoesNotExist:
    messages.success(request, "Workshop not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


def userRegistration(request, workshop_id, user_id):
  """
  userRegistration is called from the path 'workshops/edit'
  :param request: request from the browser
  :param workshop_id='': id of workshop
  :param user_id='': id of workshop
  :returns: registration status
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission check registration')
    else:
      workshop = models.Workshop.objects.get(id=workshop_id)
      registration = models.Registration.objects.all().filter(workshop_registration_setting__workshop__id=workshop.id, user__id=user_id).first()
      return registration

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
# GET USER WORKPLACE
################################################
def userProfileWorkPlace(request, id):
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to get user workplace')
    elif request.user.userProfile.user_role in ['T', 'P'] and request.user.userProfile.id != id:
      raise CustomException('You do not have the permission to get this user''s workplace')

    user = models.UserProfile.objects.get(id=id)
    if request.method == 'GET':
      if user.work_place:
        work_place_id = str(user.work_place.id)
        work_place_name = user.work_place.name
      else:
        work_place_id = work_place_name = None
      response_data = {'success': True, 'work_place_id': work_place_id, 'work_place_name': work_place_name}
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  except CustomException as ce:
    response_data = {'success': False, 'message': ce}
    return http.HttpResponse(json.dumps(response_data), content_type="application/json")

################################################
# WORKSHOPS BASE QUERY BEFORE APPLYING FILTERS
################################################
def workshopsBaseQuery(request, extra='', user_id=''):
  """
  workshopsBaseQuery is called from the path 'workshops/list'
  :param request: request from the browser
  :param extra: extra parameter [my or teacher]
  :param user_id='': id of the user to get their registered workshops or teacher leader workshops
  :returns: workshop base query
  """
  workshops = None
  if request.user.is_authenticated:
    #for admins
    if request.user.userProfile.user_role in ['A', 'S']:
      #fetch user workshops to display on user profile
      if user_id:
        workshops = models.Workshop.objects.all().filter(Q(registration_setting__workshop_registrants__user__id=user_id))
      #fetch all workshops to display on workshops page
      else:
        workshops = models.Workshop.objects.all()
    #for non-admins
    else:
      #fetch my workshops
      if extra =='my' or request.user.userProfile.id == user_id:
        workshops = models.Workshop.objects.all().filter(Q(registration_setting__workshop_registrants__user=request.user.userProfile))
      #fetch teacher leader workshops
      elif extra == 'teacher':
        workshops = models.Workshop.objects.all().filter(teacher_leaders__teacher=request.user.userProfile)
      #fetch all active workshops
      else:
        workshops = models.Workshop.objects.all().filter(status='A', workshop_category__status='A')
  #for public, fetch all active workshops
  else:
    workshops = models.Workshop.objects.all().filter(status='A', workshop_category__status='A')

  workshops = workshops.order_by('start_date', 'start_time')
  return workshops

################################################
# VIEW WORKSHOPS
################################################
def workshops(request, display='list', period='current', extra=''):
  """
  workshops is called from the path 'workshops/list'
  :param request: request from the browser
  :param display: display type [list or table]
  :param period: workshop period [current, previous or all]
  :param extra: extra parameter [my, teacher]
  :returns: rendered template 'bcse_app/WorkshopsPublicBaseView.html' or rendered template 'bcse_app/WorkshopsAdminBaseView.html'
  """
  if request.session.get('workshops_search_%s_%s'%(period, extra), False):
    searchForm = forms.WorkshopsSearchForm(user=request.user, initials=request.session['workshops_search_%s_%s'%(period, extra)], prefix="workshop_search")
    page = request.session['workshops_search_%s_%s'%(period, extra)]['page']
  else:
    searchForm = forms.WorkshopsSearchForm(user=request.user, initials=None, prefix="workshop_search")
    page = 1

  context = {'searchForm': searchForm, 'display': display, 'period': period, 'extra': extra, 'page': page}
  if request.user.is_authenticated and request.user.userProfile.user_role in ['A', 'S']:
    return render(request, 'bcse_app/WorkshopsAdminBaseView.html', context)
  else:
    return render(request, 'bcse_app/WorkshopsPublicBaseView.html', context)

##########################################################
# FILTER WORKSHOP BASE QUERY BASED ON FILTER CRITERIA
##########################################################
def workshopsSearch(request, display='list', period='current', extra=''):
  """
  workshopsSearch is called from the path 'workshops/list'
  :param request: request from the browser
  :param display: display type [list or table]
  :param period: workshop period [current, previous or all]
  :param extra: extra parameter [my, teacher]
  :returns: JSON view of workshops with filter applied or error page
  """
  workshops = workshopsBaseQuery(request, extra)

  if request.method == 'GET':

    query_filter = Q()
    keyword_filter = None
    workshop_category_filter = None
    starts_after_filter = None
    ends_before_filter = None
    registration_filter = None
    cancelled_filter = None
    status_filter = None
    tags_filter = None
    filters_applied = False

    keywords = request.GET.get('workshop_search-keywords', '')
    starts_after = request.GET.get('workshop_search-starts_after', '')
    ends_before = request.GET.get('workshop_search-ends_before', '')
    registration_open = request.GET.get('workshop_search-registration_open', '')
    cancelled = request.GET.get('workshop_search-cancelled', '')
    workshop_category = request.GET.get('workshop_search-workshop_category', '')
    status = request.GET.get('workshop_search-status', '')
    sort_by = request.GET.get('workshop_search-sort_by', '')
    rows_per_page = request.GET.get('workshop_search-rows_per_page', settings.DEFAULT_ITEMS_PER_PAGE)
    page = request.GET.get('page', '')

    #set session variable
    workshop_search_vars = {
      'keywords': keywords,
      'starts_after': starts_after,
      'ends_before': ends_before,
      'registration_open': registration_open,
      'cancelled': cancelled,
      'workshop_category': workshop_category,
      'status': status,
      'sort_by': sort_by,
      'rows_per_page': rows_per_page,
      'page': page
    }

    tags = []
    for tag in models.Tag.objects.all().filter(status='A'):
      sub_tags = request.GET.getlist('workshop_search-tag_%s'%tag.id, '')
      if sub_tags:
        workshop_search_vars['tag_'+str(tag.id)] = sub_tags
        tags.append(sub_tags)

    request.session['workshops_search_%s_%s'%(period, extra)] = workshop_search_vars

    if keywords:
      keyword_filter = Q(name__icontains=keywords) | Q(sub_title__icontains=keywords)
      keyword_filter = keyword_filter | Q(workshop_category__name__icontains=keywords)
      keyword_filter = keyword_filter | Q(teacher_leaders__teacher__user__first_name__icontains=keywords)
      keyword_filter = keyword_filter | Q(teacher_leaders__teacher__user__last_name__icontains=keywords)
      keyword_filter = keyword_filter | Q(summary__icontains=keywords)
      keyword_filter = keyword_filter | Q(description__icontains=keywords)
      keyword_filter = keyword_filter | Q(location__icontains=keywords)

    if workshop_category:
      workshop_category_filter = Q(workshop_category__id=workshop_category)

    if status:
      status_filter = Q(status=status)

    if cancelled:
      cancelled_filter = Q(cancelled=cancelled)

    if starts_after:
      starts_after = datetime.datetime.strptime(starts_after, '%B %d, %Y')
      starts_after_filter = Q(start_date__gte=starts_after)

    if ends_before:
      ends_before = datetime.datetime.strptime(ends_before, '%B %d, %Y')
      ends_before_filter = Q(end_date__lte=ends_before)

    if tags:
      tags_filter = Q()
      for sub_tags in tags:
        tags_filter = tags_filter & Q(tags__id__in=sub_tags)


    if keyword_filter:
      query_filter = keyword_filter
      filters_applied = True
    if status_filter:
      query_filter = query_filter & status_filter
      filters_applied = True
    if cancelled_filter:
      query_filter = query_filter & cancelled_filter
      filters_applied = True
    if workshop_category_filter:
      query_filter = query_filter & workshop_category_filter
      filters_applied = True
    if starts_after_filter:
      query_filter = query_filter & starts_after_filter
      filters_applied = True
    if ends_before_filter:
      query_filter = query_filter & ends_before_filter
      filters_applied = True
    if tags_filter:
      query_filter = query_filter & tags_filter
      filters_applied = True

    workshops = workshops.filter(query_filter)
    if registration_open != '':
      workshops_with_open_registration = []
      for workshop in workshops:
        registration_setting_status = workshopRegistrationSettingStatus(workshop)
        if str(registration_setting_status['registration_open']) == registration_open:
          workshops_with_open_registration.append(workshop.id)

      workshops = workshops.filter(id__in=workshops_with_open_registration)
      filters_applied = True

    if period == 'current':
      if not request.user.is_authenticated or not request.user.userProfile.user_role in 'AS':
        workshops = workshops.filter(featured=False)
    elif period == 'previous':
      workshops = workshops.filter(featured=True)

    workshops = workshops.distinct()

    order_by = 'start_date'
    direction = request.GET.get('direction') or 'desc'
    ignorecase = request.GET.get('ignorecase') or 'false'
    if sort_by:
      if sort_by == 'title':
        order_by = 'name'
        direction = 'asc'
        ignorecase = 'true'
      elif sort_by == 'start_date_desc':
        order_by = 'start_date'
        direction = 'desc'
        ignorecase = 'false'
      elif sort_by == 'start_date_asc':
        order_by = 'start_date'
        direction = 'asc'
        ignorecase = 'false'
      elif sort_by == 'created_date_desc':
        order_by = 'created_date'
        direction = 'desc'
        ignorecase = 'false'
      elif sort_by == 'created_date_asc':
        order_by = 'created_date'
        direction = 'asc'
        ignorecase = 'false'


    sort_order = [{'order_by': order_by, 'direction': direction, 'ignorecase': ignorecase}]
    workshops = paginate(request, workshops, sort_order, rows_per_page, page)

    context = {'workshops': workshops, 'tag': 'workshops', 'display': display, 'period': period, 'extra': extra, 'filters_applied': filters_applied}
    response_data = {}
    response_data['success'] = True
    if display == 'list':
      response_data['html'] = render_to_string('bcse_app/WorkshopsListView.html', context, request)
    else:
      response_data['html'] = render_to_string('bcse_app/WorkshopsTableView.html', context, request)

    return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  return http.HttpResponseNotAllowed(['GET'])


##########################################################
# WORKSHOP REGISTRATION SETTING
##########################################################
def workshopRegistrationSetting(request, id=''):
  """
  workshopsSearch is called from the path 'workshops/list'
  :param request: request from the browser
  :param id='': id of workshop
  :returns: redirects page user was on before, redirects to view of workshop settings, rendered template 'bcse_app/WorkshopRegistrationSetting.html' or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
# LIST OF SINGLE WORKSHOP REGISTRANTS
##########################################################
def workshopRegistrants(request, id=''):
  """
  workshopsSearch is called from the path 'workshops/list'
  :param request: request from the browser
  :param id='': id of workshop
  :returns: rendered template 'bcse_app/WorkshopAdminRegistrants.html', rendered template 'bcse_app/WorkshopFacilitatorRegistrants.html'  or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises models.Workshop.DoesNotExist: redirects user to page they were on before encountering error due to workshop not existing
  """
  try:

    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to view workshop registrants')

    if request.method == 'GET':
      if '' != id:
        workshop = models.Workshop.objects.get(id=id)
        if request.user.userProfile.user_role not in  ['A', 'S']:
          if models.TeacherLeader.objects.all().filter(teacher=request.user.userProfile, id__in=workshop.teacher_leaders.all()).count() == 0:
            raise CustomException('You do not have the permission to view workshop registrants')

        workshop_registration_setting, created = models.WorkshopRegistrationSetting.objects.get_or_create(workshop=workshop)

        if request.session.get('workshop_%s_registrants_search'%id, False):
          searchForm = forms.WorkshopRegistrantsSearchForm(user=request.user, initials=request.session['workshop_%s_registrants_search'%id], prefix="registrant_search")
          page = request.session['workshop_%s_registrants_search'%id]['page']
        else:
          searchForm = forms.WorkshopRegistrantsSearchForm(user=request.user, initials=None, prefix="registrant_search")
          page = 1

        context = {'workshop': workshop,'searchForm': searchForm, 'page': page}
        if request.user.is_authenticated and request.user.userProfile.user_role in ['A', 'S']:
          return render(request, 'bcse_app/WorkshopAdminRegistrants.html', context)
        else:
          return render(request, 'bcse_app/WorkshopFacilitatorRegistrants.html', context)

      else:
        raise models.Workshop.DoesNotExist

    return http.HttpResponseNotAllowed(['GET'])

  except models.Workshop.DoesNotExist:
    messages.error(request, 'Workshop not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# SEARCH SINGLE WORKSHOP REGISTRANTS
##########################################################
def workshopRegistrantsSearch(request, id=''):
  """
  workshopsSearch is called from the path 'workshops/list'
  :param request: request from the browser
  :param id='': id of workshop
  :returns: JSON view of single workshop registrants or error page
  """
  try:
    if request.method == 'GET':

      workshop = models.Workshop.objects.get(id=id)

      query_filter = Q()
      email_filter = None
      first_name_filter = None
      last_name_filter = None
      user_role_filter = None
      work_place_filter = None
      registration_status_filter = None
      registration_sub_status_filter = None
      subscribed_filter = None
      photo_release_filter = None

      email = request.GET.get('registrant_search-email', '')
      first_name = request.GET.get('registrant_search-first_name', '')
      last_name = request.GET.get('registrant_search-last_name', '')
      user_role = request.GET.get('registrant_search-user_role', '')
      work_place = request.GET.get('registrant_search-work_place', '')
      registration_status = request.GET.getlist('registrant_search-registration_status', '')
      registration_sub_status = request.GET.getlist('registrant_search-registration_sub_status', '')
      subscribed = request.GET.get('registrant_search-subscribed', '')
      photo_release_complete = request.GET.get('registrant_search-photo_release_complete', '')
      sort_by = request.GET.get('registrant_search-sort_by', '')
      rows_per_page = request.GET.get('registrant_search-rows_per_page', settings.DEFAULT_ITEMS_PER_PAGE)
      page = request.GET.get('page' '')

      request.session['workshop_%s_registrants_search'%id] = {
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'user_role': user_role,
        'work_place': work_place,
        'registration_status': registration_status,
        'registration_sub_status': registration_sub_status,
        'subscribed': subscribed,
        'photo_release_complete': photo_release_complete,
        'sort_by': sort_by,
        'rows_per_page': rows_per_page,
        'page': page
      }

      if email:
        email_filter = Q(Q(user__user__email__icontains=email) | Q(user__secondary_email__icontains=email))
        query_filter = query_filter & email_filter

      if first_name:
        first_name_filter = Q(user__user__first_name__icontains=first_name)
        query_filter = query_filter & first_name_filter
      if last_name:
        last_name_filter = Q(user__user__last_name__icontains=last_name)
        query_filter = query_filter & last_name_filter

      if user_role:
        user_role_filter = Q(user__user_role=user_role)
        query_filter = query_filter & user_role_filter

      if work_place:
        work_place_filter = Q(registration_to_work_place__work_place=work_place)
        query_filter = query_filter & work_place_filter

      if subscribed:
        if subscribed == 'Y':
          subscribed_filter = Q(user__subscribe=True)
        else:
          subscribed_filter = Q(user__subscribe=False)

        query_filter = query_filter & subscribed_filter

      if photo_release_complete:
        if photo_release_complete == 'Y':
          photo_release_filter = Q(user__photo_release_complete=True)
        else:
          photo_release_filter = Q(user__photo_release_complete=False)

        query_filter = query_filter & photo_release_filter

      if registration_status:
        registration_status_filter = Q(status__in=registration_status)
        query_filter = query_filter & registration_status_filter

      if registration_sub_status:
        registration_sub_status_filter = Q(sub_status__in=registration_sub_status)
        query_filter = query_filter & registration_sub_status_filter

      registrations = models.Registration.objects.all().filter(workshop_registration_setting__workshop__id=id)
      registrations = registrations.filter(query_filter)

      direction = request.GET.get('direction') or 'asc'
      ignorecase = request.GET.get('ignorecase') or 'false'

      if sort_by:
        if sort_by == 'email':
          order_by = 'user__user__email'
        elif sort_by == 'first_name':
          order_by = 'user__user__first_name'
        elif sort_by == 'last_name':
          order_by = 'user__user__last_name'
        elif sort_by == 'created_date_desc':
          order_by = 'created_date'
          direction = 'desc'
        elif sort_by == 'created_date_asc':
          order_by = 'created_date'
          direction = 'asc'
      else:
        order_by = 'created_date'

      sort_order = [{'order_by': order_by, 'direction': direction, 'ignorecase': ignorecase}]

      registrations = paginate(request, registrations, sort_order, rows_per_page, page)

      context = {'workshop': workshop, 'registrations': registrations}
      response_data = {}
      response_data['success'] = True
      response_data['html'] = render_to_string('bcse_app/WorkshopRegistrantsTableView.html', context, request)
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

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
  """
  workshopsSearch is called from the path 'workshops/list'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/WorkshopsRegistrants.html', to view all registrants across all workshops
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in  ['A', 'S'] :
      raise CustomException('You do not have the permission to view workshop registrants')

    if request.session.get('workshops_registrants_search', False):
      searchForm = forms.WorkshopsRegistrantsSearchForm(user=request.user, initials=request.session['workshops_registrants_search'], prefix="registrants_search")
      page = request.session['workshops_registrants_search']['page']
    else:
      searchForm = forms.WorkshopsRegistrantsSearchForm(user=request.user, initials=None, prefix="registrants_search")
      page = 1

    context = {'searchForm': searchForm, 'page': page}
    return render(request, 'bcse_app/WorkshopsRegistrants.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# SEARCH REGISTRANTS ACROSS ALL WORKSHOPS
##########################################################
def workshopsRegistrantsSearch(request):
  """
  workshopsRegistrantsSearch is called from the path 'workshops/list'
  :param request: request from the browser
  :returns: JSON view of registrants who match search criteria or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:

    if request.user.is_anonymous or request.user.userProfile.user_role not in  ['A', 'S'] :
      raise CustomException('You do not have the permission to view workshop registrants')

    if request.method == 'GET':

      query_filter = Q(workshop_registration_setting__workshop__cancelled=False)

      workshop_category = [int(i) for i in request.GET.getlist('registrants_search-workshop_category', '')]
      workshop = [int(i) for i in request.GET.getlist('registrants_search-workshop', '')]
      work_place = [int(i) for i in request.GET.getlist('registrants_search-work_place', '')]
      user = [int(i) for i in request.GET.getlist('registrants_search-user', '')]
      user_role = request.GET.getlist('registrants_search-user_role', '')
      year = request.GET.get('registrants_search-year', '')
      starts_after = request.GET.get('registrants_search-starts_after', '')
      ends_before = request.GET.get('registrants_search-ends_before', '')
      status = request.GET.getlist('registrants_search-status', '')
      sub_status = request.GET.getlist('registrants_search-sub_status', '')
      keywords = request.GET.get('registrants_search-keywords', '')
      sort_by = request.GET.get('registrants_search-sort_by', '')
      rows_per_page = request.GET.get('registrants_search-rows_per_page', settings.DEFAULT_ITEMS_PER_PAGE)
      page = request.GET.get('page', '')


      registrants_search_vars = {
        'workshop_category': workshop_category,
        'workshop': workshop,
        'work_place': work_place,
        'user': user,
        'user_role': user_role,
        'starts_after': starts_after,
        'ends_before': ends_before,
        'year': year,
        'status': status,
        'sub_status': sub_status,
        'keywords': keywords,
        'sort_by': sort_by,
        'rows_per_page': rows_per_page,
        'page': page
      }

      tags = []
      for tag in models.Tag.objects.all().filter(status='A'):
        sub_tags = request.GET.getlist('registrants_search-tag_%s'%tag.id, '')
        if sub_tags:
          registrants_search_vars['tag_'+str(tag.id)] = sub_tags
          tags.append(sub_tags)

      request.session['workshops_registrants_search'] = registrants_search_vars

      if workshop_category:
        workshop_category_filter = Q(workshop_registration_setting__workshop__workshop_category__id__in=workshop_category)
        query_filter = query_filter & workshop_category_filter
      if workshop:
        workshop_filter = Q(workshop_registration_setting__workshop__id__in=workshop)
        query_filter = query_filter & workshop_filter
      if work_place:
        workplace_filter = Q(registration_to_work_place__work_place__id__in=work_place)
        query_filter = query_filter & workplace_filter

      if user:
        user_filter = Q(user__id__in=user)
        query_filter = query_filter & user_filter

      if user_role:
        user_role_filter = Q(user__user_role__in=user_role)
        query_filter = query_filter & user_role_filter


      if year:
        year_filter = Q(workshop_registration_setting__workshop__start_date__year=int(year))
        query_filter = query_filter & year_filter
      if status:
        status_filter  = Q(status__in=status)
        query_filter = query_filter & status_filter

      if sub_status:
        sub_status_filter  = Q(sub_status__in=sub_status)
        query_filter = query_filter & sub_status_filter

      if starts_after:
        starts_after = datetime.datetime.strptime(starts_after, '%B %d, %Y')
        starts_after_filter = Q(workshop_registration_setting__workshop__start_date__gte=starts_after)
        query_filter = query_filter & starts_after_filter

      if ends_before:
        ends_before = datetime.datetime.strptime(ends_before, '%B %d, %Y')
        ends_before_filter = Q(workshop_registration_setting__workshop__end_date__lte=ends_before)
        query_filter = query_filter & ends_before_filter

      if tags:
        tags_filter = Q()
        for sub_tags in tags:
          tags_filter = tags_filter & Q(workshop_registration_setting__workshop__tags__id__in=sub_tags)

        query_filter = query_filter & tags_filter

      if keywords:
        keyword_filter = Q(workshop_registration_setting__workshop__name__icontains=keywords) | Q(workshop_registration_setting__workshop__sub_title__icontains=keywords)
        keyword_filter = keyword_filter | Q(workshop_registration_setting__workshop__workshop_category__name__icontains=keywords)
        keyword_filter = keyword_filter | Q(workshop_registration_setting__workshop__teacher_leaders__teacher__user__first_name__icontains=keywords)
        keyword_filter = keyword_filter | Q(workshop_registration_setting__workshop__teacher_leaders__teacher__user__last_name__icontains=keywords)
        keyword_filter = keyword_filter | Q(workshop_registration_setting__workshop__summary__icontains=keywords)
        keyword_filter = keyword_filter | Q(workshop_registration_setting__workshop__description__icontains=keywords)
        keyword_filter = keyword_filter | Q(workshop_registration_setting__workshop__location__icontains=keywords)

        query_filter = query_filter & keyword_filter

      # Convert the choices into a list of When cases
      when_cases = [When(status=key, then=Value(value)) for key, value in models.WORKSHOP_REGISTRATION_STATUS_CHOICES]

      # Default case if none of the choices match
      default_case = Value('Unknown')

      registrations = models.Registration.objects.all().annotate(
        status_display=Case(
            *when_cases,
            default=default_case,
            output_field=CharField(),
        )).filter(query_filter).distinct()

      all_registration_summary = {
        '# of Workshops': len(list(set(list(registrations.values_list('workshop_registration_setting__workshop__id', flat=True))))),
        '# of Unique Workplaces': len(list(set(list(registrations.exclude(registration_to_work_place=None).values_list('registration_to_work_place__work_place__id', flat=True))))),
        '# of Unique Registrants': len(list(set(list(registrations.values_list('user__id', flat=True))))),
      }

      status_breakdown = {}
      attended_breakdown = {}
      for registrant in registrations:
        status = registrant.get_status_display()
        if status in status_breakdown:
          status_breakdown[status] += 1
        else:
          status_breakdown[status] = 1

        if status == 'Attended':
          sub_status = registrant.get_sub_status_display()
          if sub_status in attended_breakdown:
            attended_breakdown[sub_status] += 1
          else:
            attended_breakdown[sub_status] = 1

      keys = list(status_breakdown.keys())
      keys.sort()
      status_breakdown = {i: status_breakdown[i] for i in keys}
      all_registration_summary.update(status_breakdown)

      keys = list(attended_breakdown.keys())
      keys.sort()
      attended_summary = {i: attended_breakdown[i] for i in keys}

      workshops = models.Workshop.objects.all().annotate(
        total_registrants=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations), distinct=True),
        total_workplaces=Count('registration_setting__workshop_registrants__registration_to_work_place__work_place__id', filter=Q(registration_setting__workshop_registrants__in=registrations), distinct=True),
        reg_accepted=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='C'), distinct=True),
        reg_applied=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='A'), distinct=True),
        reg_attended=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='T'), distinct=True),

        reg_attended_participant=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='T', registration_setting__workshop_registrants__sub_status='P'), distinct=True),
        reg_attended_facilitator=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='T', registration_setting__workshop_registrants__sub_status='F'), distinct=True),
        reg_attended_staff=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='T', registration_setting__workshop_registrants__sub_status='S'), distinct=True),
        reg_attended_observer=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='T', registration_setting__workshop_registrants__sub_status='O'), distinct=True),

        reg_no_show=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='U'), distinct=True),
        reg_cancelled=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='N'), distinct=True),
        reg_denied=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='D'), distinct=True),
        reg_pending=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='P'), distinct=True),
        reg_registered=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='R'), distinct=True),
        reg_waitlisted=Count('registration_setting__workshop_registrants__id', filter=Q(registration_setting__workshop_registrants__in=registrations, registration_setting__workshop_registrants__status='W'), distinct=True)

        ).filter(id__in=registrations.values_list('workshop_registration_setting__workshop__id', flat=True))

      workplaces = models.WorkPlace.objects.all().annotate(
        total_workshops = Count('work_place_to_registration__registration__workshop_registration_setting__workshop__id', filter=Q(work_place_to_registration__registration__in=registrations), distinct=True),
        total_registrants=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations), distinct=True),
        reg_accepted=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='C'), distinct=True),
        reg_applied=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='A'), distinct=True),
        reg_attended=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='T'), distinct=True),

        reg_attended_participant=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='T', work_place_to_registration__registration__sub_status='P'), distinct=True),
        reg_attended_facilitator=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='T', work_place_to_registration__registration__sub_status='F'), distinct=True),
        reg_attended_staff=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='T', work_place_to_registration__registration__sub_status='S'), distinct=True),
        reg_attended_observer=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='T', work_place_to_registration__registration__sub_status='O'), distinct=True),

        reg_no_show=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='U'), distinct=True),
        reg_cancelled=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='N'), distinct=True),
        reg_denied=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='D'), distinct=True),
        reg_pending=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='P'), distinct=True),
        reg_registered=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='R'), distinct=True),
        reg_waitlisted=Count('work_place_to_registration__registration__id', filter=Q(work_place_to_registration__registration__in=registrations, work_place_to_registration__registration__status='W'), distinct=True)

        ).filter(id__in=registrations.values_list('registration_to_work_place__work_place__id', flat=True))

      users = models.UserProfile.objects.all().annotate(
        total_workshops = Count('registered_workshops__workshop_registration_setting__workshop__id', filter=Q(registered_workshops__in=registrations), distinct=True),
        total_workplaces=Count('registered_workshops__registration_to_work_place__work_place__id', filter=Q(registered_workshops__in=registrations), distinct=True),
        workplaces=ArrayAgg('registered_workshops__registration_to_work_place__work_place__name', filter=Q(Q(registered_workshops__in=registrations), ~Q(registered_workshops__registration_to_work_place__work_place=None)), distinct=True, ordering=F('registered_workshops__registration_to_work_place__work_place__name').asc()),
        reg_accepted=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='C'), distinct=True),
        reg_applied=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='A'), distinct=True),
        reg_attended=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='T'), distinct=True),

        reg_attended_participant=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='T', registered_workshops__sub_status='P'), distinct=True),
        reg_attended_facilitator=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='T', registered_workshops__sub_status='F'), distinct=True),
        reg_attended_staff=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='T', registered_workshops__sub_status='S'), distinct=True),
        reg_attended_observer=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='T', registered_workshops__sub_status='O'), distinct=True),

        reg_no_show=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='U'), distinct=True),
        reg_cancelled=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='N'), distinct=True),
        reg_denied=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='D'), distinct=True),
        reg_pending=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='P'), distinct=True),
        reg_registered=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='R'), distinct=True),
        reg_waitlisted=Count('registered_workshops__id', filter=Q(registered_workshops__in=registrations, registered_workshops__status='W'), distinct=True)

        ).filter(id__in=registrations.values_list('user__id', flat=True))

      direction = request.GET.get('direction') or 'asc'
      ignorecase = request.GET.get('ignorecase') or 'false'

      registrations_sort_order = []
      workshops_sort_order = []
      workplaces_sort_order = []
      users_sort_order = []
      if sort_by:
        if sort_by == 'title':
          registrations_sort_order.append({'order_by': 'workshop_registration_setting__workshop__name', 'direction': 'asc', 'ignorecase': 'true'})
          workshops_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
          workplaces_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
          users_sort_order.append({'order_by': 'user__last_name', 'direction': 'asc', 'ignorecase': 'true'})
          users_sort_order.append({'order_by': 'user__first_name', 'direction': 'asc', 'ignorecase': 'true'})
        elif sort_by == 'start_date':
          registrations_sort_order.append({'order_by': 'workshop_registration_setting__workshop__start_date', 'direction': 'asc', 'ignorecase': 'false'})
          workshops_sort_order.append({'order_by': 'start_date', 'direction': 'asc', 'ignorecase': 'false'})
          workplaces_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
          users_sort_order.append({'order_by': 'user__last_name', 'direction': 'asc', 'ignorecase': 'true'})
          users_sort_order.append({'order_by': 'user__first_name', 'direction': 'asc', 'ignorecase': 'true'})
        elif sort_by == 'status':
          registrations_sort_order.append({'order_by': 'status_display', 'direction': 'asc', 'ignorecase': 'true'})
          workshops_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
          workplaces_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
          users_sort_order.append({'order_by': 'user__last_name', 'direction': 'asc', 'ignorecase': 'true'})
          users_sort_order.append({'order_by': 'user__first_name', 'direction': 'asc', 'ignorecase': 'true'})
        elif sort_by == 'workplace':
          registrations_sort_order.append({'order_by': 'registration_to_work_place__work_place__name', 'direction': 'asc', 'ignorecase': 'true'})
          workshops_sort_order.append({'order_by': 'start_date', 'direction': 'asc', 'ignorecase': 'false'})
          workplaces_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
          users_sort_order.append({'order_by': 'workplaces', 'direction': 'asc', 'ignorecase': 'false'})
        elif sort_by == 'user':
          registrations_sort_order.append({'order_by': 'user__user__last_name', 'direction': 'asc', 'ignorecase': 'true'})
          registrations_sort_order.append({'order_by': 'user__user__first_name', 'direction': 'asc', 'ignorecase': 'true'})
          workshops_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
          workplaces_sort_order.append({'order_by': 'name', 'direction': 'asc', 'ignorecase': 'true'})
          users_sort_order.append({'order_by': 'user__last_name', 'direction': 'asc', 'ignorecase': 'true'})
          users_sort_order.append({'order_by': 'user__first_name', 'direction': 'asc', 'ignorecase': 'true'})
        else:
          registrations_sort_order.append({'order_by': 'workshop_registration_setting__workshop__name', 'direction': 'asc', 'ignorecase': 'true'})
          workshops_sort_order.append({'order_by': 'reg_attended', 'direction': 'desc', 'ignorecase': 'false'})
          workplaces_sort_order.append({'order_by': 'reg_attended', 'direction': 'desc', 'ignorecase': 'false'})
          users_sort_order.append({'order_by': 'reg_attended', 'direction': 'desc', 'ignorecase': 'false'})

      else:
          registrations_sort_order.append({'order_by': 'workshop_registration_setting__workshop__name', 'direction': 'asc', 'ignorecase': 'true'})
          workshops_sort_order.append({'order_by': 'reg_attended', 'direction': 'desc', 'ignorecase': 'false'})
          workplaces_sort_order.append({'order_by': 'reg_attended', 'direction': 'desc', 'ignorecase': 'false'})
          users_sort_order.append({'order_by': 'reg_attended', 'direction': 'desc', 'ignorecase': 'false'})

      registrations_sort_order.append({'order_by': 'created_date', 'direction': 'asc', 'ignorecase': 'false'})
      workshops_sort_order.append({'order_by': 'created_date', 'direction': 'asc', 'ignorecase': 'false'})
      workplaces_sort_order.append({'order_by': 'created_date', 'direction': 'asc', 'ignorecase': 'false'})
      users_sort_order.append({'order_by': 'created_date', 'direction': 'asc', 'ignorecase': 'false'})

      all_registrations = paginate(request, registrations, registrations_sort_order, rows_per_page, page)
      all_workshops = paginate(request, workshops, workshops_sort_order, rows_per_page, page)
      all_workplaces = paginate(request, workplaces, workplaces_sort_order, rows_per_page, page)
      all_users = paginate(request, users, users_sort_order, rows_per_page, page)

      context = {'registrations': all_registrations, 'all_registration_summary': all_registration_summary, 'attended_summary': attended_summary, 'workshops': all_workshops, 'workplaces': all_workplaces, 'users': all_users}
      response_data = {}
      response_data['success'] = True
      response_data['html'] = render_to_string('bcse_app/WorkshopsRegistrantsTableView.html', context, request)
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# UPLOAD WORKSHOPS VIA AN JSON FILE
##########################################################
@login_required
def workshopsUpload(request):
  """
  workshopsUpload is called from the path 'workshops/list'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/WorkshopsUploadModal.html', JSON view of uploaded workshops or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
              registration_type = row['registration_type'] or 'register'
              capacity = row['capacity']
              status = row['status']
              image_url = row['uri']
              if image_url:
                if 'storage-field-preview-image://' in image_url:
                  image_url = image_url.replace('storage-field-preview-image://', 'https://bcoe.s3.amazonaws.com/').replace(' ', '%20')
                elif 'public://' in image_url:
                  image_url = image_url.replace('public://', 'https://bcse.northwestern.edu/sites/default/files/').replace(' ', '%20')

              workshop_category = models.WorkshopCategory.objects.all().filter(name=category).first()
              workshop, created = models.Workshop.objects.get_or_create(nid=nid, workshop_category=workshop_category, name=title, sub_title=sub_title, summary=summary, description=description, start_date=start_date.date(), start_time=start_date.time(), end_date=end_date.date(), end_time=end_date.time(), location=location, enable_registration=True)
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
  """
  userProfileView is called from the path 'users'
  :param request: request from the browser
  :param id='': id of user
  :returns: rendered template 'bcse_app/UserProfileView.html', rendered template 'bcse_app/MyProfileView.html' or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises models.UserProfile.DoesNotExist: redirects user to page they were on before encountering error due to user profile not existing
  """
  try:

    if '' != id:
      userProfile = models.UserProfile.objects.get(id=id)
    else:
      raise models.UserProfile.DoesNotExist

    if request.user.userProfile.user_role not in  ['A', 'S'] and request.user.id != userProfile.user.id:
      raise CustomException('You do not have the permission to view this user profile')

    if request.method == 'GET':
      workshops = workshopsBaseQuery(request, '', id)
      reservations = reservationsList(request, id)
      context = {'userProfile': userProfile, 'workshops': workshops, 'reservations': reservations}

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
  """
  userProfileEdit is called from the path 'users'
  :param request: request from the browser
  :param id='': id of user
  :returns: rendered template 'bcse_app/UserProfileEdit.html', JSON view of edited user profiles or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  :raises models.UserProfile.DoesNotExist: redirects user to page they were on before encountering error due to user profile not existing
  """
  try:
    if '' != id:
      userProfile = models.UserProfile.objects.get(id=id)
      work_place = models.WorkPlace()
    else:
      raise models.UserProfile.DoesNotExist


    if request.user.userProfile.user_role != 'A' and request.user.id != userProfile.user.id:
      raise CustomException('You do not have the permission to edit this user profile')

    if profile_update_required(userProfile):
      update_required = True
    else:
      update_required = False

    redirect_url = request.GET.get('next', '')

    if request.method == 'GET':
      userForm = forms.UserForm(instance=userProfile.user, user=request.user, prefix="user")
      work_place_form = forms.WorkPlaceForm(instance=work_place, user=request.user, prefix='work_place')

      if request.user.userProfile.user_role != 'A' and request.user.userProfile.work_place.status == 'I':
        userProfileForm = forms.UserProfileForm(instance=userProfile, user=request.user, prefix="user_profile", initial={'work_place': None}, update_required=update_required)
      else:
        userProfileForm = forms.UserProfileForm(instance=userProfile, user=request.user, prefix="user_profile", update_required=update_required)

      context = {'userProfileForm': userProfileForm, 'userForm': userForm, 'work_place_form': work_place_form, 'update_required': update_required, 'redirect_url': redirect_url}
      if update_required:
        if userProfile.work_place.id == models.get_placeholder_workplace():
          messages.warning(request, "Your profile is incomplete. <br> Please update your %s workplace below." % ('IEIN and ' if userProfile.user_role == 'T' else ''))
        else:
          messages.warning(request, "Your profile was last updated on %s. <br> Please confirm or update your %s workplace below." % (userProfile.modified_date.strftime('%b %d, %Y'), 'IEIN and ' if userProfile.user_role == 'T' else ''))

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
      secondary_hash = None
      if userProfile.secondary_email:
        secondary_hash = hashlib.md5(userProfile.secondary_email.lower().encode("utf-8")).hexdigest()

      subscribed = userProfile.subscribe
      old_email = userProfile.user.email
      old_secondary_email = userProfile.secondary_email
      old_first_name = userProfile.user.first_name
      old_last_name = userProfile.user.last_name
      old_phone_number = userProfile.phone_number
      old_password = userProfile.user.password

      userForm = forms.UserForm(data, instance=userProfile.user, user=request.user, prefix='user')
      userProfileForm = forms.UserProfileForm(data, files=request.FILES,  instance=userProfile, user=request.user, prefix="user_profile", update_required=update_required)
      work_place_form = forms.WorkPlaceForm(data=request.POST, instance=work_place, user=request.user, prefix='work_place')

      response_data = {}
      has_error = False

      if userForm.is_valid(userProfile.user.id) and userProfileForm.is_valid():

        primary_email = userForm.cleaned_data.get('email')
        secondary_email = userProfileForm.cleaned_data.get('secondary_email')

        if primary_email == secondary_email:
          userProfileForm.add_error('secondary_email', 'Please choose a secondary email different from the primary email.')
          has_error = True
        else:
          savedUser = userForm.save(commit=False)
          savedUserProfile = userProfileForm.save(commit=False)

          new_work_place_flag = userProfileForm.cleaned_data['new_work_place_flag']
          if new_work_place_flag:
            if work_place_form.is_valid():
              #create a new school entry
              new_work_place = work_place_form.save(commit=False)
              new_work_place.save()
              savedUserProfile.work_place = new_work_place
            else:
              print(work_place_form.errors)
              context = {'userProfileForm': userProfileForm, 'userForm': userForm, 'work_place_form': work_place_form, 'update_required': update_required, 'redirect_url': redirect_url}
              if update_required:
                messages.warning(request, "Your profile was last updated on %s. <br> Please confirm or update your workplace below." % userProfile.modified_date.strftime('%b %d, %Y'))

              response_data['success'] = False
              response_data['html'] = render_to_string('bcse_app/UserProfileEdit.html', context, request)
              return http.HttpResponse(json.dumps(response_data), content_type="application/json")

          savedUser.save()
          savedUserProfile.save()


          new_password = savedUserProfile.user.password
          if request.user.id == userProfile.user.id and new_password != old_password:
            update_session_auth_hash(request, userProfile.user)

          userDetails = {'email_address': savedUserProfile.user.email, 'first_name': savedUserProfile.user.first_name, 'last_name': savedUserProfile.user.last_name}
          if secondary_email:
            userSecondaryDetails = {'email_address': savedUserProfile.secondary_email, 'first_name': savedUserProfile.user.first_name, 'last_name': savedUserProfile.user.last_name}

          if savedUserProfile.phone_number:
            userDetails['phone_number'] = savedUserProfile.phone_number
            if secondary_email:
              userSecondaryDetails['phone_number'] = savedUserProfile.phone_number

          #user unsubscribed
          if subscribed and not savedUserProfile.subscribe:
            subscription(userDetails, 'delete', subscriber_hash)
            if secondary_hash:
              subscription(userSecondaryDetails, 'delete', secondary_hash)

          #user subscribed
          elif not subscribed and savedUserProfile.subscribe:
            subscription(userDetails, 'add')
            if secondary_email:
              subscription(userSecondaryDetails, 'add')

          #user stays subscribed but bio changes
          elif subscribed and savedUserProfile.subscribe:
            #user email, secondary email, first name or last name changed
            if old_email != savedUserProfile.user.email or old_secondary_email != savedUserProfile.secondary_email or old_first_name != savedUserProfile.user.first_name or old_last_name != savedUserProfile.user.last_name or old_phone_number != savedUserProfile.phone_number:
              subscription(userDetails, 'update', subscriber_hash)

              if old_secondary_email != savedUserProfile.secondary_email or old_first_name != savedUserProfile.user.first_name or old_last_name != savedUserProfile.user.last_name or old_phone_number != savedUserProfile.phone_number:
                #user removed secondary email
                if old_secondary_email is not None and savedUserProfile.secondary_email is None:
                  userSecondaryDetails = {'email_address': old_secondary_email, 'first_name': savedUserProfile.user.first_name, 'last_name': savedUserProfile.user.last_name}
                  subscription(userSecondaryDetails, 'delete', secondary_hash)
                #user added secondary email
                elif old_secondary_email is None and savedUserProfile.secondary_email is not None:
                  subscription(userSecondaryDetails, 'add')
                #user changed secondary email or other details
                else:
                  subscription(userSecondaryDetails, 'update', secondary_hash)

        messages.success(request, "User profile saved successfully")
        response_data['success'] = True
        response_data['work_place'] = savedUserProfile.work_place.name
        response_data['redirect_url'] =  redirect_url

      else:
        has_error = True


      if has_error:
        print(userForm.errors)
        print(userProfileForm.errors)
        context = {'userProfileForm': userProfileForm, 'userForm': userForm, 'work_place_form': work_place_form, 'update_required': update_required, 'redirect_url': redirect_url}
        if update_required:
          messages.warning(request, "Your profile was last updated on %s. <br> Please confirm or update your workplace below." % userProfile.modified_date.strftime('%b %d, %Y'))

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
  """
  userProfileDelete is called from the path 'users'
  :param request: request from the browser
  :param id='': id of user
  :returns: redirects to page with all user profiles
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete this user')
    if '' != id:
      if id == models.get_placeholder_reservation_assignee():
        messages.error(request, "This user is the default assignee for reservations and cannot be deleted.")
      else:
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
# EMAIL LINK TO SUBSCRIBE USER TO MAILCHIMP
##########################################################
def subscribeFromEmail(request):
  """
  subscribeFromEmail is called from an email link in the footer
  :param request: request from the browser
  :returns: rendered template 'bcse_app/SubscribeModal.html' if user is anonymous, subscription status if user is logged in
  """
  if request.user.is_authenticated:
    return subscribe(request)
  else:
    return http.HttpResponseRedirect('/?next=/subscribe')

##########################################################
# SUBSCRIBE USER TO MAILCHIMP
##########################################################
def subscribe(request):
  """
  subscribe is called from the path 'about/contact'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/SubscribeModal.html', JSON view of subscribed users, page user was on before or error page
  """
  try:
    if request.method == 'GET':
      if request.user.is_authenticated:
        userProfile = models.UserProfile.objects.get(id=request.user.userProfile.id)

        userDetails = {'email_address': userProfile.user.email.lower(), 'first_name':  userProfile.user.first_name, 'last_name':  userProfile.user.last_name}
        if userProfile.phone_number:
          userDetails['phone_number'] = userProfile.phone_number
        subscription(userDetails, 'add')

        if userProfile.subscribe:
          messages.success(request, "You are already subscribed to our mailing list")
        else:
          userProfile.subscribe = True
          userProfile.save()
          messages.success(request, "You have successfully subscribed to our mailing list")

        if request.META.get('HTTP_REFERER'):
          return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
        else:
          return shortcuts.redirect('bcse:home')
      else:
        form = forms.SubscriptionForm(user=request.user)
        context = {'form': form}
        return render(request, 'bcse_app/SubscribeModal.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()

      recaptcha_token = data.get("recaptchaToken")
      recaptcha_passed = validateReCaptcha(recaptcha_token, 'subscribe')

      form = forms.SubscriptionForm(data, user=request.user)
      response_data = {}
      if recaptcha_passed and form.is_valid():
        userDetails = {'email_address': data.__getitem__('email').lower(), 'first_name':  data.__getitem__('first_name'), 'last_name':  data.__getitem__('last_name')}
        if data.__getitem__('phone_number'):
          userDetails['phone_number'] = data.__getitem__('phone_number')
        subscription(userDetails, 'add')

        try:
          userProfile = models.UserProfile.objects.get(Q(user__email=userDetails['email_address']) | Q(secondary_email=userDetails['email_address']))
          userProfile.subscribe = True
          userProfile.save()
        except models.UserProfile.DoesNotExist:
          pass

        messages.success(request, "You have successfully subscribed to our mailing list")
        response_data['success'] = True

      else:
        if not recaptcha_passed:
          messages.error(request, 'reCAPTCHA validation failed')
        print(form.errors)
        context = {'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/SubscribeModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])


    return render(request, 'bcse_app/SubscribeModal.html', context)
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# LIST OF HOMEPAGE BLOCKS
##########################################################
@login_required
def homepageBlocks(request):
  """
  homepageBlocks is called from the path 'adminConfiguration/homepageBlocks'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/HomepageBlocks.html'
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
  """
  homepageBlockEdit is called from the path 'adminConfiguration/homepageBlocks'
  :param request: request from the browser
  :param id='': id of homepage to edit
  :returns: rendered template 'bcse_app/HomepageBlockEdit.html', page with updated homepage or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
  """
  homepageBlockDelete is called from the path 'adminConfiguration/homepageBlocks'
  :param request: request from the browser
  :param id='': id of home page to delete
  :returns: page with remaining homepage blocks
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
# LIST OF STANDALONE PAGES
##########################################################
@login_required
def standalonePages(request):
  """
  standalonePages is called from the path 'adminConfiguration/standalonePages/'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/StandalonePages.html'
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view standalone pages')

    standalone_pages = models.StandalonePage.objects.all()
    context = {'standalone_pages': standalone_pages}
    return render(request, 'bcse_app/StandalonePages.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# EDIT STANDALONE PAGE
##########################################################
@login_required
def standalonePageEdit(request, id=''):
  """
  standalonePageEdit is called from the path 'adminConfiguration/standalonePages'
  :param request: request from the browser
  :param id='': id of standalone page to edit
  :returns: rendered template 'bcse_app/StandalonePageEdit.html', page with updated standalone page or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit standalone page')
    if '' != id:
      standalone_page = models.StandalonePage.objects.get(id=id)
    else:
      standalone_page = models.StandalonePage()

    if request.method == 'GET':
      form = forms.StandalonePageForm(instance=standalone_page)
      context = {'form': form}
      return render(request, 'bcse_app/StandalonePageEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.StandalonePageForm(data, files=request.FILES, instance=standalone_page)
      if form.is_valid():
        savedStandalonePage = form.save()
        messages.success(request, "Standalone Page saved")
        return shortcuts.redirect('bcse:standalonePageEdit', id=savedStandalonePage.id)
      else:
        print(form.errors)
        messages.error(request, "Standalone Page could not be saved. Check the errors below.")
        context = {'form': form}
        return render(request, 'bcse_app/StandalonePageEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# DELETE STANDALONE PAGE
##########################################################
@login_required
def standalonePageDelete(request, id=''):
  """
  standalonePageDelete is called from the path 'adminConfiguration/standalonePages'
  :param request: request from the browser
  :param id='': id of standalone page to delete
  :returns: page with remaining standalone pages
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete standalone page')
    if '' != id:
      standalone_page = models.StandalonePage.objects.get(id=id)
      standalone_page.delete()
      messages.success(request, "Standalone Page deleted")

    return shortcuts.redirect('bcse:standalonePages')

  except models.StandalonePage.DoesNotExist:
    messages.success(request, "Standalone Page not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# VIEW STANDALONE PAGE
##########################################################
def standalonePageView(request, id='', url_alias=''):
  """
  standalonePageView is called from the path 'adminConfiguration/standalonePages'
  :param request: request from the browser
  :param id='': id of standalone page to view
  :param url_alias='': url of standalone page to view, is another way to get a specific page if id not provided
  :returns: rendered template 'bcse_app/StandalonePageView.html'
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if '' != id:
      standalone_page = models.StandalonePage.objects.get(id=id)
    elif '' != url_alias:
      standalone_page = models.StandalonePage.objects.get(url_alias=url_alias)

    if standalone_page.status == 'I':
      if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
        raise CustomException('You do not have the permission to view this standalone page')

    context = {'standalone_page': standalone_page}
    return render(request, 'bcse_app/StandalonePageView.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# CLONE STANDALONE PAGE
####################################
@login_required
def standalonePageCopy(request, id=''):
  """
  standalonePageCopy is called from the path 'adminConfiguration/standalonePages'
  :param request: request from the browser
  :param id='': id of standalone page to copy
  :returns: page with updated view of standalone pages or page user was on before
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:

    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to copy this standalone page')
    if '' != id:
      standalone_page = models.StandalonePage.objects.get(id=id)
      title = standalone_page.title
      standalone_page.pk = None
      standalone_page.id = None
      standalone_page.image = None
      standalone_page.url_alias = None
      standalone_page.save()

      original_standalone_page = models.StandalonePage.objects.get(id=id)
      standalone_page.title = 'Copy of ' + title
      standalone_page.created_date = datetime.datetime.now()
      standalone_page.modified_date = datetime.datetime.now()

      if original_standalone_page.image:
        try:
          source = original_standalone_page.image
          filecontent = ContentFile(source.file.read())
          filename = os.path.split(source.file.name)[-1]
          filename_array = filename.split('.')
          new_filename = filename_array[0] + '-' + str(standalone_page.id) + '.' + filename_array[1]
          standalone_page.image.save(new_filename, filecontent)
          standalone_page.save()
          source.file.close()
          original_standalone_page.image.save(filename, filecontent)
          original_standalone_page.save()
        except IOError as e:
          standalone_page.save()
      else:
        standalone_page.save()

      messages.success(request, "Standalone Page copied")
      return shortcuts.redirect('bcse:standalonePageEdit', id=standalone_page.id)

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


  except models.StandalonePage.DoesNotExist:
    messages.success(request, "Standalone Page not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# LIST OF FACILITATORS
##########################################################
@login_required
def facilitators(request):
  """
  facilitators is called from the path 'adminConfiguration/facilitators/'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/Facilitators.html'
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view facilitators')

    facilitators = models.TeacherLeader.objects.all()
    context = {'facilitators': facilitators}
    return render(request, 'bcse_app/Facilitators.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# EDIT FACILITATOR
##########################################################
@login_required
def facilitatorEdit(request, id=''):
  """
  facilitatorEdit is called from the path 'adminConfiguration/facilitators/'
  :param request: request from the browser
  :param id='': id of facilitatorEdit to edit
  :returns: page with remaining standalone pages
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit teacher leader')
    if '' != id:
      facilitator = models.TeacherLeader.objects.get(id=id)
    else:
      facilitator = models.TeacherLeader()

    if request.method == 'GET':
      form = forms.FacilitatorForm(instance=facilitator)
      context = {'form': form}
      return render(request, 'bcse_app/FacilitatorEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.FacilitatorForm(data, files=request.FILES, instance=facilitator)
      if form.is_valid():
        savedFacilitator = form.save()
        messages.success(request, "Facilitator saved")
        return shortcuts.redirect('bcse:facilitatorEdit', id=savedFacilitator.id)
      else:
        print(form.errors)
        message.error(request, "Facilitator could not be saved. Check the errors below.")
        context = {'form': form}
        return render(request, 'bcse_app/FacilitatorEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# DELETE TEACHER LEADER
##########################################################
@login_required
def facilitatorDelete(request, id=''):
  """
  facilitatorDelete is called from the path 'adminConfiguration/facilitators/'
  :param request: request from the browser
  :param id='': id of facilitator to delete
  :returns: page with remaining facilitator
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete facilitator')
    if '' != id:
      facilitator = models.TeacherLeader.objects.get(id=id)
      facilitator.delete()
      messages.success(request, "Facilitator deleted")

    return shortcuts.redirect('bcse:facilitators')

  except models.TeacherLeader.DoesNotExist:
    messages.success(request, "Facilitator not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# LIST OF USERS
##########################################################
@login_required
def users(request):
  """
  users is called from the path 'adminConfiguration/users/'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/Users.html'
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view users')

    if request.session.get('users_search', False):
      searchForm = forms.UsersSearchForm(user=request.user, initials=request.session['users_search'], prefix="user_search")
      page = request.session['users_search']['page']
    else:
      searchForm = forms.UsersSearchForm(user=request.user, initials=None, prefix="user_search")
      page = 1

    context = {'searchForm': searchForm, 'page': page}
    return render(request, 'bcse_app/Users.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################################
# FILTER USER LIST BASED ON FILTER CRITERIA
####################################################
@login_required
def usersSearch(request):
  """
  usersSearch is called from the path 'adminConfiguration/users/'
  :param request: request from the browser
  :returns: JSON view of filtered user(s)
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
      subscribed_filter = None
      photo_release_filter = None

      email = request.GET.get('user_search-email', '')
      first_name = request.GET.get('user_search-first_name', '')
      last_name = request.GET.get('user_search-last_name', '')
      user_role = request.GET.get('user_search-user_role', '')
      work_place = request.GET.get('user_search-work_place', '')
      joined_after = request.GET.get('user_search-joined_after', '')
      joined_before = request.GET.get('user_search-joined_before', '')
      status = request.GET.get('user_search-status', '')
      subscribed = request.GET.get('user_search-subscribed', '')
      photo_release_complete = request.GET.get('user_search-photo_release_complete', '')
      sort_by = request.GET.get('user_search-sort_by', '')
      columns = request.GET.getlist('user_search-columns', '')
      rows_per_page = request.GET.get('user_search-rows_per_page', settings.DEFAULT_ITEMS_PER_PAGE)
      page = request.GET.get('page', '')

      #set session variable
      request.session['users_search'] = {
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'user_role': user_role,
        'work_place': work_place,
        'joined_after': joined_after,
        'joined_before': joined_before,
        'status': status,
        'subscribed': subscribed,
        'photo_release_complete': photo_release_complete,
        'sort_by': sort_by,
        'columns': columns,
        'rows_per_page': rows_per_page,
        'page': page
      }

      if email:
        email_filter = Q(Q(user__email__icontains=email) | Q(user__userProfile__secondary_email__icontains=email))

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

      if subscribed:
        if subscribed == 'Y':
          subscribed_filter = Q(subscribe=True)
        else:
          subscribed_filter = Q(subscribe=False)

      if photo_release_complete:
        if photo_release_complete == 'Y':
          photo_release_filter = Q(photo_release_complete=True)
        else:
          photo_release_filter = Q(photo_release_complete=False)


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

      if subscribed_filter:
        query_filter = query_filter & subscribed_filter

      if photo_release_filter:
        query_filter = query_filter & photo_release_filter

      if status_filter:
        query_filter = query_filter & status_filter

      users = models.UserProfile.objects.all().filter(query_filter)

      direction = request.GET.get('direction') or 'asc'
      ignorecase = request.GET.get('ignorecase') or 'false'

      if sort_by:
        if sort_by == 'email':
          order_by = 'user__email'
        elif sort_by == 'first_name':
          order_by = 'user__first_name'
        elif sort_by == 'last_name':
          order_by = 'user__last_name'
        elif sort_by == 'date_joined_desc':
          order_by = 'created_date'
          direction = 'desc'
        elif sort_by == 'date_joined_asc':
          order_by = 'created_date'
          direction = 'asc'
        elif sort_by == 'last_updated_desc':
          order_by = 'modified_date'
          direction = 'desc'
        elif sort_by == 'last_updated_asc':
          order_by = 'modified_date'
          direction = 'asc'
      else:
        order_by = 'user__email'

      sort_order = [{'order_by': order_by, 'direction': direction, 'ignorecase': ignorecase}]

      users = paginate(request, users, sort_order, rows_per_page, page)

      context = {'users': users, 'columns': columns}
      response_data = {}
      response_data['success'] = True
      response_data['html'] = render_to_string('bcse_app/UsersTableView.html', context, request)
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################################
# CLEAR search FILTER
####################################################
def clearSearch(request, session_var=''):
  """
  clearSearch is called from the path 'adminConfiguration/', can be used on users, workplaces, etc
  :param request: request from the browser
  :param session_var='': saved search from admin that's previously been made
  :returns: page admin was on before
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if session_var in request.session:
      del request.session[session_var]

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# EXPORT USERS ON AN EXCEL DOC
##########################################################
@login_required
def usersExport(request):
  """
  usersExport is called from the path 'adminConfiguration/users/'
  :param request: request from the browser
  :returns: exported excel sheet of users or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to export users')

    if request.method == 'GET':
      users = models.UserProfile.objects.all().order_by('user__last_name', 'user__first_name')
      response = http.HttpResponse(content_type='application/ms-excel')
      response['Content-Disposition'] = 'attachment; filename="users_%s.xls"'%datetime.datetime.now()
      wb = xlwt.Workbook(encoding='utf-8')
      bold_font_style = xlwt.XFStyle()
      bold_font_style.font.bold = True
      font_style = xlwt.XFStyle()
      font_style.alignment.wrap = 1
      date_format = xlwt.XFStyle()
      date_format.num_format_str = 'mm/dd/yyyy'
      date_time_format = xlwt.XFStyle()
      date_time_format.num_format_str = 'mm/dd/yyyy hh:mm AM/PM'

      columns = ['User ID', 'Email', 'Full Name', 'Role', 'Workplace', 'Phone Number', 'IEIN', 'Grades Taught', 'Instagram Handle', 'Twitter Handle', 'Subscribed?', 'Photo Release Complete?', 'Status', 'Joined On', 'Last Login']
      font_styles = [font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, date_format, date_time_format]

      ws = wb.add_sheet('BCSE Users')
      row_num = 0
      #write the headers
      for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], bold_font_style)

      for user in users:
        row = [user.id,
               user.user.email,
               user.user.get_full_name(),
               user.get_user_role_display(),
               user.work_place.name if user.work_place else '',
               user.phone_number,
               user.iein,
               user.get_grades_taught_display(),
               user.instagram_handle,
               user.twitter_handle,
               'Yes' if user.subscribe else 'No',
               'Yes' if user.photo_release_complete else 'No',
               'Active' if user.user.is_active else 'Inactive',
               user.created_date.replace(tzinfo=None),
               user.user.last_login.replace(tzinfo=None) if user.user.last_login else '']
        row_num += 1
        for col_num in range(len(row)):
          ws.write(row_num, col_num, row[col_num], font_styles[col_num])

      wb.save(response)
      return response

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# UPLOAD USERS VIA AN EXCEL TEMPLATE
##########################################################
@login_required
def usersUpload(request):
  """
  usersUpload is called from the path 'adminConfiguration/users/'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/UsersUploadModal.html', JSON view of uploaded users or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
            name_pronounciation = row[7]
            dietary_preference = row[8]
            photo_release_complete = row[9]
            iein = row[10]
            admin_notes = row[11]
            workplace_id = row[12]
            if email:
              if User.objects.all().filter(username=email.lower()).count() == 0:
                if first_name:
                  if last_name:
                    if user_role:
                      #all required fields available to create user
                      newUser = create_user(request, email, first_name, last_name, user_roles[user_role], phone_number, twitter_handle, instagram_handle, name_pronounciation, dietary_preference, photo_release_complete, iein, admin_notes, workplace_id)
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
  """
  workPlaces is called from the path 'adminConfiguration/workPlaces/'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/WorkPlaces.html'
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view workplaces')

    if request.session.get('workplaces_search', False):
      searchForm = forms.WorkPlacesSearchForm(user=request.user, initials=request.session['workplaces_search'], prefix="work_place_search")
      page = request.session['workplaces_search']['page']
    else:
      searchForm = forms.WorkPlacesSearchForm(user=request.user, initials=None, prefix="work_place_search")
      page = 1

    context = {'searchForm': searchForm, 'page': page}
    return render(request, 'bcse_app/WorkPlaces.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################################
# FILTER WORKPLACES LIST BASED ON FILTER CRITERIA
####################################################
@login_required
def workPlacesSearch(request):
  """
  workPlacesSearch is called from the path 'adminConfiguration/workPlaces/'
  :param request: request from the browser
  :returns: JSON view of filtered workplace(s) or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to search workplaces')

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
      columns = request.GET.getlist('work_place_search-columns', '')
      rows_per_page = request.GET.get('work_place_search-rows_per_page', settings.DEFAULT_ITEMS_PER_PAGE)
      page = request.GET.get('page', '')


      #set session variable
      request.session['workplaces_search'] = {
        'name': name,
        'work_place_type': work_place_type,
        'district_number': district_number,
        'street_address_1': street_address_1,
        'street_address_2': street_address_2,
        'city': city,
        'state': state,
        'zip_code': zip_code,
        'status': status,
        'sort_by': sort_by,
        'columns': columns,
        'rows_per_page': rows_per_page,
        'page': page
      }

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
      work_places = work_places.annotate(users_count=Count('users'))

      ignorecase = 'false'
      direction = request.GET.get('direction') or 'asc'
      if sort_by:
        if sort_by == 'name':
          order_by = 'name'
          ignorecase = 'true'
        elif sort_by == 'status':
          order_by = 'status'
        elif sort_by == 'created_date_desc':
          order_by = 'created_date'
          direction = 'desc'
        elif sort_by == 'created_date_asc':
          order_by = 'created_date'
          direction = 'asc'
        elif sort_by == 'users_desc':
          order_by = 'users_count'
          direction = 'desc'
        elif sort_by == 'users_asc':
          order_by = 'users_count'
          direction = 'asc'
      else:
        order_by = 'name'

      sort_order = [{'order_by': order_by, 'direction': direction, 'ignorecase': ignorecase}]
      work_places = paginate(request, work_places, sort_order, rows_per_page, page)

      context = {'work_places': work_places, 'columns': columns}
      response_data = {}
      response_data['success'] = True
      response_data['html'] = render_to_string('bcse_app/WorkPlacesTableView.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# EDIT WORKPLACE
##########################################################
@login_required
def workPlaceEdit(request, id=''):
  """
  workPlaceEdit is called from the path 'adminConfiguration/workPlaces/'
  :param request: request from the browser
  :param id='': id of workplace to edit
  :returns: JSON view of workplace or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit workplace')
    if '' != id:
      work_place = models.WorkPlace.objects.get(id=id)
    else:
      work_place = models.WorkPlace()

    if request.method == 'GET':
      form = forms.WorkPlaceForm(instance=work_place, user=request.user, prefix='work_place')
      context = {'form': form}
      return render(request, 'bcse_app/WorkPlaceEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.WorkPlaceForm(data, instance=work_place, user=request.user, prefix='work_place')
      response_data = {}
      if form.is_valid():
        savedWorkPlace = form.save()
        messages.success(request, "Workplace saved successfully")
        response_data['success'] = True
      else:
        print(form.errors)
        context = {'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/WorkPlaceEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


###################################################
# UPDATE WORKPLACE NOTES
###################################################
@login_required
def workPlaceUpdate(request, id=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S', 'D']:
      raise CustomException('You do not have the permission to update workplace notes')

    workplace = models.WorkPlace.objects.get(id=id)

    if request.method == 'GET':
      form = forms.WorkPlaceUpdateForm(instance=workplace)
      context = {'form': form}
      return render(request, 'bcse_app/WorkplaceUpdateModal.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.WorkPlaceUpdateForm(data, instance=workplace)
      response_data = {}
      if form.is_valid():
        savedWorkPlace = form.save()
        response_data['success'] = True
        messages.success(request, 'Workplace %s updated' % id)
      else:
        print(form.errors)
        response_data['success'] = False
        context = {'form': form}
        response_data['html'] = render_to_string('bcse_app/WorkplaceUpdateModal.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except models.WorkPlace.DoesNotExist as e:
    messages.error(request, 'Workplace does not exists')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# DELETE WORKPLACE
##########################################################
@login_required
def workPlaceDelete(request, id=''):
  """
  workPlaceDelete is called from the path 'adminConfiguration/workPlaces/'
  :param request: request from the browser
  :param id='': id of workplace to delete
  :returns: page view of remaining workplaces
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete workplace')
    if '' != id:
      work_place = models.WorkPlace.objects.get(id=id)
      if id == models.get_placeholder_workplace():
        messages.success(request, "This is the default workplace and cannot be deleted")
      elif work_place.users.count() > 0 or work_place.work_place_to_registration.count() > 0 or work_place.work_place_to_reservation.count() > 0:
        messages.success(request, "%s is associated with %s user(s), %s workshop registration(s) and %s Baxter Box reservation(s) and cannot be deleted" % (work_place.name, work_place.users.count(), work_place.work_place_to_registration.count(), work_place.work_place_to_reservation.count()))
      else:
        work_place.delete()
        messages.success(request, "Workplace deleted")

    return shortcuts.redirect('bcse:workPlaces')

  except models.WorkPlace.DoesNotExist:
    messages.success(request, "Workplace not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# UPLOAD WORKPLACES VIA AN EXCEL TEMPLATE
##########################################################
@login_required
def workPlacesUpload(request):
  """
  workPlacesUpload is called from the path 'adminConfiguration/workPlaces/'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/WorkPlacesUploadModal.html', JSON view of uploaded workplaces or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to upload workplaces')

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
            if name and work_place_type: # and street_address_1 and city and state and zip_code:
              if models.WorkPlace.objects.all().filter(name=name, work_place_type=work_place_types[work_place_type]).count() > 0:
                upload_status.append("Workplace already exists")
              else:
                work_place = models.WorkPlace(name=name, work_place_type=work_place_types[work_place_type], district_number=district_number, street_address_1=street_address_1, street_address_2=street_address_2, city=city, state=state, zip_code=zip_code, status='A')
                work_place.save()
                new_schools += 1
                upload_status.append("Workplace created")
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
# EXPORT WORKPLACES ON AN EXCEL DOC
##########################################################
@login_required
def workPlacesExport(request):
  """
  workPlacesExport is called from the path 'adminConfiguration/workPlaces/'
  :param request: request from the browser
  :returns: exported excel sheet of workplaces or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to export workplaces')

    if request.method == 'GET':
      workplaces = models.WorkPlace.objects.all().order_by('name')
      response = http.HttpResponse(content_type='application/ms-excel')
      response['Content-Disposition'] = 'attachment; filename="workplaces_%s.xls"'%datetime.datetime.now()
      wb = xlwt.Workbook(encoding='utf-8')
      bold_font_style = xlwt.XFStyle()
      bold_font_style.font.bold = True
      font_style = xlwt.XFStyle()
      font_style.alignment.wrap = 1
      date_format = xlwt.XFStyle()
      date_format.num_format_str = 'mm/dd/yyyy'
      date_time_format = xlwt.XFStyle()
      date_time_format.num_format_str = 'mm/dd/yyyy hh:mm AM/PM'

      columns = ['ID', 'Name', 'Workplace Type', 'District #', 'Street Address 1', 'Street Address 2', 'City', 'State', 'Zip Code', 'Latitude', 'Longitude', 'Distance (miles)', 'Travel Time (mins)', 'Status', 'Created Date', 'Modified Date']
      font_styles = [font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, date_time_format, date_time_format]

      ws = wb.add_sheet('Workplaces')
      row_num = 0
      #write the headers
      for col_num in range(len(columns)):
        ws.write(row_num, col_num, columns[col_num], bold_font_style)

      for workplace in workplaces:
        row = [workplace.id,
               workplace.name,
               workplace.get_work_place_type_display(),
               workplace.district_number,
               workplace.street_address_1,
               workplace.street_address_2,
               workplace.city,
               workplace.state,
               workplace.zip_code,
               workplace.latitude,
               workplace.longitude,
               workplace.distance_from_base,
               workplace.time_from_base,
               workplace.get_status_display(),
               workplace.created_date.replace(tzinfo=None),
               workplace.modified_date.replace(tzinfo=None)]
        row_num += 1
        for col_num in range(len(row)):
          ws.write(row_num, col_num, row[col_num], font_styles[col_num])

      wb.save(response)
      return response

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# UPLOAD WORKSHOP REGISTRATIONS VIA AN EXCEL TEMPLATE
##########################################################
@login_required
def workshopRegistrantsUpload(request, id=''):
  """
  workshopRegistrantsUpload is called from the path 'adminConfiguration/workshopsRegistrants/'
  :param request: request from the browser
  :param id='': id of workplace to upload a registrant to via an excel template
  :returns: rendered template 'bcse_app/RegistrantsUploadModal.html', JSON view of a workshop's registrants, or an error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
            name_pronounciation = row[7]
            dietary_preference = row[8]
            photo_release_complete = row[9]
            iein = row[10]
            admin_notes = row[11]
            workplace_id = row[12]
            if email:
              if User.objects.all().filter(username=email.lower()).count() == 0:
                if first_name:
                  if last_name:
                    if user_role:
                      #all required fields available to create user
                      newUser = create_user(request, email, first_name, last_name, user_roles[user_role], phone_number, twitter_handle, instagram_handle, name_pronounciation, dietary_preference, photo_release_complete, iein, admin_notes, workplace_id)
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
# UPLOAD ALL WORKSHOPS REGISTRATIONS VIA CSV TEMPLATE
##########################################################
@login_required
def allWorkshopsRegistrantsUpload(request):
  """
  allWorkshopsRegistrantsUpload is called from the path 'adminConfiguration/workshopsRegistrants/'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/RegistrantsUploadModal.html', JSON view of a workshop's registrants, or an error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to upload registrants')

    if request.method == 'GET':
      form = forms.UsersUploadForm(user=request.user)
      context = {'form': form}
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
          upload_status = ["Status"]
          registration_statuses = dict(map(reversed, models.WORKSHOP_REGISTRATION_STATUS_CHOICES))
          total_rows = 0
          new_registrants = 0
          for row in sheet:
            total_rows += 1
            nid = row[0]
            status = row[1]
            email = row[2]

            if nid:
              workshop = models.Workshop.objects.all().filter(nid=nid).first()
              if workshop:
                if email:
                  if User.objects.all().filter(username=email.lower()).count() == 1:
                    created = create_registration(request, email, workshop.id, registration_statuses[status])
                    print(created)
                    if created:
                      new_registrants += 1
                      upload_status.append("User added to workshop.")
                    else:
                      upload_status.append("User registration for workshop already exists")
                else:
                  upload_status.append("User email not provided. User not added to workshop.")
              else:
                upload_status.append("Workshop with nid %s does not exist. User not added to workshop." % nid)
            else:
               upload_status.append("Workshop nid not provided. User not added to workshop.")

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
          response_data['message'] = "%s out of %s workshop registrations were successfully added. \
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
  """
  teamMembers is called from the path 'adminConfiguration/teamMembers/'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/TeamMembers.html'
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view team members')

    members = models.Team.objects.all().order_by('former_member', 'order')
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
  """
  teamMemberEdit is called from the path 'adminConfiguration/teamMembers/'
  :param request: request from the browser
  :param id='': id of team member to edit
  :returns: rendered template 'bcse_app/TeamMemberEdit.html', JSON view of team members or an error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
  """
  teamMemberDelete is called from the path 'adminConfiguration/teamMembers/'
  :param request: request from the browser
  :param id='': id of team member to delete
  :returns: page view of remaining team members
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

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
# VIEW TEAM MEMBER
##########################################################
def teamMemberView(request, id=''):
  try:
    member = models.Team.objects.get(id=id)
    context = {'member': member}
    return render(request, 'bcse_app/TeamModal.html', context)

  except models.Team.DoesNotExist as e:
    messages.error(request, 'Team member not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# VIEW PARTNERS
##########################################################
@login_required
def partners(request):
  """
  partners is called from the path 'adminConfiguration/partners/'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/Partners.html'
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view partners')

    partners = models.Partner.objects.all()
    context = {'partners': partners}
    return render(request, 'bcse_app/Partners.html', context)

  except models.Partner.DoesNotExist as e:
    messages.error(request, 'Partner not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# EDIT PARTNER
##########################################################
@login_required
def partnerEdit(request, id=''):
  """
  partnerEdit is called from the path 'adminConfiguration/partners/'
  :param request: request from the browser
  :param id='': id of partner to edit
  :returns: rendered template 'bcse_app/PartnerEdit.html', JSON view of partners or an error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
  """
  partnerDelete is called from the path 'adminConfiguration/partners/'
  :param request: request from the browser
  :param id='': id of partner to delete
  :returns: page view of remaining partners
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

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


##########################################################
# VIEW COLLABORATORS
##########################################################
@login_required
def collaborators(request):
  """
  collaborators is called from the path 'adminConfiguration/collaborators/'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/Collaborators.html'
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view collaborators')

    collaborators = models.Collaborator.objects.all()
    context = {'collaborators': collaborators}
    return render(request, 'bcse_app/Collaborators.html', context)

  except models.Collaborator.DoesNotExist as e:
    messages.error(request, 'Collaborator not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# EDIT COLLABORATOR
##########################################################
@login_required
def collaboratorEdit(request, id=''):
  """
  collaboratorEdit is called from the path 'adminConfiguration/collaborators/'
  :param request: request from the browser
  :param id='': id of collaborator to edit
  :returns: rendered template 'bcse_app/CollaboratorEdit.html', JSON view of collaborators or an error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit collaborator')
    if '' != id:
      collaborator = models.Collaborator.objects.get(id=id)
    else:
      collaborator = models.Collaborator()

    if request.method == 'GET':
      form = forms.CollaboratorForm(instance=collaborator)
      context = {'form': form}
      return render(request, 'bcse_app/CollaboratorEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.CollaboratorForm(data, files=request.FILES, instance=collaborator)
      response_data = {}
      if form.is_valid():
        savedcollaborator = form.save()
        messages.success(request, "Collaborator saved successfully")
        response_data['success'] = True
      else:
        print(form.errors)
        context = {'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/CollaboratorEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# DELETE COLLABORATOR
##########################################################
@login_required
def collaboratorDelete(request, id=''):
  """
  collaboratorDelete is called from the path 'adminConfiguration/collaborators/'
  :param request: request from the browser
  :param id='': id of collaborator to delete
  :returns: page view of remaining collaborators
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete collaborator')
    if '' != id:
      collaborator = models.Collaborator.objects.get(id=id)
      collaborator.delete()
      messages.success(request, "Collaborator deleted")

    return shortcuts.redirect('bcse:collaborators')

  except models.Collaborator.DoesNotExist:
    messages.error(request, "Collaborator not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################
# SURVEYS
####################################
@login_required
def surveys(request):
  """
  surveys is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :returns: rendered template 'bcse_app/Surveys.html'
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view surveys')

    if request.method == 'GET':
      if request.session.get('surveys_search', False):
        searchForm = forms.SurveysSearchForm(user=request.user, initials=request.session['surveys_search'], prefix="survey_search")
        page = request.session['surveys_search']['page']
      else:
        searchForm = forms.SurveysSearchForm(user=request.user, initials=None, prefix="survey_search")
        page = 1

      context = {'searchForm': searchForm, 'page': page}
      return render(request, 'bcse_app/Surveys.html', context)

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


################################################################
# FILTER SURVEY LIST BASED ON FILTER CRITERIA
################################################################
@login_required
def surveysSearch(request):
  """
  surveysSearch is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :returns: page view of filtered surveys or an error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:

    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to search surveys')

    if request.method == 'GET':

      query_filter = Q()

      name = request.GET.get('survey_search-name', '')
      survey_type = request.GET.get('survey_search-survey_type', '')
      status = request.GET.get('survey_search-status', '')
      sort_by = request.GET.get('survey_search-sort_by', '')
      rows_per_page = request.GET.get('survey_search-rows_per_page', settings.DEFAULT_ITEMS_PER_PAGE)
      page = request.GET.get('page', '')

      #set session variable
      request.session['surveys_search'] = {
        'name': name,
        'survey_type': survey_type,
        'status': status,
        'sort_by': sort_by,
        'rows_per_page': rows_per_page,
        'page': page
      }

      if name:
        query_filter = query_filter & Q(name__icontains=name)

      if survey_type:
        query_filter = query_filter & Q(survey_type=survey_type)

      if status:
        query_filter = query_filter & Q(status=status)

      # Convert the choices into a list of When cases
      when_cases = [When(survey_type=key, then=Value(value)) for key, value in models.SURVEY_TYPE_CHOICES]

      # Default case if none of the choices match
      default_case = Value('Unknown')

      surveys = models.Survey.objects.all().annotate(
        num_of_responses=Count('survey_submission'),
        survey_type_display=Case(
            *when_cases,
            default=default_case,
            output_field=CharField(),
      )).filter(query_filter)

      direction = request.GET.get('direction') or 'asc'
      ignorecase = request.GET.get('ignorecase') or 'false'

      if sort_by:
        if sort_by == 'name':
          order_by = 'name'
        elif sort_by == 'survey_type':
          order_by = 'survey_type_display'
        elif sort_by == 'status':
          order_by = 'status'
        elif sort_by == 'responses':
          order_by = 'num_of_responses'
          direction = 'desc'
      else:
        order_by = 'name'

      sort_order = [{'order_by': order_by, 'direction': direction, 'ignorecase': ignorecase}]

      surveys = paginate(request, surveys, sort_order, rows_per_page, page)

      domain = request.get_host()

      if 'localhost' not in domain:
        domain = 'https://%s' % domain

      context = {'surveys': surveys, 'domain': domain}

      response_data = {}
      response_data['success'] = True
      response_data['html'] = render_to_string('bcse_app/SurveysTableView.html', context, request)
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except models.Survey.DoesNotExist as ce:
    messages.error(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# EDIT SURVEY
##########################################################
@login_required
def surveyEdit(request, id=''):
  """
  surveyEdit is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param id='': id of survey to edit
  :returns: rendered template 'bcse_app/SurveyEdit.html', page view of edited surveys or an error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

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
        messages.warning(request, "This survey has %s user submissions. Please be careful with the modification." % surveySubmissions.count())
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


####################################
# CLONE SURVEY
####################################
def surveyCopy(request, id=''):
  """
  surveyEdit is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param id='': id of survey to copy
  :returns: page view of edited surveys or page admin was on before
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:

    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to copy this survey')
    if '' != id:
      survey = models.Survey.objects.get(id=id)
      surveyComponents = models.SurveyComponent.objects.all().filter(survey=survey)
      title = survey.name
      survey.pk = None
      survey.id = None
      survey.save()

      original_survey = models.Survey.objects.get(id=id)
      survey.name = 'Copy of ' + title
      survey.created_date = datetime.datetime.now()
      survey.modified_date = datetime.datetime.now()
      survey.save()

      for surveyComponent in surveyComponents:
        surveyComponent.pk = None
        surveyComponent.id = None
        surveyComponent.survey = survey
        surveyComponent.created_date = datetime.datetime.now()
        surveyComponent.modified_date = datetime.datetime.now()
        surveyComponent.save()

      messages.success(request, "Survey copied")
      return shortcuts.redirect('bcse:surveyEdit', id=survey.id)

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

  except models.Survey.DoesNotExist:
    messages.success(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# GET ASSOCIATED ENTITY FOR SURVEY SUBMISSION
##########################################################
def get_submission_connected_entity(submission_id):
  connected_entity = {}
  reservation_feedback = models.ReservationFeedback.objects.all().filter(feedback__UUID=submission_id)
  if reservation_feedback.count():
    reservation = models.Reservation.objects.get(id=reservation_feedback[0].reservation.id)
    connected_entity['entity_type'] = 'Reservation'
    connected_entity['entity'] = reservation
    return connected_entity
  else:
    workshop_application = models.WorkshopApplication.objects.all().filter(application__UUID=submission_id)
    if workshop_application:
      workshop = models.Workshop.objects.get(id=workshop_application[0].registration.workshop_registration_setting.workshop.id)
      connected_entity['entity_type'] = 'Workshop'
      connected_entity['entity'] = workshop
      return connected_entity

  return None

##########################################################
# VIEW SURVEY SUBMISSIONS
##########################################################
@login_required
def surveySubmissions(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to view survey submissions')

    survey = models.Survey.objects.get(id=id)

    if request.method == 'GET':
      if request.session.get('survey_submissions_search', False):
        searchForm = forms.SurveySubmissionsSearchForm(user=request.user, initials=request.session['survey_submissions_search'], prefix="survey_submission_search")
        page = request.session['survey_submissions_search']['page']
      else:
        searchForm = forms.SurveySubmissionsSearchForm(user=request.user, initials=None, prefix="survey_submission_search")
        page = 1

      context = {'survey': survey, 'searchForm': searchForm, 'page': page}
      return render(request, 'bcse_app/SurveySubmissions.html', context)

    return http.HttpResponseNotAllowed(['GET'])

  except models.Survey.DoesNotExist as ce:
    messages.error(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

################################################################
# FILTER SURVEY SUBMISSIONS LIST BASED ON FILTER CRITERIA
################################################################
@login_required
def surveySubmissionsSearch(request, id='', download=False):
  """
  surveyEdit is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param id='': id of survey to search through submissions for
  :returns: page view of filtered submissions from survey or an error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:

    survey = models.Survey.objects.get(id=id)
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to search survey submissions')
    elif request.user.userProfile.user_role not in ['A', 'S']:
      if survey.survey_type == 'W':
        try:
          workshop = models.Workshop.objects.get(registration_setting__application=survey)
          if request.user.userProfile.id not in workshop.teacher_leaders.all().values_list('teacher__id', flat=True):
            raise CustomException('You do not have the permission to search survey submission')
        except models.Workshop.DoesNotExist:
          raise CustomException('You do not have the permission to search survey submission')
      else:
        raise CustomException('You do not have the permission to search survey submission')


    if request.method == 'GET':

      query_filter = Q(survey=survey)
      email_filter = None
      first_name_filter = None
      last_name_filter = None
      user_role_filter = None
      work_place_filter = None
      status_filter = None
      response_after_filter = None
      response_before_filter = None

      email = request.GET.get('survey_submission_search-email', '')
      first_name = request.GET.get('survey_submission_search-first_name', '')
      last_name = request.GET.get('survey_submission_search-last_name', '')
      user_role = request.GET.get('survey_submission_search-user_role', '')
      work_place = request.GET.get('survey_submission_search-work_place', '')
      status = request.GET.getlist('survey_submission_search-status', '')
      response_after = request.GET.get('survey_submission_search-response_after', '')
      response_before = request.GET.get('survey_submission_search-response_before', '')
      sort_by = request.GET.get('survey_submission_search-sort_by', '')
      columns = request.GET.getlist('survey_submission_search-columns', '')
      rows_per_page = request.GET.get('survey_submission_search-rows_per_page', settings.DEFAULT_ITEMS_PER_PAGE)
      page = request.GET.get('page', '')

      #set session variable
      request.session['survey_submissions_search'] = {
        'email': email,
        'first_name': first_name,
        'last_name': last_name,
        'user_role': user_role,
        'work_place': work_place,
        'status': status,
        'response_after': response_after,
        'response_before': response_before,
        'columns': columns,
        'sort_by': sort_by,
        'rows_per_page': rows_per_page,
        'page': page
      }

      if email:
        email_filter = Q(Q(user__user__email__icontains=email) | Q(user__secondary_email__icontains=email))


      if first_name:
        first_name_filter = Q(user__user__first_name__icontains=first_name)
        query_filter = query_filter & first_name_filter

      if last_name:
        last_name_filter = Q(user__user__last_name__icontains=last_name)
        query_filter = query_filter & last_name_filter

      if user_role:
        user_role_filter = Q(user__user_role=user_role)
        query_filter = query_filter & user_role_filter

      if work_place:
        work_place_filter = Q(survey_submission_to_work_place__work_place=work_place)
        query_filter = query_filter & work_place_filter

      if status:
        status_filter = Q(status__in=status)
        query_filter = query_filter & status_filter

      if response_after:
        response_after = datetime.datetime.strptime(response_after, '%B %d, %Y')
        response_after_filter = Q(created_date__gte=response_after)
        query_filter = query_filter & response_after_filter

      if response_before:
        response_before = datetime.datetime.strptime(response_before, '%B %d, %Y')
        response_before_filter = Q(created_date__lte=response_before)
        query_filter = query_filter & response_before_filter

      surveySubmissions = models.SurveySubmission.objects.all().filter(query_filter)

      if download:
        return surveySubmissions
      else:
        direction = request.GET.get('direction') or 'asc'
        ignorecase = request.GET.get('ignorecase') or 'false'

        if sort_by:
          if sort_by == 'email':
            order_by = 'user__user__email'
          elif sort_by == 'first_name':
            order_by = 'user__user__first_name'
          elif sort_by == 'last_name':
            order_by = 'user__user__last_name'
          elif sort_by == 'created_date_desc':
            order_by = 'created_date'
            direction = 'desc'
            ignorecase = 'false'
          elif sort_by == 'created_date_asc':
            order_by = 'created_date'
            direction = 'asc'
            ignorecase = 'false'
        else:
          order_by = 'user__user__email'

        sort_order = [{'order_by': order_by, 'direction': direction, 'ignorecase': ignorecase}]

        surveySubmissions = paginate(request, surveySubmissions, sort_order, rows_per_page, page)

        context = {'survey': survey, 'surveySubmissions': surveySubmissions, 'columns': columns}

        response_data = {}
        response_data['success'] = True
        response_data['html'] = render_to_string('bcse_app/SurveySubmissionsTableView.html', context, request)
        return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except models.Survey.DoesNotExist as ce:
    messages.error(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


###################################################################################
# EXPORT SURVEY SUBMISSIONS OF ONE SURVEY OR ONE SUBMISSION ON AN EXCEL DOC
###################################################################################
@login_required
def surveySubmissionsExport(request, survey_id='', submission_uuid=''):
  """
  surveySubmissionsExport is called from the path 'adminConfiguration/surveys/', can export one or multiple submissions to excel
  :param request: request from the browser
  :param survey_id='': id of survey to export submissions for
  :param submission_uuid='': id of submission to export
  :returns: excel sheet with exported submission(s) or an error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    survey = models.Survey.objects.get(id=survey_id)
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to export survey submission')
    elif request.user.userProfile.user_role not in ['A', 'S']:
      if survey.survey_type == 'W':
        try:
          workshop = models.Workshop.objects.get(registration_setting__application=survey)
          if request.user.userProfile.id not in workshop.teacher_leaders.all().values_list('teacher__id', flat=True):
            raise CustomException('You do not have the permission to export survey submission')
        except models.Workshop.DoesNotExist:
          raise CustomException('You do not have the permission to export survey submission')
      else:
        raise CustomException('You do not have the permission to export survey submission')

    if request.method == 'GET':
      filters = None
      if '' != submission_uuid:
        surveySubmissions = models.SurveySubmission.objects.all().filter(survey=survey, UUID=submission_uuid)
      else:
        email = request.GET.get('survey_submission_search-email', '')
        first_name = request.GET.get('survey_submission_search-first_name', '')
        last_name = request.GET.get('survey_submission_search-last_name', '')
        user_role = request.GET.get('survey_submission_search-user_role', '')
        work_place = request.GET.get('survey_submission_search-work_place', '')
        status = request.GET.get('survey_submission_search-status', '')

        filters = {
          'Email': email,
          'First Name': first_name,
          'Last Name': last_name,
          'User Role': dict(models.USER_ROLE_CHOICES)[user_role] if user_role else '',
          'Workplace': models.WorkPlace.objects.get(id=work_place).name if work_place else '',
          'Response Status': dict(models.SURVEY_SUBMISSION_STATUS_CHOICES)[status] if status else ''
        }
        surveySubmissions = surveySubmissionsSearch(request, survey.id, True)

      if surveySubmissions.count() == 0:
        raise CustomException('There are no responses to export')

      response = http.HttpResponse(content_type='application/ms-excel')
      if submission_uuid:
        response['Content-Disposition'] = 'attachment; filename="survey_%s_response_%s.xls"'% (survey.id, submission_uuid)
      else:
        response['Content-Disposition'] = 'attachment; filename="survey_%s_responses.xls"'%survey.id

      wb = generateSurveySubmissionsExcel(request, survey, surveySubmissions, filters)
      wb.save(response)
      return response

    return http.HttpResponseNotAllowed(['GET'])

  except models.Survey.DoesNotExist as ce:
    messages.error(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

#########################################
# GENERATE EXCEL WITH SURVEY RESPONSES
########################################
def generateSurveySubmissionsExcel(request, survey, surveySubmissions, filters=''):
  """
  generateSurveySubmissionsExcel is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param survey: survey to generate excel sheet from
  :param surveySubmissions: submissions associated with the survey passed as parameter
  :returns: excel sheet with generated submissions from a survey
  """
  is_admin = None
  if not request.user.is_anonymous:
    if request.user.userProfile.user_role in ['A', 'S']:
      is_admin = True
    else:
      if survey.survey_type == 'W':
        try:
          workshop = models.Workshop.objects.get(registration_setting__application=survey)
          if request.user.userProfile.id in workshop.teacher_leaders.all().values_list('teacher__id', flat=True):
            is_admin = True
          else:
            is_admin = False
        except models.Workshop.DoesNotExist:
          raise CustomException('You do not have the permission to export survey submission')
      else:
        is_admin = False

  else:
    is_admin = False

  wb = xlwt.Workbook(encoding='utf-8')
  bold_font_style = xlwt.XFStyle()
  bold_font_style.font.bold = True
  font_style = xlwt.XFStyle()
  font_style.alignment.wrap = 1
  date_format = xlwt.XFStyle()
  date_format.num_format_str = 'mm/dd/yyyy'
  date_time_format = xlwt.XFStyle()
  date_time_format.num_format_str = 'mm/dd/yyyy hh:mm AM/PM'

  connected_entity_type = 'Connected Entity'
  if survey.survey_type == 'B':
    connected_entity_type = 'Activity'
  elif survey.survey_type == 'W':
    connected_entity_type = 'Workshop'

  ws = wb.add_sheet('Survey Responses')
  row_num = 0

  ###########################################
  # get list of questions in the survey
  questions = []
  for survey_component in survey.survey_component.all():
    if survey_component.component_type != 'IN':
      questions.append(survey_component)
  ##########################################

  #include all columns for admins
  if is_admin:

    #survey stats header
    columns = ['Survey ID', 'Survey Name', 'Total Responses', 'In-Progress', 'Submitted', 'Reviewed']
    font_styles = [font_style,font_style,font_style,font_style,font_style, font_style]
    #write the headers
    for col_num in range(len(columns)):
      ws.write(row_num, col_num, columns[col_num], bold_font_style)

    all_submissions = models.SurveySubmission.objects.all().filter(survey=survey)
    #survey stats data
    row = [survey.id,
           survey.name,
           all_submissions.count(),
           all_submissions.filter(status='I').count(),
           all_submissions.filter(status='S').count(),
           all_submissions.filter(status='R').count()
          ]
    row_num += 1
    #write stats data
    for col_num in range(len(row)):
      ws.write(row_num, col_num, row[col_num], font_styles[col_num])

    #add two empty rows
    row_num += 3

    #user info header
    columns = ['User ID', 'Email', 'Full Name', 'Workplace', connected_entity_type, 'Response ID', 'IP Address']
    font_styles = [font_style,font_style,font_style,font_style,font_style, font_style, font_style]
    question_col_num = len(columns)

    #question header
    for question in questions:
      question_label = 'Question %s.%s' % (question.page, question.order)
      if question.is_required:
        question_label += ' *'
      columns.append(question_label)
      font_styles.append(font_style)

    #status header
    columns.append('Survey Status')
    font_styles.append(font_style)
    columns.append('Created Date')
    font_styles.append(date_time_format)
    columns.append('Admin Notes')
    font_styles.append(font_style)

    #write the user info header, question header and status header
    for col_num in range(len(columns)):
      ws.write(row_num, col_num, columns[col_num], bold_font_style)

    row_num += 1
    col_num = question_col_num

    #write question content
    for question in questions:
      #question content
      ws.write(row_num, col_num, remove_html_tags(request, smart_str(question.content)), font_style)

      #question type
      ws.write(row_num+1, col_num, question.get_component_type_display(), font_style)

      #question options
      options = question.options
      if question.display_other_option and question.other_option_label:
        options += '\n'
        options += question.other_option_label
      ws.write(row_num+2, col_num, options, font_style)

      col_num += 1

    row_num += 2

  ##########################################
  #non-admin survey submission confirmation
  else:
    columns = []
    font_styles = []
    #question header
    for question in questions:
      question_label = 'Question %s.%s' % (question.page, question.order)
      if question.is_required:
        question_label += ' *'
      columns.append(question_label)
      font_styles.append(font_style)

    #write question headers
    for col_num in range(len(columns)):
      ws.write(row_num, col_num, columns[col_num], bold_font_style)

    row_num += 1
    col_num = 0

    #write the question content
    for question in questions:
      #question content
      ws.write(row_num, col_num, remove_html_tags(request, smart_str(question.content)), font_style)
      col_num += 1

  ####################################
  #iterate each submission
  for submission in surveySubmissions:
    row_num += 1

    #find connected entity
    connected_entity = get_submission_connected_entity(submission.UUID)
    connected_entity_name = ''
    if connected_entity:
      if survey.survey_type == 'B':
        if connected_entity['entity'].activity:
          connected_entity_name = connected_entity['entity'].activity.name
        elif connected_entity['entity'].other_activity:
          connected_entity_name = connected_entity['entity'].other_activity_name
      elif survey.survey_type == 'W':
        connected_entity_name = connected_entity['entity'].name

    # user info data for admins
    if is_admin:
      row = [submission.user.id if submission.user else '',
             submission.user.user.email if submission.user else '',
             submission.user.user.get_full_name() if submission.user else '',
             submission.survey_submission_to_work_place.work_place.name if hasattr(submission, 'survey_submission_to_work_place') else '',
             connected_entity_name,
             str(submission.UUID),
             submission.ip_address
           ]
    # non-admins
    else:
      row = []

    #responses for each submission
    survey_responses = models.SurveyResponse.objects.all().filter(submission=submission)
    for question in questions:
      survey_response = survey_responses.filter(survey_component=question)
      response = ''
      if survey_response:
        if survey_response.first().response:
          response = survey_response.first().response
        elif survey_response.first().responseFile:
          response = survey_response.first().responseFile.url

      row.append(response)

    #submission status for admins
    if is_admin:
      row.append(submission.get_status_display())
      row.append(submission.created_date.replace(tzinfo=None))
      row.append(submission.admin_notes)

    #write responses
    for col_num in range(len(row)):
      ws.write(row_num, col_num, row[col_num], font_styles[col_num])

  if filters:
    ws = wb.add_sheet('Applied Filters')
    row_num = 0
    ws.write(row_num, 0, 'Field', bold_font_style)
    ws.write(row_num, 1, 'Value', bold_font_style)
    row_num += 1
    for field, value in filters.items():
      ws.write(row_num, 0, field, font_style)
      ws.write(row_num, 1, value, font_style)
      row_num += 1

  return wb

##########################################################
# EDIT SURVEY COMPONENT
##########################################################
@login_required
def surveyComponentEdit(request, survey_id='', id=''):
  """
  surveyComponentEdit is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param survey_id='': id of survey to access components for
  :param id='': id of survey component to edit
  :returns: rendered template 'bcse_app/SurveyComponentEdit.html', JSON view of surveys or error page
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

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
        messages.error(request, 'Please check the form below for missing required fields or duplicate Page/Order entry')
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
  """
  surveyComponentDelete is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param survey_id='': id of survey to access components for
  :param id='': id of survey component to delete
  :returns: page view of remaining survey components present in survey(s)
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

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
  """
  surveyDelete is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param id='': id of survey to delete
  :returns: page view of remaining surveys
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete survey')
    if '' != id:
      survey = models.Survey.objects.get(id=id)
      surveySubmissions = models.SurveySubmission.objects.all().filter(survey=survey)
      submissions = surveySubmissions.count()
      if submissions > 0:
        messages.error(request, "This survey has %s response(s) and cannot be deleted.  If you need to delete this survey, delete all the responses first." % submissions)
        return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
      else:
        survey.delete()
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
  """
  surveySubmission is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param survey_id=='': id of survey to create submission for
  :param page_num='': page number to get survey from
  :returns: rendered template 'bcse_app/SurveySubmission.html', JSON view of survey submissions present, home page or error page
  :raises CustomException: redirects user to page they were on before encountering error due to the survey not having the request page number
  """
  try:
    survey = models.Survey.objects.get(id=survey_id)
    if survey.status == 'A':
      total_pages = models.SurveyComponent.objects.all().filter(survey=survey).aggregate(Max('page'))['page__max']
      if request.user.is_anonymous:
        user = None
      else:
        user = request.user.userProfile

      #connecting parameters
      workshop_id = request.GET.get('workshop_id', '')
      if survey.survey_type == 'W' and workshop_id:
        workshop = models.Workshop.objects.get(id=workshop_id)

      reservation_id = request.GET.get('reservation_id', '')
      if '' == page_num:
        page_num = 1

      if '' != submission_uuid:
        submission = models.SurveySubmission.objects.get(UUID=submission_uuid)
        print('existing submission')
      else:
        #delete old incomplete submissions
        if survey.survey_type == 'W' and workshop_id:
          #for workshop applications, delete all previous submissions
          incomplete_submissions = models.SurveySubmission.objects.all().filter(survey=survey, user=user, application_to_registration__registration__workshop_registration_setting__workshop__id=workshop_id)
          incomplete_submissions.delete()
        '''elif survey.survey_type == 'B' and reservation_id:
          #for baxter box survey, delete all incomplete submissions
          incomplete_submissions = models.SurveySubmission.objects.all().filter(survey=survey, status='I', feedback_to_reservation__reservation__id=reservation_id)
          incomplete_submissions.delete()
        '''
        submission = models.SurveySubmission.objects.create(UUID=uuid.uuid4(), survey=survey, ip_address=request.META['REMOTE_ADDR'])
        print('new submission')
        if user and page_num == 1:
          if user.user_role == 'A':
            submission.admin_notes = 'Submission created by admin'
          if user.user_role != 'A':
            submission.user = user
          elif reservation_id:
            reservation = models.Reservation.objects.get(id=reservation_id)
            submission.user = reservation.user
          submission.save()

        if submission.user and submission.user.work_place:
          submission_work_place = models.SurveySubmissionWorkPlace(submission=submission, work_place=submission.user.work_place)
          submission_work_place.save()

        if survey.survey_type == 'B' and reservation_id:
          reservation = models.Reservation.objects.get(id=reservation_id)
          models.ReservationFeedback.objects.get_or_create(reservation=reservation, feedback=submission)
          reservation.feedback_status = 'I'
          reservation.save()


      if page_num <= total_pages:
          surveyComponents = getSurveyComponents(request, survey.id, submission, page_num)
      else:
        raise CustomException('Survey does not have the request page number')

      SurveyResponseFormSet = modelformset_factory(models.SurveyResponse, form=forms.SurveyResponseForm, can_delete=False, can_order=False, extra=0)

      if request.method == 'GET':

        formset = SurveyResponseFormSet(queryset=models.SurveyResponse.objects.filter(submission=submission, survey_component__in=surveyComponents))
        context = {'survey': survey, 'formset': formset, 'submission': submission, 'page_num': page_num, 'total_pages': total_pages}

        if user and user.user_role == 'A' and page_num == 1:
          form = forms.SurveySubmissionForm(instance=submission)
          context['form'] = form

        if survey.survey_type == 'W' and workshop_id:
          context['workshop_id'] = workshop_id
          if user and user.user_role != 'A' and workshop.registration_setting.registration_type == 'R':
            if page_num == 1:
              userProfileForm = forms.WorkshopRegistrationQuestionnaireForm(instance=user, prefix='user-profile')
              context['userProfileForm'] = userProfileForm
              context['photo_release_url'] = settings.PHOTO_RELEASE_URL

            context['workshop'] = workshop

        elif survey.survey_type == 'B' and reservation_id:
          context['reservation_id'] = reservation_id

        return render(request, 'bcse_app/SurveySubmission.html', context)

      elif request.method == 'POST':
        data = request.POST.copy()
        autosave = False
        response_data = {}

        if data['save'][0] == '1':
          autosave = True
        if page_num > 1 and data['back'][0] == '1':
          print('clicking back button')
          response_data['success'] = True
          #go to the previous page
          next_page_num = page_num - 1
          surveyComponents = getSurveyComponents(request, survey.id, submission, next_page_num)
          formset = SurveyResponseFormSet(queryset=models.SurveyResponse.objects.filter(submission=submission, survey_component__in=surveyComponents))
          context = {'survey': survey, 'formset': formset, 'submission': submission, 'page_num': next_page_num, 'total_pages': total_pages}
          if user and user.user_role == 'A' and next_page_num == 1:
            form = forms.SurveySubmissionForm(instance=submission)
            context['form'] = form

          #workshop application
          if survey.survey_type == 'W' and workshop_id:
            context['workshop_id'] = workshop_id
            if user and user.user_role != 'A' and workshop.registration_setting.registration_type == 'R':
              if next_page_num == 1:
                userProfileForm = forms.WorkshopRegistrationQuestionnaireForm(instance=user, prefix='user-profile')
                context['userProfileForm'] = userProfileForm
                context['photo_release_url'] = settings.PHOTO_RELEASE_URL
              context['workshop'] = workshop

          #reservation feedback
          elif survey.survey_type == 'B' and reservation_id:
            context['reservation_id'] = reservation_id

          response_data['html'] = render_to_string('bcse_app/SurveySubmission.html', context, request)
          return http.HttpResponse(json.dumps(response_data), content_type="application/json")

        else:
          #clicking Next or Submit
          recaptcha_token = data.get("recaptchaToken")
          recaptcha_passed = validateReCaptcha(recaptcha_token, 'survey')

          is_valid = False
          formset = SurveyResponseFormSet(data, request.FILES, queryset=models.SurveyResponse.objects.filter(submission=submission, survey_component__in=surveyComponents))
          if user and user.user_role == 'A' and page_num == 1:
            form = forms.SurveySubmissionForm(data, instance=submission)
            if recaptcha_passed and form.is_valid() and formset.is_valid():
              is_valid = True
          elif user and user.user_role != 'A' and page_num == 1 and survey.survey_type == 'W' and workshop_id and workshop.registration_setting.registration_type == 'R':
            userProfileForm = forms.WorkshopRegistrationQuestionnaireForm(data, instance=user, prefix='user-profile')
            if recaptcha_passed and userProfileForm.is_valid() and formset.is_valid():
              is_valid = True
          else:
            if recaptcha_passed and formset.is_valid():
              is_valid = True

          if is_valid:
            if user and user.user_role == 'A' and page_num == 1:
              submission = form.save()
              submission.admin_notes = 'Submission created by admin'
              submission.save()
              if submission.user and submission.user.work_place:
                try:
                  submission_work_place = models.SurveySubmissionWorkPlace.objects.get(submission=submission)
                  submission_work_place.work_place = submission.user.work_place
                  submission_work_place.save()
                except  models.SurveySubmissionWorkPlace.DoesNotExist:
                  submission_work_place = models.SurveySubmissionWorkPlace(submission=submission, work_place=submission.user.work_place)
                  submission_work_place.save()
            elif user and user.user_role != 'A' and page_num == 1 and survey.survey_type == 'W' and workshop_id and workshop.registration_setting.registration_type == 'R':
              userProfileForm.save()
            for response_form in formset:
              response_form.save()

            if autosave:
              print('autosave')
              response_data['success'] = True
              return http.HttpResponse(json.dumps(response_data), content_type="application/json")
            elif page_num < total_pages:
              print('clicking Next')
              messages.success(request, 'Page %s has been saved' % page_num)
              response_data['success'] = True
              #go to the next page
              next_page_num = page_num + 1
              surveyComponents = getSurveyComponents(request, survey.id, submission, next_page_num)
              formset = SurveyResponseFormSet(queryset=models.SurveyResponse.objects.filter(submission=submission, survey_component__in=surveyComponents))
              context = {'survey': survey, 'formset': formset, 'submission': submission, 'page_num': next_page_num, 'total_pages': total_pages}

              #workshop application/questionnaire
              if survey.survey_type == 'W' and workshop_id:
                context['workshop_id'] = workshop_id
                context['workshop'] = workshop
              #reservation feedback
              elif survey.survey_type == 'B' and reservation_id:
                context['reservation_id'] = reservation_id

              response_data['success'] = True
              response_data['html'] = render_to_string('bcse_app/SurveySubmission.html', context, request)
              return http.HttpResponse(json.dumps(response_data), content_type="application/json")
            else:
              ### survey submission
              print('clicking Submit')
              submission.status = 'S'
              submission.save()

              #workshop application
              if survey.survey_type == 'W' and workshop_id:
                registration_setting_status = workshopRegistrationSettingStatus(workshop)
                #get or create registration and set status to default registration status
                try:
                  registration = models.Registration.objects.get(workshop_registration_setting=workshop.registration_setting, user=request.user.userProfile)
                  registration.status = registration_setting_status['default_registration_status']
                  registration.save()
                except models.Registration.DoesNotExist:
                  registration = models.Registration.objects.create(workshop_registration_setting=workshop.registration_setting, user=request.user.userProfile, status=registration_setting_status['default_registration_status'])

                #create registration - workplace association
                if registration.user.work_place:
                  try:
                    registration_work_place = models.RegistrationWorkPlace.objects.get(registration=registration)
                    registration_work_place.work_place = registration.user.work_place
                    registration_work_place.save()
                  except models.RegistrationWorkPlace.DoesNotExist:
                    registration_work_place = models.RegistrationWorkPlace(registration=registration, work_place=registration.user.work_place)
                    registration_work_place.save()


                models.WorkshopApplication.objects.create(registration=registration, application=submission)
                if workshop.registration_setting.registration_type == 'R':
                  messages.success(request, 'Your questionnaire has been submitted')
                else:
                  messages.success(request, 'Your application has been submitted')
              #reservation feedback
              elif survey.survey_type == 'B' and reservation_id:
                reservation = models.Reservation.objects.get(id=reservation_id)
                #reservation feedback submitted
                reservation.feedback_status = 'S'
                reservation.save()
                messages.success(request, 'Your feedback has been submitted')
              #other surveys
              else:
                messages.success(request, 'The survey has been submitted')

              #send survey submission confirmation email
              surveySubmissionEmailSend(request, survey, user, submission)

              if request.is_ajax():
                response_data['success'] = True
                return http.HttpResponse(json.dumps(response_data), content_type="application/json")
              else:
                return shortcuts.redirect('bcse:home')
          else:

            if not recaptcha_passed:
              messages.error(request, 'reCAPTCHA validation failed')

            if user and user.user_role == 'A' and page_num == 1:
              print(form.errors)

            print(formset.errors)
            if autosave:
              response_data['success'] = False
              return http.HttpResponse(json.dumps(response_data), content_type="application/json")
            else:
              messages.error(request, 'Please correct the errors below and resubmit')
              context = {'survey': survey, 'formset': formset, 'submission': submission, 'page_num': page_num, 'total_pages': total_pages}
              if user and user.user_role == 'A' and page_num == 1:
                context['form'] = form

              if survey.survey_type == 'W' and workshop_id:
                context['workshop_id'] = workshop_id
                if user and user.user_role != 'A' and page_num == 1 and workshop.registration_setting.registration_type == 'R':
                  context['userProfileForm'] = userProfileForm
                  context['photo_release_url'] = settings.PHOTO_RELEASE_URL
                  context['workshop'] = workshop

              elif survey.survey_type == 'B' and reservation_id:
                context['reservation_id'] = reservation_id
              response_data['success'] = False
              response_data['html'] = render_to_string('bcse_app/SurveySubmission.html', context, request)
              return http.HttpResponse(json.dumps(response_data), content_type="application/json")

      return http.HttpResponseNotAllowed(['GET', 'POST'])

    else:
      context = {'survey': survey}
      messages.warning(request, "This survey has been closed")
      return render(request, 'bcse_app/SurveySubmission.html', context)

  except models.Survey.DoesNotExist:
    messages.success(request, "Survey not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def surveySubmissionEmailSend(request, survey, user, submission):
  """
  surveySubmissionEmailSend is called from the path 'surveySubmission'
  :param request: request from the browser
  :param survey: the survey that is submitted
  :param user: the user who submitted the survey
  :param submission: the submission object
  :returns
  """
  domain = request.get_host()

  #check if email confirmation needs to be sent to the respondant
  if survey.email_confirmation and survey.email_confirmation_message:
    respondant_emails = []
    #check if email address is available
    if user and user.user.email:
      #user is logged in, so email is available in their profile
      respondant_emails = [user.user.email]
      if user.secondary_email:
        respondant_emails.append(user.secondary_email)
    else:
      #check if email is part of the survey response
      email_responses = models.SurveyResponse.objects.all().filter(submission=submission, survey_component__component_type='EM')
      if email_responses:
        respondant_emails = [email_responses.first().response]

    if respondant_emails:
      filename = "/tmp/survey_%s_submission_%s.xls"% (survey.id, submission.UUID)
      surveySubmissions = models.SurveySubmission.objects.all().filter(UUID=submission.UUID)
      wb = generateSurveySubmissionsExcel(request, survey, surveySubmissions)
      wb.save(filename)

      subject = 'Survey %s submission confirmation' % survey.name

      if domain != 'bcse.northwestern.edu':
        subject = '***** TEST **** '+ subject + ' ***** TEST **** '

      email_body = survey.email_confirmation_message
      context = {'email_body': email_body, 'domain': domain}
      body = get_template('bcse_app/EmailGeneralTemplate.html').render(context)

      email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, respondant_emails)
      email.attach_file(filename, 'application/ms-excel')

      email.content_subtype = "html"
      email.send(fail_silently=True)

  #send confirmation email to admins
  if survey.admin_notification:
    subject = '%s - New Submission' % survey.name

    if domain != 'bcse.northwestern.edu':
      subject = '***** TEST **** '+ subject + ' ***** TEST **** '

    email_body = '%s has submitted <strong>%s</strong> survey.  Please click <a href="https://%s%s">here</a> to review the submission.' % (user.user.get_full_name() if user else 'A user', survey.name, domain, reverse('bcse:surveySubmissionView', args=[survey.id, submission.UUID]))

    context = {'email_body': email_body, 'domain': domain}
    body = get_template('bcse_app/EmailGeneralTemplate.html').render(context)

    email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [settings.DEFAULT_FROM_EMAIL])
    email.content_subtype = "html"
    email.send(fail_silently=True)

def getSurveyComponents(request, survey_id, submission, page_num):
  """
  getSurveyComponents is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param survey_id=='': id of survey to create submission for
  :param submission: user's submission to access components for
  :param page_num='': page number to get survey from
  :returns: the survey component(s)
  :raises models.SurveyComponent.DoesNotExist: redirects user to page they were on before encountering error due to survey component not existing
  """
  try:
    if '' != survey_id and '' != page_num:
      surveyComponents = models.SurveyComponent.objects.all().filter(survey__id=survey_id, page=page_num).order_by('order')

      for surveyComponent in surveyComponents:
        surveyResponse, created = models.SurveyResponse.objects.get_or_create(submission=submission, survey_component=surveyComponent)
        if surveyResponse.response is None:
          surveyResponse.response = ''
          surveyResponse.save()

      return surveyComponents
    else:
      raise models.SurveyComponent.DoesNotExist

  except models.SurveyComponent.DoesNotExist:
    messages.success(request, "Survey Component not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))



##########################################################
# SURVEY SUBMISSION VIEW BY ADMIN
##########################################################
@login_required
def surveySubmissionView(request, id='', submission_uuid=''):
  """
  getSurveyComponents is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param id=='': id of survey to view
  :param submission_uuid='': id of submission to view
  :returns: rendered template 'bcse_app/SurveySubmissionView.html', a page to view a specific survey submission
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
# SURVEY SUBMISSION VIEW IN A MODAL BY ADMIN
##########################################################
@login_required
def surveySubmissionViewModal(request, id='', submission_uuid=''):
  """
  surveySubmissionViewModal is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param id=='': id of survey to view
  :param submission_uuid='': id of submission to view
  :returns: rendered template 'bcse_app/SurveySubmissionViewModal.html', a page to view a specific survey submission
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    survey = models.Survey.objects.get(id=id)
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to view survey submission')
    elif request.user.userProfile.user_role not in ['A', 'S']:
      if survey.survey_type == 'W':
        try:
          workshop = models.Workshop.objects.get(registration_setting__application=survey)
          if request.user.userProfile.id not in workshop.teacher_leaders.all().values_list('teacher__id', flat=True):
            raise CustomException('You do not have the permission to view survey submission')
        except models.Workshop.DoesNotExist:
          raise CustomException('You do not have the permission to view survey submission')
      else:
        raise CustomException('You do not have the permission to view survey submission')

    submission = models.SurveySubmission.objects.get(UUID=submission_uuid, survey=survey)
    surveyResponses = models.SurveyResponse.objects.all().filter(submission=submission).order_by('survey_component__page', 'survey_component__order')
    context = {'survey': survey, 'submission': submission, 'surveyResponses': surveyResponses}
    return render(request, 'bcse_app/SurveySubmissionViewModal.html', context)


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
  """
  surveySubmissionEdit is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param id=='': id of survey to edit
  :param submission_uuid='': id of submission to edit
  :returns: rendered template 'bcse_app/SurveySubmissionEdit.html' or JSON view of all survey submissions
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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
        survey_submission_work_place = form.cleaned_data['work_place']
        savedSubmission = form.save()
        if survey_submission_work_place:
          if hasattr(savedSubmission, 'survey_submission_to_work_place'):
            savedSubmission.survey_submission_to_work_place.work_place = survey_submission_work_place
            savedSubmission.survey_submission_to_work_place.save()
          else:
            models.SurveySubmissionWorkPlace.objects.create(submission=savedSubmission, work_place=survey_submission_work_place)
        else:
          if hasattr(savedSubmission, 'survey_submission_to_work_place'):
            savedSubmission.survey_submission_to_work_place.delete()

        for surveyResponse in savedSubmission.survey_response.all():
          surveyResponse.created_date = savedSubmission.created_date
          surveyResponse.modified_date = savedSubmission.modified_date
          surveyResponse.save()

        messages.success(request, "Survey submission updated.")
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
  """
  surveySubmissionDelete is called from the path 'adminConfiguration/surveys/'
  :param request: request from the browser
  :param id=='': id of survey to delete
  :param submission_uuid='': id of submission to delete
  :returns: page view of remaining survey submissions
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
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


####################################
# VIGNETTES
####################################
def vignettes(request, flag=''):
  """
  vignettes is called from the path 'vignettes/table'
  :param request: request from the browser
  :param flag='': specifies if vignettes are being viewed in table or list view
  :returns: rendered template 'bcse_app/VignettesPublicView.html' or 'bcse_app/VignettesBaseView.html' based on flag value
  :raises CustomException: redirects user to page they were on before encountering error due to lack of permissions
  """
  try:
    if '' == flag:
      flag = 'list'

    if flag == 'table':
      if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
        raise CustomException('You do not have the permission to view vignettes')

    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:

      vignettes = models.Vignette.objects.all().filter(status='A')
      context = {'vignettes': vignettes}
      return render(request, 'bcse_app/VignettesPublicView.html', context)

    else:

      if request.session.get('vignettes_search', False):
        searchForm = forms.VignettesSearchForm(user=request.user, initials=request.session['vignettes_search'], prefix="vignette_search")
        page = request.session['vignettes_search']['page']
      else:
        searchForm = forms.VignettesSearchForm(user=request.user, initials=None, prefix="vignette_search")
        page = 1

      context = {'searchForm': searchForm, 'page': page, 'flag': flag}

      return render(request, 'bcse_app/VignettesBaseView.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################################
# FILTER VIGNETTE LIST BASED ON FILTER CRITERIA
####################################################
def vignettesSearch(request, flag=''):

  try:
    if flag == 'table':
      if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
        raise CustomException('You do not have the permission to search vignettes')

    if request.method == 'GET':

      query_filter = Q()
      title_filter = None
      blurb_filter = None
      featured_filter = None
      status_filter = None

      title = request.GET.get('vignette_search-title', '')
      blurb = request.GET.get('vignette_search-blurb', '')
      featured = request.GET.get('vignette_search-featured', '')
      status = request.GET.get('vignette_search-status', '')
      rows_per_page = request.GET.get('vignette_search-rows_per_page', settings.DEFAULT_ITEMS_PER_PAGE)
      page = request.GET.get('page', '')

      #set session variable
      request.session['vignette_search'] = {
        'title': title,
        'blurb': blurb,
        'featured': featured,
        'status': status,
        'rows_per_page': rows_per_page,
        'page': page
      }

      if title:
        title_filter = Q(title__icontains=title)
        query_filter = title_filter

      if blurb:
        blurb_filter = Q(blurb__icontains=blurb)
        query_filter = query_filter & blurb_filter

      if featured:
        if featured == 'Y':
          featured_filter = Q(featured=True)
        elif featured == 'N':
          featured_filter = Q(featured=False)

        query_filter = query_filter & featured_filter

      if status:
        status_filter = Q(status=status)
        query_filter = query_filter & status_filter
      elif request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
        status_filter = Q(status='A')
        query_filter = query_filter & status_filter

      vignettes = models.Vignette.objects.all().filter(query_filter)

      direction = request.GET.get('direction') or 'asc'
      ignorecase = request.GET.get('ignorecase') or 'false'

      order_by = 'order'

      sort_order = [{'order_by': order_by, 'direction': direction, 'ignorecase': ignorecase}]

      vignettes = paginate(request, vignettes, sort_order, rows_per_page, page)

      context = {'vignettes': vignettes}
      response_data = {}
      response_data['success'] = True
      if flag == 'table':
        response_data['html'] = render_to_string('bcse_app/VignettesTableView.html', context, request)
      else:
        response_data['html'] = render_to_string('bcse_app/VignettesTileView.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

##########################################################
# EDIT VIGNETTE
##########################################################
@login_required
def vignetteEdit(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit vignette')

    if '' != id:
      vignette = models.Vignette.objects.get(id=id)
    else:
      vignette = models.Vignette()

    if request.method == 'GET':
      form = forms.VignetteForm(instance=vignette)
      context = {'form': form}
      return render(request, 'bcse_app/VignetteEdit.html', context)
    elif request.method == 'POST':
      data = request.POST.copy()
      form = forms.VignetteForm(data, files=request.FILES, instance=vignette)
      response_data = {}
      if form.is_valid():
        savedVignette = form.save()
        messages.success(request, "Vignette saved successfully")
        response_data['success'] = True
      else:
        print(form.errors)
        context = {'form': form}
        response_data['success'] = False
        response_data['html'] = render_to_string('bcse_app/VignetteEdit.html', context, request)

      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


##########################################################
# DELETE VIGNETTE
##########################################################
@login_required
def vignetteDelete(request, id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to delete vignette')
    if '' != id:
      vignette = models.Vignette.objects.get(id=id)
      vignette.delete()
      messages.success(request, "Vignette deleted")

    return shortcuts.redirect('bcse:vignettes')

  except models.Vignette.DoesNotExist:
    messages.success(request, "Vignette not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


#########################################################
# VIEW VIGNETTE
##########################################################
def vignetteView(request, id=''):

  try:
    if '' != id:
      vignette = models.Vignette.objects.get(id=id)
      context = {'vignette': vignette}
      return render(request, 'bcse_app/VignetteViewModal.html', context)
    else:
      raise models.Vignette.DoesNotExist

  except models.Vignette.DoesNotExist:
    messages.success(request, "Vignette not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


####################################
# CLONE VIGNETTE
####################################
def vignetteCopy(request, id=''):
  try:

    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to copy this vignette')
    if '' != id:
      vignette = models.Vignette.objects.get(id=id)
      title = vignette.title
      vignette.pk = None
      vignette.id = None
      vignette.image = None
      vignette.save()

      original_vignette = models.Vignette.objects.get(id=id)
      vignette.title = 'Copy of ' + title
      vignette.created_date = datetime.datetime.now()
      vignette.modified_date = datetime.datetime.now()

      if original_vignette.image:
        try:
          source = original_vignette.image
          filecontent = ContentFile(source.file.read())
          filename = os.path.split(source.file.name)[-1]
          filename_array = filename.split('.')
          new_filename = filename_array[0] + '-' + str(vignette.id) + '.' + filename_array[1]
          vignette.image.save(new_filename, filecontent)
          vignette.save()
          source.file.close()
          original_vignette.image.save(filename, filecontent)
          original_vignette.save()
        except IOError as e:
          vignette.save()
      else:
        vignette.save()

      messages.success(request, "Vignette copied")
      return shortcuts.redirect('bcse:vignetteEdit', id=vignette.id)

    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


  except models.Vignette.DoesNotExist:
    messages.success(request, "Vignette not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def teacherLeadershipOpportunities(request):

  try:
    vignettes = models.Vignette.objects.all().filter(status='A', featured=True)
    context = {'vignettes': vignettes}
    return render(request, 'bcse_app/TeacherLeadershipOpportunities.html', context)

  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

########################################################################
# PAGINATE THE QUERYSET BASED ON THE ITEMS PER PAGE AND SORT ORDER
########################################################################
def paginate(request, queryset, sort_order, count=settings.DEFAULT_ITEMS_PER_PAGE, page=1):

  ordering_list = []

  if sort_order:
    for order in sort_order:
      order_by = order['order_by']
      direction = order['direction']
      ignorecase = order['ignorecase']

      ordering = order_by

      if type(queryset) is list:
        ordering_list.append((order_by, direction, ignorecase))
      else:

        if ignorecase == 'true':
          ordering = Lower(ordering)
          if direction == 'desc':
            ordering = ordering.desc(nulls_last=True)
        else:
          if direction == 'desc':
            #ordering = '-{}'.format(ordering)
            ordering = F(ordering).desc(nulls_last=True)

        ordering_list.append(ordering)

    if type(queryset) is list:
      for order_by, direction, ignorecase in reversed(ordering_list):
        reverse = direction == 'desc'
        queryset = sorted(queryset, key=lambda x: x.get(order_by).lower() if ignorecase == 'true' else x.get(order_by), reverse=reverse)
    else:
      queryset = queryset.order_by(*ordering_list)

  if int(count) > 0:
    paginator = Paginator(queryset, count)
  elif type(queryset) is list:
    if len(queryset) > 0:
      paginator = Paginator(queryset, len(queryset))
    else:
      paginator = Paginator(queryset, settings.DEFAULT_ITEMS_PER_PAGE)
  elif queryset.count() > 0:
    paginator = Paginator(queryset, queryset.count())
  else:
    paginator = Paginator(queryset, settings.DEFAULT_ITEMS_PER_PAGE)

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
def subscription(userDetails, status, subscriber_hash=None):
  api_key = settings.MAILCHIMP_API_KEY
  server = settings.MAILCHIMP_DATA_CENTER
  list_id = settings.MAILCHIMP_EMAIL_LIST_ID

  mailchimp = Client()
  mailchimp.set_config({
      "api_key": api_key,
      "server": server,
  })

  try:
    member_info = {
      "email_address": userDetails['email_address'],
      "merge_fields": {"FNAME": userDetails['first_name'], "LNAME": userDetails['last_name']},
      "status": "subscribed",
    }
    if not subscriber_hash:
      subscriber_hash = hashlib.md5(userDetails['email_address'].lower().encode("utf-8")).hexdigest()

    try:
      #first delete
      #if contact does not exist, this will throw an exception
      delete_response = mailchimp.lists.delete_list_member(list_id, subscriber_hash)
      #print("delete response: {}".format(delete_response))
    except ApiClientError as error:
      print("An exception occurred: {}".format(error.text))
      pass

    # if not delete then add user back
    if status != 'delete':
      if 'phone_number' in userDetails:
        member_info['merge_fields']['PHONE'] = userDetails['phone_number']

      add_response = mailchimp.lists.add_list_member(list_id, member_info)
      #print("add response: {}".format(add_response))

  except ApiClientError as error:
    print("An exception occurred: {}".format(error.text))

#####################################################
# SEND A CONFIRMATION EMAIL TO ADMINS AND THE USER
# WHEN A RESERVATION IS CONFIRMED
#####################################################
def reservationConfirmationEmailSend(request, id):
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to send reservation email')

    reservation = models.Reservation.objects.get(id=id)
    if request.user.userProfile.user_role in ['T', 'P'] and reservation.user != request.user.userProfile:
      raise CustomException('You do not have the permission to send reservation email')

    domain = request.get_host()
    subject = 'Baxter Box Reservation Confirmed for %s' % reservation.get_activity_name()
    if domain != 'bcse.northwestern.edu':
      subject = '***** TEST **** '+ subject + ' ***** TEST **** '

    context = {'reservation': reservation, 'domain': domain}
    body = get_template('bcse_app/EmailReservationConfirmation.html').render(context)
    qs = models.UserProfile.objects.all().filter(Q(user__email='bcse@northwestern.edu') | Q(id=reservation.user.id)).values_list('user__email', 'secondary_email')
    receipients = [email for email in chain.from_iterable(qs) if email]
    email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, receipients)
    email.content_subtype = "html"
    success = email.send(fail_silently=True)
    if success:
      reservation.email_sent = True
      if reservation.confirmation_email_dates:
        reservation.confirmation_email_dates+= '<br> %s' % datetime.datetime.now().strftime('%B %d, %Y %I:%M:%S %p')
      else:
        reservation.confirmation_email_dates = '%s' % datetime.datetime.now().strftime('%B %d, %Y %I:%M:%S %p')
      reservation.save()

    if request.is_ajax():
      response_data = {}
      if success:
        response_data['success'] = True
        response_data['message'] = 'Reservation confirmation email sent'
      else:
        response_data['success'] = False
        response_data['message'] = 'Reservation confirmation email could not be sent'
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  except models.Reservation.DoesNotExist as e:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, 'Reservation not found')
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % 'Reservation not found')
  except CustomException as ce:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, ce)
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % ce)

#####################################################
# SEND A CANCELLATION EMAIL TO ADMINS AND THE USER
# WHEN A RESERVATION IS cancelled
#####################################################
def reservationCancellationEmailSend(request, id):
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to send reservation email')

    reservation = models.Reservation.objects.get(id=id)
    if reservation.status != 'N':
      raise CustomException("This reservation isn't cancelled")

    if request.user.userProfile.user_role in ['T', 'P'] and reservation.user != request.user.userProfile:
      raise CustomException('You do not have the permission to send reservation email')

    domain = request.get_host()
    subject = 'Baxter Box Reservation Cancelled for %s' % reservation.get_activity_name()
    if domain != 'bcse.northwestern.edu':
      subject = '***** TEST **** '+ subject + ' ***** TEST **** '

    context = {'reservation': reservation, 'domain': domain, 'user_role': 'A', 'activity': reservation.get_activity_name()}

    body = get_template('bcse_app/EmailReservationCancellation.html').render(context)
    qs = models.UserProfile.objects.all().filter(user__email='bcse@northwestern.edu').values_list('user__email', 'secondary_email')
    receipients = [email for email in chain.from_iterable(qs) if email]
    email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, receipients)
    email.content_subtype = "html"
    success = email.send(fail_silently=True)

    context['user_role'] = 'T'
    body = get_template('bcse_app/EmailReservationCancellation.html').render(context)
    qs = models.UserProfile.objects.all().filter(id=reservation.user.id).values_list('user__email', 'secondary_email')
    receipients = [email for email in chain.from_iterable(qs) if email]
    email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, receipients)
    email.content_subtype = "html"
    success = email.send(fail_silently=True)


    if request.is_ajax():
      response_data = {}
      if success:
        response_data['success'] = True
        response_data['message'] = 'Reservation cancellation email sent'
      else:
        response_data['success'] = False
        response_data['message'] = 'Reservation cancellation email could not be sent'
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  except models.Reservation.DoesNotExist as e:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, 'Reservation not found')
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % 'Reservation not found')
  except CustomException as ce:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, ce)
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % ce)

#####################################################
# VIEW RESERVATION CONFIRMATION EMAIL TEMPLATE
#####################################################
def reservationConfirmationEmailView(request, id):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role in ['T', 'P']:
      raise CustomException('You do not have the permission to view reservation email')

    reservation = models.Reservation.objects.get(id=id)

    domain = request.get_host()
    subject = 'Baxter Box Reservation Confirmed'
    if domain != 'bcse.northwestern.edu':
      subject = '***** TEST **** '+ subject + ' ***** TEST **** '
    context = {'reservation': reservation, 'domain': domain, 'subject': subject}

    return render(request, 'bcse_app/EmailReservationConfirmationView.html', context)

  except models.Reservation.DoesNotExist as e:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, 'Reservation not found')
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % 'Reservation not found')
  except CustomException as ce:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, ce)
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % ce)

#####################################################
# PREVIEW RESERVATION DELIVERY/PICKUP EMAIL
#####################################################
def reservationDeliveryPickupEmailView(request, reservation_id, email_type=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role in ['T', 'P']:
      raise CustomException('You do not have the permission to view reservation email')

    reservation = models.Reservation.objects.get(id=reservation_id)
    email_template = models.ReservationDeliveryPickupEmailTemplate.objects.get(delivery_or_pickup=email_type)
    try:
      email = models.ReservationDeliveryPickupEmail.objects.get(reservation=reservation, delivery_or_pickup=email_type)
      subject = email.email_subject
      email_message = email.email_message
    except models.ReservationDeliveryPickupEmail.DoesNotExist as e:
      subject = email_template.email_subject
      email_message = email_template.email_message


    domain = request.get_host()
    if domain != 'bcse.northwestern.edu':
      subject = '***** TEST **** '+ subject + ' ***** TEST **** '
    context = {'subject': subject, 'email_message': email_message}

    return render(request, 'bcse_app/EmailReservationDeliveryPickupView.html', context)

  except models.Reservation.DoesNotExist as e:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, 'Reservation not found')
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % 'Reservation not found')
  except models.ReservationDeliveryPickupEmailTemplate.DoesNotExist as e:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, 'Reservation Email Template not found')
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % 'Reservation email not found')
  except CustomException as ce:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, ce)
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % ce)

#####################################################
# SEND RESERVATION DELIVERY OR PICK UP EMAIL
#####################################################
def reservationDeliveryPickupEmailSend(request, reservation_id, email_type=''):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to send feedback email')

    reservation = models.Reservation.objects.get(id=reservation_id)
    if reservation.status not in ['R', 'I']:
      raise CustomException('The reservation status is not Checked Out or Completed, so the delivery/pickup email cannot be sent')
    email_template = models.ReservationDeliveryPickupEmailTemplate.objects.get(delivery_or_pickup=email_type)
    try:
      email = models.ReservationDeliveryPickupEmail.objects.get(reservation=reservation, delivery_or_pickup=email_type)
      subject = email.email_subject
      email_message = email.email_message
    except models.ReservationDeliveryPickupEmail.DoesNotExist as e:
      subject = email_template.email_subject
      email_message = email_template.email_message


    domain = request.get_host()
    if domain != 'bcse.northwestern.edu':
      subject = '***** TEST **** '+ subject + ' ***** TEST **** '
    context = {'subject': subject, 'email_message': email_message}

    body = get_template('bcse_app/EmailReservationDeliveryPickup.html').render(context)
    qs = models.UserProfile.objects.all().filter(Q(user__email='bcse@northwestern.edu') | Q(id=reservation.user.id)).values_list('user__email', 'secondary_email')
    receipients = [email for email in chain.from_iterable(qs) if email]

    email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, receipients)
    email.content_subtype = "html"
    success = email.send(fail_silently=True)
    if request.is_ajax():
      response_data = {}
      if success:
        response_data['success'] = True
        response_data['message'] = 'Reservation %s email sent' % ('Delivery' if email_type == 'D' else 'Pickup')
      else:
        response_data['success'] = False
        response_data['message'] = 'Reservation %s email could not be sent' % ('Delivery' if email_type == 'D' else 'Pickup')
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  except models.Reservation.DoesNotExist as e:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, 'Reservation not found')
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % 'Reservation not found')
  except models.ReservationDeliveryPickupEmailTemplate.DoesNotExist as e:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, 'Reservation Email Template not found')
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % 'Reservation email not found')
  except CustomException as ce:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, ce)
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % ce)

#####################################################
# SEND FEEDBACK REQUEST EMAIL TO THE USER
# AFTER A RESERVATION IS CHECKED OUT OR COMPLETED
#####################################################
def reservationFeedbackEmailSend(request, id):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to send feedback email')

    reservation = models.Reservation.objects.get(id=id)
    survey = models.Survey.objects.all().filter(status='A', survey_type='B').first()
    if not survey:
      raise CustomException('Baxter Box Feedback Survey not found')

    domain = request.get_host()
    subject = 'How was %s?' % reservation.get_activity_name()
    if domain != 'bcse.northwestern.edu':
      subject = '***** TEST **** '+ subject + ' ***** TEST **** '

    context = {'reservation': reservation, 'survey': survey, 'domain': domain}

    body = get_template('bcse_app/EmailReservationFeedbackRequest.html').render(context)
    qs = models.UserProfile.objects.all().filter(Q(user__email='bcse@northwestern.edu') | Q(id=reservation.user.id)).values_list('user__email', 'secondary_email')
    receipients = [email for email in chain.from_iterable(qs) if email]

    email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, receipients)
    email.content_subtype = "html"
    success = email.send(fail_silently=True)
    if success:
      if reservation.feedback_status is None:
        reservation.feedback_status = 'E'
      if reservation.feedback_email_count:
        reservation.feedback_email_count = reservation.feedback_email_count + 1
      else:
        reservation.feedback_email_count = 1
      reservation.feedback_email_date = datetime.datetime.now()
      reservation.save()

    if request.is_ajax():
      response_data = {}
      if success:
        response_data['success'] = True
        response_data['message'] = 'Reservation feedback request email sent'
      else:
        response_data['success'] = False
        response_data['message'] = 'Reservation feedback request email could not be sent'
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  except models.Reservation.DoesNotExist as e:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, 'Reservation not found')
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % 'Reservation not found')
  except CustomException as ce:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, ce)
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % ce)


#####################################################
# SEND A RECEIPT EMAIL TO ADMINS AND THE USER
# WHEN A NEW RESERVATIONIS MADE
#####################################################
def reservationReceiptEmailSend(request, id):
  try:
    if request.user.is_anonymous:
      raise CustomException('You do not have the permission to send reservation email')

    reservation = models.Reservation.objects.get(id=id)
    if request.user.userProfile.user_role in ['T', 'P'] and reservation.user != request.user.userProfile:
      raise CustomException('You do not have the permission to send reservation email')

    domain = request.get_host()
    subject = 'Baxter Box Request Received for %s' % reservation.get_activity_name()
    if domain != 'bcse.northwestern.edu':
      subject = '***** TEST **** '+ subject + ' ***** TEST **** '

    context = {'reservation': reservation, 'domain': domain}
    body = get_template('bcse_app/EmailReservationRequest.html').render(context)
    qs = models.UserProfile.objects.all().filter(Q(user__email='bcse@northwestern.edu') | Q(id=reservation.user.id)).values_list('user__email', 'secondary_email')
    receipients = [email for email in chain.from_iterable(qs) if email]

    email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, receipients)
    email.content_subtype = "html"
    success = email.send(fail_silently=True)

    if request.is_ajax():
      response_data = {}
      if success:
        response_data['success'] = True
        response_data['message'] = 'Reservation receipt email sent'
      else:
        response_data['success'] = False
        response_data['message'] = 'Reservation receipt email could not be sent'
      return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  except models.Reservation.DoesNotExist as e:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, 'Reservation not found')
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % 'Reservation not found')
  except CustomException as ce:
    if request.META.get('HTTP_REFERER'):
      messages.error(request, ce)
      return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
    else:
      return http.HttpResponseNotFound('<h1>%s</h1>' % ce)
#####################################################
# SEND A NOTIFICATION EMAIL TO ADMINS AND THE USER
# WHEN A NEW MESSAGE IS POSTED FOR A RESERVATION
#####################################################
def send_reservation_message_email(request, reservation_message):
  domain = request.get_host()
  subject = 'New message about your Baxter Box Reservation for %s' % reservation_message.reservation.get_activity_name()
  if domain != 'bcse.northwestern.edu':
    subject = '***** TEST **** '+ subject + ' ***** TEST **** '

  context = {'reservation_message': reservation_message, 'domain': domain}
  body = get_template('bcse_app/EmailNewMessage.html').render(context)
  qs = models.UserProfile.objects.all().filter(Q(user__email='bcse@northwestern.edu') | Q(id=reservation_message.reservation.user.id)).exclude(id=reservation_message.created_by.id).values_list('user__email', 'secondary_email')
  receipients = [email for email in chain.from_iterable(qs) if email]

  email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, receipients)
  email.content_subtype = "html"
  email.send(fail_silently=True)


#####################################################
# CREATE A NEW USER WITH RANDOM PASSWORD
#####################################################
def create_user(request, email, first_name, last_name, user_role, phone_number, twitter_handle, instagram_handle, name_pronounciation, dietary_preference, photo_release_complete, iein, admin_notes, workplace_id):
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
  if name_pronounciation:
    newUser.name_pronounciation = name_pronounciation
  if dietary_preference:
    newUser.dietary_preference = dietary_preference
  if photo_release_complete:
    if photo_release_complete == 'Yes':
      newUser.photo_release_complete = True
    else:
      newUser.photo_release_complete = False
  if iein:
    newUser.iein = iein
  if admin_notes:
    newUser.admin_notes = admin_notes
  if workplace_id and isinstance(workplace_id, int):
    try:
      work_place = models.WorkPlace.objects.get(id=workplace_id)
      newUser.work_place = work_place
    except models.WorkPlace.DoesNotExist:
      pass
  newUser.user = user
  newUser.validation_code = get_random_string(length=5)
  newUser.save()

  return newUser


#####################################################
# CREATE A WORKSHOP REGISTRATION RECORD FOR A USER
#####################################################
def create_registration(request, email, workshop_id, registration_status=None):
  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to create registration')

    workshop = models.Workshop.objects.get(id=workshop_id)
    if workshop.enable_registration and workshop.registration_setting and workshop.registration_setting.registration_type:
      if workshop.registration_setting.registration_type == 'R':
        default_registration_status = 'R'
      elif workshop.registration_setting.registration_type == 'A':
        default_registration_status = 'A'
      else:
        default_registration_status = 'T'
    else:
      raise CustomException('Please enable registration and select a Registration Type for this workshop before creating registration.')

    if registration_status is None:
      registration_status = default_registration_status

    user = models.UserProfile.objects.get(user__email=email.lower())
    try:
      workshop_registration = models.Registration.objects.get(workshop_registration_setting=workshop.registration_setting, user=user)
      created = False
    except models.Registration.DoesNotExist:
      workshop_registration = models.Registration.objects.create(workshop_registration_setting=workshop.registration_setting, status=registration_status, user=user)
      created = True
      if user.work_place:
        registration_work_place = models.RegistrationWorkPlace(registration=workshop_registration, work_place=user.work_place)
        registration_work_place.save()

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

#####################################################
# LOAD MAPPED EQUIPMENT FOR THE SELECTED ACTIVITY
#####################################################
def load_equipment_options(request, activity_id=''):
  try:
    if request.method == 'GET':
      if request.user.is_anonymous:
        raise CustomException('You do not have the permission load equipment')

      if request.user.userProfile.user_role in ['T', 'P'] and '' != activity_id:
        activity = models.Activity.objects.get(id=activity_id)
        equipment = activity.equipment_mapping.all().filter(status='A', equipment__status='A').distinct().order_by('order')
      else:
        equipment = models.EquipmentType.objects.all().filter(status='A', equipment__status='A').distinct().order_by('order')

      context = {'equipment': equipment}
      html = render_to_string('bcse_app/EquipmentSelectionOptions.html', context, request)
      if '' != activity_id:
        return html
      else:
        response_data = {}
        response_data['success'] = True
        response_data['html'] = html
        return http.HttpResponse(json.dumps(response_data), content_type="application/json")

    return http.HttpResponseNotAllowed(['GET'])

  except models.Activity.DoesNotExist as e:
    messages.error(request, 'Activity not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


#####################################################
# LOAD MAPPED CONSUMABLES FOR THE SELECTED ACTIVITY
#####################################################
def load_consumable_options(request, activity_id=''):
  try:
    if request.method == 'GET':
      if request.user.is_anonymous or request.user.userProfile.user_role in ['T', 'P']:
        raise CustomException('You do not have the permission load consumables')

      activity = models.Activity.objects.get(id=activity_id)
      consumables = activity.consumables.all().filter(status='A').distinct()

      context = {'consumables': consumables}
      html = render_to_string('bcse_app/ConsumableSelectionOptions.html', context, request)
      return html

    return http.HttpResponseNotAllowed(['GET'])

  except models.Activity.DoesNotExist as e:
    messages.error(request, 'Activity not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

#####################################################
# TERMS OF USE
#####################################################
def termsOfUse(request):
  context = {}
  return render(request, 'bcse_app/TermsOfUse.html', context)

#####################################################
# USERS AUTOCOMPLETE
#####################################################
class UserAutocomplete(autocomplete.Select2QuerySetView):
  def get_queryset(self):
    qs = models.UserProfile.objects.all().filter(user__is_active=True).order_by('user__last_name', 'user__first_name')
    if self.q:
      qs = qs.filter(Q(user__last_name__icontains=self.q) | Q(user__first_name__icontains=self.q) | Q(user__email__icontains=self.q) | Q(user__userProfile__secondary_email__icontains=self.q))

    return qs


#####################################################
# FACILITATOR AUTOCOMPLETE
#####################################################
class FacilitatorAutocomplete(autocomplete.Select2QuerySetView):
  def get_queryset(self):
    existing_facilitators = models.TeacherLeader.objects.all().values_list('teacher', flat=True)
    qs = models.UserProfile.objects.all().filter(user__is_active=True, user_role__in=['T', 'P']).exclude(id__in=existing_facilitators).order_by('user__last_name', 'user__first_name')
    if self.q:
      qs = qs.filter(Q(user__last_name__icontains=self.q) | Q(user__first_name__icontains=self.q))

    return qs

#####################################################
# REGISTRANTS AUTOCOMPLETE
#####################################################
class RegistrantAutocomplete(autocomplete.Select2QuerySetView):
  def get_queryset(self):
    workshop_registration_setting = self.forwarded.get('workshop_registration_setting', None)
    print(workshop_registration_setting)
    if workshop_registration_setting:
      #registered_users = models.Registration.objects.all().filter(workshop_registration_setting=workshop_registration_setting).values_list('user', flat=True)
      qs = models.UserProfile.objects.all().filter(user__is_active=True).order_by('user__last_name', 'user__first_name')

      if self.q:
        qs = qs.filter(Q(user__last_name__icontains=self.q) | Q(user__first_name__icontains=self.q) | Q(user__email__icontains=self.q) | Q(user__userProfile__secondary_email__icontains=self.q))
    else:
      qs = models.UserProfile.objects.none()

    return qs

#####################################################
# WORKPLACE AUTOCOMPLETE
#####################################################
class WorkplaceAutocomplete(autocomplete.Select2QuerySetView):
  def get_queryset(self):
    qs = models.WorkPlace.objects.all().filter(status='A').order_by('name')
    if self.q:
      qs = qs.filter(name__icontains=self.q)

    return qs

#####################################################
# ALL WORKPLACE AUTOCOMPLETE
#####################################################
class WorkplaceAllAutocomplete(autocomplete.Select2QuerySetView):
  def get_queryset(self):
    qs = models.WorkPlace.objects.all().order_by('name')
    if self.q:
      qs = qs.filter(name__icontains=self.q)

    return qs

################################
# REMOVE HTML TAGS FROM STRING
################################
def remove_html_tags(request, text):
  html_re = re.compile(r'<[^>]+>')
  text_re = html_re.sub('', text)
  plain_text = html.unescape(text_re)
  return plain_text

################################
# CHECK IF USER PROFILE NEEDS TO BE UPDATED
################################
@login_required
def profile_update_required(userProfile):
  if settings.REQUIRE_PROFILE_UPDATE:

    profile_modified = userProfile.modified_date

    current_month = datetime.datetime.now().month
    current_year = datetime.datetime.now().year
    cutoff_month = settings.PROFILE_UPDATE_CUTOFF_MONTH
    cutoff_day = settings.PROFILE_UPDATE_CUTOFF_DAY

    if current_month >= int(cutoff_month) and current_month <=12:
      cutoff_date = datetime.datetime.strptime("%s-%s-%s 00:00"%(current_year, cutoff_month, cutoff_day), "%Y-%m-%d %H:%M").replace(tzinfo=pytz.timezone(settings.TIME_ZONE))
    else:
      cutoff_date = datetime.datetime.strptime("%s-%s-%s 00:00"%(current_year-1, cutoff_month, cutoff_day), "%Y-%m-%d %H:%M").replace(tzinfo=pytz.timezone(settings.TIME_ZONE))

    if userProfile.work_place.id == models.get_placeholder_workplace():
      return True
    elif profile_modified < cutoff_date:
      return True
    else:
      return False

  else:
    return False

def send_workshop_email(id=id, cron=False):
  message = None
  if '' != id:
    workshop_email = models.WorkshopEmail.objects.get(id=id)
    workshop_id = workshop_email.workshop.id
    workshop = models.Workshop.objects.get(id=workshop_id)

    if workshop_email.email_subject and workshop_email.email_message:

      #get the receipients
      registration_email_addresses = None
      if workshop_email.registration_status or workshop_email.registration_sub_status:
        query_filter = Q(workshop_registration_setting__workshop__id=workshop_id)

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

      email_to = [settings.DEFAULT_FROM_EMAIL]
      if workshop_email.email_to:
        email_to = email_to + workshop_email.email_to.split(';')

      email_cc = []
      if workshop_email.email_cc:
        email_cc = workshop_email.email_cc.split(';')

      email_bcc = []
      if workshop_email.email_bcc:
        email_bcc = workshop_email.email_bcc.split(';')

      if registration_email_addresses or email_to or email_cc or email_bcc:

        if registration_email_addresses:
          email_bcc += registration_email_addresses

        domain = request.get_host()

        subject = workshop_email.email_subject
        subject = models.replace_workshop_tokens(subject, workshop)

        if domain != 'bcse.northwestern.edu':
          subject = '***** TEST **** '+ subject + ' ***** TEST **** '

        email_body = workshop_email.email_message
        email_body = models.replace_workshop_tokens(email_body, workshop)
        context = {'email_body': email_body, 'domain': domain}
        body = get_template('bcse_app/EmailGeneralTemplate.html').render(context)

        if len(email_to) + len(email_cc) + len(email_bcc) <= 50:
          email = EmailMessage(subject=subject, body=body, from_email=settings.DEFAULT_FROM_EMAIL, to=email_to, cc=email_cc, bcc=email_bcc)
          email.content_subtype = "html"
          sent = email.send(fail_silently=True)
        else:

          if len(email_to) > 0:
            if len(email_to) <= 50:
              email = EmailMessage(subject=subject, body=body, from_email=settings.DEFAULT_FROM_EMAIL, to=email_to)
              email.content_subtype = "html"
              sent = email.send(fail_silently=True)
            else:
              for i in range(0, len(email_to), 50):
                email = EmailMessage(subject=subject, body=body, from_email=settings.DEFAULT_FROM_EMAIL, to=email_to[i:i+50])
                email.content_subtype = "html"
                sent = email.send(fail_silently=True)

          if len(email_cc) > 0:
            if len(email_cc) <= 50:
              email = EmailMessage(subject=subject, body=body, from_email=settings.DEFAULT_FROM_EMAIL, cc=email_cc)
              email.content_subtype = "html"
              sent = email.send(fail_silently=True)
            else:
              for i in range(0, len(email_cc), 50):
                email = EmailMessage(subject=subject, body=body, from_email=settings.DEFAULT_FROM_EMAIL, cc=email_cc[i:i+50])
                email.content_subtype = "html"
                sent = email.send(fail_silently=True)

          if len(email_bcc) > 0:
            if len(email_bcc) <= 50:
              email = EmailMessage(subject=subject, body=body, from_email=settings.DEFAULT_FROM_EMAIL, bcc=email_bcc)
              email.content_subtype = "html"
              sent = email.send(fail_silently=True)
            else:
              for i in range(0, len(email_bcc), 50):
                email = EmailMessage(subject=subject, body=body, from_email=settings.DEFAULT_FROM_EMAIL, bcc=email_bcc[i:i+50])
                email.content_subtype = "html"
                sent = email.send(fail_silently=True)


        if sent:
          workshop_email.email_status = 'S'
          workshop_email.sent_date = datetime.datetime.now()
          if registration_email_addresses:
            workshop_email.registration_email_addresses = ';'.join(registration_email_addresses)
          workshop_email.save()
          message = (True, 'The email message with id %s has been sent' % id)
        else:
          message = (False, 'The email message with id %s could not be sent' % id)
      else:
        message = (False, 'The email message with id %s has no receipients' % id)
    else:
      message = (False, 'The email message with id %s has missing fields and cannot be sent' % id)
  else:
    message = (False, 'The email message id not provided')

  return message
