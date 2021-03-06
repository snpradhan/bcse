from django.shortcuts import render
from bcse_app import models, forms
from bcse_app.exceptions import CustomException
from django import http, shortcuts, template
from django.contrib import auth, messages
from django.contrib.auth.models import User
from django.db.models import Q, F
import datetime
from .utils import Calendar
import calendar
from dateutil.relativedelta import relativedelta
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.template.loader import render_to_string, get_template
import json
import csv
from django.utils.crypto import get_random_string

# Create your views here.

from django.http import HttpResponse


####################################
# USER LOGIN
####################################
def userSignin(request, user_name=''):
  username = password = ''
  print(request.method)
  redirect_url = request.GET.get('next', '')
  if request.method == 'POST':
    data = request.POST.copy()
    form = forms.SignInForm(data)
    response_data = {}
    if form.is_valid():
      username_email = form.cleaned_data['username_email'].lower()
      password = form.cleaned_data['password']
      username = None
      if User.objects.filter(username__iexact=username_email).count() == 1:
        username = username_email
      elif User.objects.filter(email__iexact=username_email).count() == 1:
        username = User.objects.get(email__iexact=username_email).username.lower()
      user = authenticate(username=username, password=password)

      if user.is_active:
        login(request, user)
        messages.success(request, "You have signed in")
        response_data['success'] = True
        response_data['redirect_url'] = '/'
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
    if user_name:
      form = forms.SignInForm(initial={'username_email': user_name})
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

    if request.user.is_anonymous or hasattr(request.user, 'administrator'):
      form = forms.SignUpForm(user=request.user)
      work_place_form = forms.WorkPlaceForm(instance=work_place, prefix='work_place')
      context = {'form': form, 'work_place_form': work_place_form}

    return render(request, 'bcse_app/SignUpModal.html', context)

  elif request.method == 'POST':
    new_work_place = None
    response_data = {}

    form = forms.SignUpForm(user=request.user, data=request.POST)
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

      #convert username to lowercase
      username = form.cleaned_data['username'].lower()
      user = User.objects.create_user(username,
                                      form.cleaned_data['email'].lower(),
                                      form.cleaned_data['password1'])
      user.first_name = form.cleaned_data['first_name']
      user.last_name = form.cleaned_data['last_name']
      #Admin, Researcher, Author, School Admin or Teacher account created by anonymous user is set as inactive
      if form.cleaned_data['account_type'] in  ['A', 'T', 'P', 'S'] and request.user.is_anonymous:
          user.is_active = False
      else:
          user.is_active = True
      user.save()

      role = ''
      newUser = models.UserProfile()
      if form.cleaned_data['account_type'] == 'T' or form.cleaned_data['account_type'] == 'P':
        newUser.validation_code = get_random_string(length=5)

        #get the work place id
        selected_work_place = form.cleaned_data['work_place']
        new_work_place_flag = form.cleaned_data['new_work_place']
        if new_work_place:
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
            context = {'form': form, 'work_place_form': work_place_form}
            response_data['success'] = False
            response_data['html'] = render_to_string('bcse_app/SignUpModal.html', context, request)
            return http.HttpResponse(json.dumps(response_data), content_type="application/json")
        else:
          newUser.work_place = form.cleaned_data['work_place']
        newUser.user = user
        newUser.save()

      # Admin or Staff account creation
      elif form.cleaned_data['account_type'] in ['A', 'S']:
        newUser.user = user
        newUser.save()


      current_site = Site.objects.get_current()
      domain = current_site.domain

      #anonymous user creates an account
      if request.user.is_anonymous:

        #account type created is Teacher or Professional
        if form.cleaned_data['account_type'] in ['T', 'P']:
          #send an email with the username and validation code to validate the account
          #send_account_validation_email(newUser)
          response_data['success'] = True
          response_data['message'] = 'An email has been sent to %s to validate your account.  Please validate your account with in 24 hours.' % newUser.user.email

        else:
          response_data['success'] = False
          messages.error(request, 'Sorry you cannot create this user account')

        response_data['redirect_url'] = '/'

      else:
        response_data['message'] = '%s account has been created.' % newUser.get_user_role_display()
        #send_account_by_admin_confirmation_email(newUser, form.cleaned_data['password1'])
        url = '/'

        response_data['success'] = True
        response_data['redirect_url'] = url

    else:
      print(form.errors)
      work_place_form.is_valid()
      context = {'form': form, 'work_place_form': work_place_form }
      response_data['success'] = False
      response_data['html'] = render_to_string('bcse_app/SignUpModal.html', context, request)

    return http.HttpResponse(json.dumps(response_data), content_type="application/json")

  return http.HttpResponseNotAllowed(['GET', 'POST'])

@login_required
def signinRedirect(request):
  messages.success(request, "You have signed in")
  return shortcuts.redirect('bcse:home')

def home(request):
  context = {}
  return render(request, 'bcse_app/Home.html', context)

def reservations(request):
  reservations = models.Reservation.objects.all()
  context = {'reservations': reservations}
  return render(request, 'bcse_app/Reservations.html', context)

def reservationEdit(request, id=''):

  if '' != id:
    reservation = models.Reservation.objects.get(id=id)
  else:
    reservation = models.Reservation()

  if request.method == 'GET':
    form = forms.ReservationForm(instance=reservation)
    context = {'form': form}

    return render(request, 'bcse_app/ReservationEdit.html', context)

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
      equipment_availability_matrix = checkAvailability(id, equipment_types, start_date, end_date, delivery_date, return_date)
      is_available = all([equipment_type['is_available'] for equipment_type in equipment_availability_matrix.values()])
      availability_calendar = []
      index_date = start_date
      while index_date <= end_date:
        cal = Calendar(index_date.year, index_date.month)
        cal.setfirstweekday(6)
        availability_calendar.append(cal.formatmonth(withyear=True, availability_matrix=equipment_availability_matrix, delivery_date=delivery_date, return_date=return_date))
        index_date += relativedelta(months=1)

      if only_checking_availability:
        messages.info(request, "Selected equipment is %s for the selected dates" % ('available' if is_available else 'unavailable'))
        context = {'form': form, 'is_available': is_available, 'equipment_availability_matrix': equipment_availability_matrix,
                   'delivery_date': delivery_date, 'return_date': return_date, 'availability_calendar': availability_calendar,
                   'start_date': start_date, 'end_date': end_date}
        return render(request, 'bcse_app/ReservationEdit.html', context)
      else:
        if is_available:
          savedReservation = form.save()
          savedReservation.equipment.clear()

          for equipment_type, availability in equipment_availability_matrix.items():
            savedReservation.equipment.add(availability['most_available_equip'])

          savedReservation.save()

          messages.success(request, "Reservation made")
          return shortcuts.redirect('bcse:reservationEdit', id=savedReservation.id)
        else:
          messages.info(request, "Selected equipment is %s for the selected dates" % ('available' if is_available else 'unavailable'))
          context = {'form': form, 'is_available': is_available, 'equipment_availability_matrix': equipment_availability_matrix,
                   'delivery_date': delivery_date, 'return_date': return_date, 'availability_calendar': availability_calendar,
                   'start_date': start_date, 'end_date': end_date}
          return render(request, 'bcse_app/ReservationEdit.html', context)

  return http.HttpResponseNotAllowed(['GET', 'POST'])

def reservationView(request, id=''):
  try:
    if '' != id:
      reservation = models.Reservation.objects.get(id=id)
      context = {'reservation': reservation}
      return render(request, 'bcse_app/ReservationView.html', context)
    else:
      raise models.Reservation.DoesNotExist

  except models.Reservation.DoesNotExist:
    messages.error(request, 'Reservation not found')
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))



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


def workshopCategory(request, id=''):
  workshop_category = models.WorkshopCategory.objects.get(id=id)
  response_data = {'success': True, 'id': workshop_category.id, 'name': workshop_category.name, 'need_teacher_info': workshop_category.need_teacher_info}
  return http.HttpResponse(json.dumps(response_data), content_type = 'application/json')


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

    if request.method == 'GET':
      form = forms.WorkshopForm(instance=workshop)
      workshop_categories = models.WorkshopCategory.objects.all()

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
        workshop_categories = models.WorkshopCategory.objects.all()
        context = {'form': form, 'workshop_registration_setting': workshop_registration_setting, 'workshop_categories': workshop_categories}

        return render(request, 'bcse_app/WorkshopEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.Workshop.DoesNotExist:
    messages.success(request, "Workshop not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

def workshopView(request, id=''):
  try:
    if '' != id:
      workshop = models.Workshop.objects.get(id=id)
      if workshop.status != 'A':
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


def workshopRegistration(request, workshop_id):

  registration = {}
  form = workshop_registration = message = None

  workshop = models.Workshop.objects.get(id=workshop_id)

  if workshop.enable_registration and workshop.registration_setting and workshop.registration_setting.registration_type:
    if workshop.registration_setting.registration_type == 'R':
      default_registration_status = 'R'
    else:
      default_registration_status = 'A'

    if request.user.is_anonymous:
      if default_registration_status == 'R':
        message = 'Please login to register for this workshop'
      else:
        message = 'Please login to apply to this workshop'
    else:
      if request.user.userProfile.user_role in ['A', 'S']:
        workshop_registration = models.Registration(workshop_registration_setting=workshop.registration_setting, status=default_registration_status)
      else:
        try:
          workshop_registration = models.Registration.objects.get(workshop_registration_setting=workshop.registration_setting, user=request.user.userProfile)
          message = workshopRegistrationMessage(workshop_registration)
        except models.Registration.DoesNotExist:
          workshop_registration = models.Registration(workshop_registration_setting=workshop.registration_setting, user=request.user.userProfile, status=default_registration_status)


  if request.method == 'GET':
    if workshop_registration:
      form = forms.WorkshopRegistrationForm(instance=workshop_registration, prefix='workshop-%s'%workshop.id)
    registration['form'] = form
    registration['instance'] = workshop_registration
    registration['message'] = message

    return registration

  elif request.method == 'POST':
    data = request.POST.copy()
    form = forms.WorkshopRegistrationForm(data, instance=workshop_registration, prefix='workshop-%s'%workshop.id)

    if form.is_valid():
      saved_registration = form.save()
      if request.user.userProfile.user_role in ['A', 'S']:
        messages.success(request, "Workshop registration for user %s saved" % saved_registration.user)
        form = forms.WorkshopRegistrationForm(instance=workshop_registration)
      else:
        message = workshopRegistrationMessage(saved_registration)
        print(message)

      registration['form'] = form
      registration['instance'] = workshop_registration
      registration['message'] = message
      success = True

    else:
      print(form.errors)
      messages.success(request, "There were some errors")

      registration['form'] = form
      registration['instance'] = workshop_registration
      registration['message'] = message
      success = False

    if request.is_ajax():
      response_data = {'success': success, 'message': message}
      return http.HttpResponse(json.dumps(response_data), content_type = 'application/json')
    else:
      print('request non ajax')
      return registration

def workshopRegistrationEdit(request, workshop_id='', id=''):

  try:
    if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
      raise CustomException('You do not have the permission to edit this registration')

    if '' != id:
      registration = models.Registration.objects.get(id=id)
      workshop = models.Workshop.objects.get(id=workshop_id)

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

      print('before returning')
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

def workshopRegistrationMessage(workshop_registration):

  if workshop_registration.workshop_registration_setting.registration_type == 'R':
    registration_type = 'registration'
  else:
    registration_type = 'application'

  message = ''

  if workshop_registration.status == 'R':
    message = 'You are registered for this workshop'
  elif workshop_registration.status == 'A':
    message = 'You have applied for this workshop'
  elif workshop_registration.status == 'P':
    message = 'You %s is pending for this workshop' % registration_type
  elif workshop_registration.status == 'N':
    message = 'Your %s is cancelled for this workshop' % registration_type
  elif workshop_registration.status == 'W':
    message = 'Your %s is waitlisted for this workshop' % registration_type

  return message

def workshops(request, flag='list'):

  if request.user.is_anonymous or request.user.userProfile.user_role not in ['A', 'S']:
    workshops = models.Workshop.objects.all().filter(status='A')
  else:
    workshops = models.Workshop.objects.all()

  workshop_list = []
  for workshop in workshops:
    registration = None
    if workshop.enable_registration and workshop.registration_setting and workshop.registration_setting.registration_type:
      registration = workshopRegistration(request, workshop.id)
    workshop_list.append({'workshop': workshop, 'registration': registration})


  context = {'workshop_list': workshop_list}

  if flag == 'list':
    return render(request, 'bcse_app/WorkshopsListView.html', context)
  else:
    return render(request, 'bcse_app/WorkshopsTableView.html', context)


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

def workshopRegistrants(request, id=''):
  try:

    if request.user.userProfile.user_role != 'A':
      raise CustomException('You do not have the permission to view this user profile')

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


def userProfileView(request, id=''):
  try:

    if '' != id:
      userProfile = models.UserProfile.objects.get(id=id)
    else:
      raise models.UserProfile.DoesNotExist

    if request.user.userProfile.user_role != 'A' and request.user.id != userProfile.user.id:
      raise CustomException('You do not have the permission to view this user profile')

    if request.method == 'GET':
      context = {'userProfile': userProfile}

      return render(request, 'bcse_app/UserProfileView.html', context)

    return http.HttpResponseNotAllowed(['GET'])

  except models.UserProfile.DoesNotExist:
    messages.error(request, "User profile not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))

####################################
# USER PROFILE
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
      #convert username and email to lowercase before save
      data.__setitem__('user-username', data.__getitem__('user-username').lower())
      data.__setitem__('user-email', data.__getitem__('user-email').lower())
      data.__setitem__('user-password', userProfile.user.password)
      data.__setitem__('user-last_login', userProfile.user.last_login)
      data.__setitem__('user-date_joined', userProfile.user.date_joined)

      userForm = forms.UserForm(data, instance=userProfile.user, user=request.user, prefix='user')
      userProfileForm = forms.UserProfileForm(data, files=request.FILES,  instance=userProfile, user=request.user, prefix="user_profile")

      if userForm.is_valid(userProfile.user.id) and userProfileForm.is_valid():
        userForm.save()
        savedUserProfile = userProfileForm.save()
        messages.success(request, "User profile saved successfully")
        return shortcuts.redirect('bcse:userProfileEdit', id=savedUserProfile.id)

      else:
        print(userForm.errors)
        print(userProfileForm.errors)
        context = {'userProfileForm': userProfileForm, 'userForm': userForm}
        return render(request, 'bcse_app/UserProfileEdit.html', context)

    return http.HttpResponseNotAllowed(['GET', 'POST'])

  except models.UserProfile.DoesNotExist:
    messages.error(request, "User profile not found")
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))
  except CustomException as ce:
    messages.error(request, ce)
    return http.HttpResponseRedirect(request.META.get('HTTP_REFERER'))


