from django import forms
from django.forms import ModelForm
from django.contrib.auth.forms import PasswordResetForm
from bcse_app import models, widgets, utils
from django.forms.widgets import TextInput
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db.models.functions import Lower
from localflavor.us.models import USStateField
from django.contrib.admin.widgets import FilteredSelectMultiple
from dal import autocomplete
import datetime
from django.template.loader import render_to_string, get_template
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMessage, EmailMultiAlternatives
from django.conf import settings
from django.contrib.sites.models import Site

####################################
# Login Form
####################################
class SignInForm (forms.Form):
  email = forms.CharField(required=True, max_length=75, label='Email',
                              error_messages={'required': 'Email is required'}, help_text='You may use your primary or secondary email to login')
  password = forms.CharField(required=True, widget=forms.PasswordInput(render_value=False), label='Password',
                              error_messages={'required': 'Password is required'})

  def __init__(self, *args, **kwargs):
    super(SignInForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      #field.widget.attrs['placeholder'] = field.help_text


  def clean_email(self):
    return self.cleaned_data['email'].strip()

  def clean(self):
    cleaned_data = super(SignInForm, self).clean()
    email = cleaned_data.get('email')
    password = cleaned_data.get('password')

    if email is None:
      self.fields['email'].widget.attrs['class'] += ' error'
    if password is None:
      self.fields['password'].widget.attrs['class'] += ' error'

    if email is not None:
      primary_email = None
      if User.objects.filter(email=email.lower()).count() == 1:
        primary_email = email.lower()
      elif models.UserProfile.objects.filter(secondary_email=email.lower()).count() == 1:
        primary_email = models.UserProfile.objects.get(secondary_email=email.lower()).user.email
      else:
        self.add_error('email', 'Email is incorrect.')
        self.fields['email'].widget.attrs['class'] += ' error'

      if primary_email and password is not None:
        user = authenticate(username=primary_email.lower(), password=password)
        if user is None:
          self.add_error('password', 'Password is incorrect.')
          self.fields['password'].widget.attrs['class'] += ' error'
        else:
          self.user = user

####################################
# Registration Form
####################################
class SignUpForm (forms.Form):
  email = forms.EmailField(required=True, max_length=75, label='Email')
  confirm_email = forms.EmailField(required=True, max_length=75, label='Confirm Email')
  first_name = forms.CharField(required=True, max_length=30, label='First Name')
  last_name = forms.CharField(required=True, max_length=30, label='Last Name')
  name_pronounciation = forms.CharField(required=False, max_length=30, label='Name Pronounciation')
  secondary_email = forms.EmailField(required=False, max_length=75, label='Secondary Email', help_text="Secondary email can be used to Sign In and reset password.  Any email sent to your user account via the BCSE website will be sent to both primary and secondary email addresses.")
  password1 = forms.CharField(required=True, widget=forms.PasswordInput(render_value=False), label='Password')
  password2 = forms.CharField(required=True, widget=forms.PasswordInput(render_value=False), label='Confirm Password')
  user_role = forms.ChoiceField(required=True, choices=(('', '---------'),)+models.USER_ROLE_CHOICES, label='I am a')
  work_place = forms.ModelChoiceField(required=False, label=u"Workplace",
                                  queryset=models.WorkPlace.objects.all(),
                                  widget=autocomplete.ModelSelect2(url='workplace-autocomplete',
                                                                  attrs={'data-placeholder': 'Start typing the name if your workplace ...', 'dropdownParent': '#signup_workplace_select'}),
                                  )
  phone_number = forms.CharField(required=False, max_length=20, label='Phone Number')
  iein = forms.CharField(required=False, max_length=20, label='IEIN')
  grades_taught = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.GRADES_CHOICES, label='Grades Taught')
  twitter_handle = forms.CharField(required=False, max_length=20, label='Twitter ID')
  instagram_handle = forms.CharField(required=False, max_length=20, label='Instagram ID')
  new_work_place_flag = forms.BooleanField(required=False, label='My Workplace Is Not Listed')
  subscribe = forms.BooleanField(required=False, label='Subscribe To Our Mailing List')
  image = forms.ImageField(required=False)


  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')

    super(SignUpForm, self).__init__(*args, **kwargs)

    if user.is_authenticated and user.userProfile.user_role in ['A', 'S']:
      self.fields['user_role'].label = 'User Role'
      self.fields['new_work_place_flag'].label = 'Workplace Not Listed'
    else:
      self.fields['user_role'].choices = (('', '---------'),)+models.USER_ROLE_CHOICES[1:3]

    for field_name, field in list(self.fields.items()):
      if field_name not in ['new_work_place_flag', 'subscribe']:
        field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'
        if field_name == 'subscribe':
          field.initial = True

      field.widget.attrs['aria-describedby'] = field.label
      #field.widget.attrs['placeholder'] = field.help_text

  def clean_email(self):
    return self.cleaned_data['email'].strip()

  def clean_confirm_email(self):
    return self.cleaned_data['confirm_email'].strip()

  def clean_secondary_email(self):
    return self.cleaned_data['secondary_email'].strip()

  def clean(self):
    cleaned_data = super(SignUpForm, self).clean()
    first_name = cleaned_data.get('first_name')
    last_name = cleaned_data.get('last_name')
    password1 = cleaned_data.get('password1')
    password2 = cleaned_data.get('password2')
    email = cleaned_data.get('email')
    confirm_email = cleaned_data.get('confirm_email')
    user_role = cleaned_data.get('user_role')
    work_place = cleaned_data.get('work_place')
    new_work_place_flag = cleaned_data.get('new_work_place_flag')
    print(new_work_place_flag, 'new workplace flag')
    secondary_email = cleaned_data.get('secondary_email')

    if email is None:
      self.fields['email'].widget.attrs['class'] += ' error'
    elif User.objects.filter(email=email.lower()).count() > 0 or models.UserProfile.objects.filter(secondary_email=email.lower()).count() > 0:
      self.add_error('email', 'This email is already taken. Please choose another.')
      self.fields['email'].widget.attrs['class'] += ' error'
    elif 'confirm_email' in self.fields and email != confirm_email:
      self.add_error('confirm_email', 'Emails do not match.')
      self.fields['email'].widget.attrs['class'] += ' error'
      self.fields['confirm_email'].widget.attrs['class'] += ' error'

    if password1 is None:
      self.fields['password1'].widget.attrs['class'] += ' error'
    if password2 is None:
      self.fields['password2'].widget.attrs['class'] += ' error'
    if password1 != password2:
      self.add_error('password1', 'Passwords do not match.')
      self.fields['password1'].widget.attrs['class'] += ' error'
      self.fields['password2'].widget.attrs['class'] += ' error'

    if first_name is None:
      self.fields['first_name'].widget.attrs['class'] += ' error'
    if last_name is None:
      self.fields['last_name'].widget.attrs['class'] += ' error'

    #check fields for Teacher, Student and School Administrator
    if work_place is None and not new_work_place_flag:
      self.fields['work_place'].widget.attrs['class'] += ' error'
      self.add_error('work_place', 'Workplace is required.')

    if secondary_email is not None and isinstance(secondary_email, str) and secondary_email.strip() != "":
      if email == secondary_email:
        self.add_error('secondary_email', 'Please choose a secondary email different from the primary email.')
        self.fields['secondary_email'].widget.attrs['class'] += ' error'
      if User.objects.filter(email=secondary_email.lower()).count() > 0 or models.UserProfile.objects.filter(secondary_email=secondary_email.lower()).count() > 0:
        self.add_error('secondary_email', 'This email is already taken. Please choose another.')
        self.fields['secondary_email'].widget.attrs['class'] += ' error'


#######################################################
# Override the password reset form to allow secondary email
#######################################################
class SecondaryEmailPasswordResetForm(PasswordResetForm):

  recaptchaToken = forms.CharField(widget=forms.HiddenInput)

  def clean(self):
    cleaned_data = super().clean()
    recaptcha_token = cleaned_data.get('recaptchaToken')

    if not recaptcha_token:
      raise forms.ValidationError("reCAPTCHA token is required")

    recaptcha_passed = utils.validateReCaptcha(recaptcha_token, 'password_reset')

    if recaptcha_passed:
      return cleaned_data

    raise forms.ValidationError('reCAPTCHA validation failed')


  def get_users(self, email):
    """Return users matching primary or secondary email."""
    email = email.lower()

    # 1) match primary email
    users = list(
      User.objects.filter(email__iexact=email, is_active=True)
    )

    # 2) match secondary email
    profile_users = User.objects.filter(
      userProfile__secondary_email__iexact=email,
      is_active=True
    )

    users.extend(list(profile_users))
    return users

  def send_mail(self, subject_template_name, email_template_name,
                context, from_email, to_email, html_email_template_name=None):

    """Override to always send to the user-entered email."""

    current_site = Site.objects.get_current()
    domain = current_site.domain

    subject = render_to_string(subject_template_name, context).strip()

    if domain != 'bcse.northwestern.edu':
      subject = '***** TEST **** '+ subject + ' ***** TEST **** '

    #body = render_to_string(email_template_name, context)
    body = get_template(email_template_name).render(context)

    #send_mail(subject, body, from_email, [to_email])
    email = EmailMultiAlternatives(subject, body, settings.DEFAULT_FROM_EMAIL, [to_email])
    # attach HTML version
    if html_email_template_name:
      html_body = get_template(html_email_template_name).render(context)
      email.attach_alternative(html_body, "text/html")

    sent = email.send(fail_silently=True)

  def save(self, domain_override=None,
           subject_template_name='password_reset/password_reset_subject.txt',
           email_template_name='password_reset/password_reset_email.html',
           use_https=False, token_generator=default_token_generator,
           from_email=None, request=None, html_email_template_name='password_reset/password_reset_email.html',
           extra_email_context=None):

    email = self.cleaned_data["email"]  # the address user typed
    current_site = Site.objects.get_current()

    for user in self.get_users(email):
      context = {
        'email': email,                # send TO this address
        'domain': current_site.domain,
        'site_name': current_site.name,
        'uid': urlsafe_base64_encode(force_bytes(user.pk)),
        'user': user,
        'token': token_generator.make_token(user),
        'protocol': 'https' if use_https else 'http',
      }
      self.send_mail(
        subject_template_name, email_template_name,
        context, from_email, email, html_email_template_name
      )


####################################
# User Form
####################################
class UserForm(ModelForm):
  password1 = forms.CharField(required=False, label='Password', help_text="Leave this field blank to retain old password")
  password2 = forms.CharField(required=False, label='Confirm Password')

  class Meta:
    model = models.User
    fields = ["first_name", "last_name", "email", "password1", "password2", "is_active"]

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    super(UserForm, self).__init__(*args, **kwargs)

    self.fields['email'].label = 'Email'

    if user.is_authenticated:
      if user.userProfile.user_role not in ['A', 'S']:
        self.fields.pop('is_active')

    for field_name, field in list(self.fields.items()):
      if field_name not in ['is_active']:
        if field_name in ['password1', 'password2']:
          field.widget.attrs['class'] = 'form-control password'
        else:
          field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

  def clean_email(self):
    return self.cleaned_data['email'].strip()

  def save(self, commit=True):
    user = super(UserForm, self).save(commit=True)
    user.username = self.cleaned_data['email']

    if self.cleaned_data['password1'] is not None and self.cleaned_data['password1'] != "":
      user.set_password(self.cleaned_data['password1'])

    user.save()
    return user

  def is_valid(self, user_id):
    valid = super(UserForm, self).is_valid()
    if not valid:
      return valid

    cleaned_data = super(UserForm, self).clean()
    first_name = cleaned_data.get('first_name')
    last_name = cleaned_data.get('last_name')
    password1 = cleaned_data.get('password1')
    password2 = cleaned_data.get('password2')
    email = cleaned_data.get('email')

    if password1 != password2:
      self.add_error('password1', 'Passwords do not match.')
      valid = False

    if first_name is None or first_name == '':
      self.add_error('first_name', 'First name is required')
      valid = False
    if last_name is None or last_name == '':
      self.add_error('last_name', 'Last name is required')
      valid = False
    if email is None or email == '':
      self.add_error('email', 'Email is required')
      valid = False
    elif User.objects.filter(email=email.lower()).exclude(id=user_id).count() > 0 or models.UserProfile.objects.filter(secondary_email=email.lower()).exclude(user__id=user_id).count() > 0:
      self.add_error('email', 'This email is already taken. Please choose another.')
      valid = False

    return valid


####################################
# UserProfile Form
####################################
class UserProfileForm (ModelForm):

  new_work_place_flag = forms.BooleanField(required=False, label='My Workplace Is Not Listed')

  class Meta:
    model = models.UserProfile
    fields = ['secondary_email', 'work_place', 'user_role', 'image', 'phone_number', 'iein', 'grades_taught', 'twitter_handle', 'instagram_handle', 'subscribe', 'photo_release_complete', 'dietary_preference', 'admin_notes', 'name_pronounciation']
    widgets = {
      'image': widgets.ClearableFileInput,
      'work_place': autocomplete.ModelSelect2(url='workplace-autocomplete',
                                              attrs={'data-placeholder': 'Start typing the name if your workplace ...', 'dropdownparent': '#profile_workplace_select'}),
    }

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    update_required = kwargs.pop('update_required')
    self.user = user
    super(UserProfileForm, self).__init__(*args, **kwargs)
    self.fields['twitter_handle'].label = 'Twitter ID'
    self.fields['instagram_handle'].label = 'Instagram ID'
    self.fields['subscribe'].label = 'Subscribe To Our Mailing List'
    self.fields['work_place'].label = 'Workplace'

    if user.is_authenticated:
      if user.userProfile.user_role not in ['A', 'S']:
        self.fields['user_role'].choices = (('', '---------'),)+models.USER_ROLE_CHOICES[1:3]
        self.fields.pop('photo_release_complete')
        self.fields.pop('admin_notes')

      self.fields['work_place'].required = False

    for field_name, field in list(self.fields.items()):
      if field_name not in ['new_work_place_flag', 'subscribe', 'photo_release_complete']:
        field.widget.attrs['class'] = 'form-control'
        if field_name in ['iein', 'work_place'] and update_required:
          field.widget.attrs['class'] += ' border-warning'

      else:
        field.widget.attrs['class'] = 'form-check-input'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

  def clean(self):
    user = self.user
    cleaned_data = super(UserProfileForm, self).clean()
    work_place = cleaned_data.get('work_place')
    new_work_place_flag = cleaned_data.get('new_work_place_flag')
    secondary_email = cleaned_data.get('secondary_email')

    #check fields for Teacher, Student and School Administrator
    if user.is_authenticated:
      if user.userProfile.user_role not in ['A', 'S']:
        if work_place is None and not new_work_place_flag:
          self.fields['work_place'].widget.attrs['class'] += ' error'
          self.add_error('work_place', 'Workplace is required.')


    if secondary_email is not None and isinstance(secondary_email, str) and secondary_email.strip() != "":
      #print(secondary_email)
      if self.instance.id:
        if User.objects.filter(email=secondary_email.lower()).exclude(userProfile__id=self.instance.id).count() > 0 or models.UserProfile.objects.filter(secondary_email=secondary_email.lower()).exclude(id=self.instance.id).count() > 0:
          self.add_error('secondary_email', 'This email is already taken. Please choose another.')
          self.fields['secondary_email'].widget.attrs['class'] += ' error'
      elif User.objects.filter(email=secondary_email.lower()).count() > 0 or models.UserProfile.objects.filter(secondary_email=secondary_email.lower()).count() > 0:
        self.add_error('secondary_email', 'This email is already taken. Please choose another.')
        self.fields['secondary_email'].widget.attrs['class'] += ' error'



####################################
# Subscription Form
####################################
class SubscriptionForm (forms.Form):
  email = forms.EmailField(required=True, max_length=75, label='Email')
  first_name = forms.CharField(required=True, max_length=30, label='First Name')
  last_name = forms.CharField(required=True, max_length=30, label='Last Name')
  phone_number = forms.CharField(required=False, max_length=20, label='Phone Number')

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    super(SubscriptionForm, self).__init__(*args, **kwargs)
    if user.is_authenticated:
      self.fields.pop('captcha')

    for field_name, field in list(self.fields.items()):
      if field_name != 'captcha':
        field.widget.attrs['class'] = 'form-control'
        field.widget.attrs['aria-describedby'] = field.label
        field.widget.attrs['placeholder'] = field.help_text

    if user.is_authenticated:
      self.fields['email'].initial = user.email
      self.fields['first_name'].initial = user.first_name
      self.fields['last_name'].initial = user.last_name
      if user.userProfile.phone_number:
        self.fields['phone_number'].initial = user.userProfile.phone_number

####################################
# User Upload Form
####################################
class UsersUploadForm(forms.Form):
  file = forms.FileField(required=True, help_text="Upload the user template")

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    super(UsersUploadForm, self).__init__(*args, **kwargs)
    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Workplace Upload Form
####################################
class WorkPlacesUploadForm(forms.Form):
  file = forms.FileField(required=True, help_text="Upload the workplace template")

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    super(WorkPlacesUploadForm, self).__init__(*args, **kwargs)
    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Workshop Upload Form
####################################
class WorkshopsUploadForm(forms.Form):
  file = forms.FileField(required=True, help_text="Upload a JSON file")

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    super(WorkshopsUploadForm, self).__init__(*args, **kwargs)
    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Activity Form
####################################
class ActivityForm(ModelForm):

  class Meta:
    model = models.Activity
    exclude = ('created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
      'notes': forms.Textarea(attrs={'rows':2}),
    }

  def __init__(self, *args, **kwargs):
    super(ActivityForm, self).__init__(*args, **kwargs)
    self.fields['materials_equipment'].label = 'Materials/Equipment'
    self.fields['manuals_resources'].label = 'Instruction Manuals/Resources'
    self.fields['notes'].label = 'Notes'
    self.fields['color'].queryset = models.ReservationColor.objects.all().filter(target__in=['K', 'B'])
    self.fields['color'].label = 'Inventory Status'

    for field_name, field in list(self.fields.items()):
      if field_name == 'tags':
        field.widget.attrs['class'] = 'form-control select2'
      else:
        field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


####################################
# Inventory Form
####################################
class InventoryForm(forms.Form):

  inventory_type = forms.ChoiceField(required=False, choices=(('', '---------'),
                                                       ('kit', 'Activity Kit'),
                                                       ('consumable', 'Consumable'),
                                                       ),)

  def __init__(self, *args, **kwargs):
    super(InventoryForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


####################################
# Activity Inventory Form
####################################
class ActivityInventoryForm(ModelForm):

  class Meta:
    model = models.ActivityInventory
    exclude = ('created_date', 'modified_date')
    widgets = {
      'expiration_date': forms.DateInput(format='%B %d, %Y'),
    }

  def __init__(self, *args, **kwargs):
    super(ActivityInventoryForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name == 'activity':
        field.widget.attrs['class'] = 'form-control select2'
      elif field_name == 'expiration_date':
        field.widget.attrs['class'] = 'form-control datepicker'
        field.widget.attrs['readonly'] = True
      else:
        field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

##########################################################
# Activity Update Form
# to update select few fields in a activity
##########################################################
class ActivityUpdateForm(ModelForm):

  class Meta:
    model = models.Activity
    fields = ['kit_unit_cost', 'notes', 'color']
    widgets = {
      'notes': forms.Textarea(attrs={'rows':1}),
    }

  def __init__(self, *args, **kwargs):
    super(ActivityUpdateForm, self).__init__(*args, **kwargs)
    self.fields['notes'].label = 'Notes'
    self.fields['color'].queryset = models.ReservationColor.objects.all().filter(target__in=['K', 'B'])
    self.fields['color'].label = 'Inventory Status'


    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Consumable Form
####################################
class ConsumableForm(ModelForm):

  class Meta:
    model = models.Consumable
    exclude = ('created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
      'notes': forms.Textarea(attrs={'rows':2}),
    }

  def __init__(self, *args, **kwargs):
    super(ConsumableForm, self).__init__(*args, **kwargs)
    self.fields['notes'].label = 'Notes'
    self.fields['color'].queryset = models.ReservationColor.objects.all().filter(target__in=['K', 'B'])
    self.fields['color'].label = 'Inventory Status'

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


####################################
# Consumable Inventory Form
####################################
class ConsumableInventoryForm(ModelForm):

  class Meta:
    model = models.ConsumableInventory
    exclude = ('created_date', 'modified_date')
    widgets = {
      'expiration_date': forms.DateInput(format='%B %d, %Y'),
    }

  def __init__(self, *args, **kwargs):
    super(ConsumableInventoryForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name == 'consumable':
        field.widget.attrs['class'] = 'form-control select2'
      elif field_name == 'expiration_date':
        field.widget.attrs['class'] = 'form-control datepicker'
        field.widget.attrs['readonly'] = True
      else:
        field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

##########################################################
# Consumable Update Form
# to update select few fields in a consumable
##########################################################
class ConsumableUpdateForm(ModelForm):

  class Meta:
    model = models.Consumable
    fields = ['unit_cost', 'notes', 'color']
    widgets = {
      'notes': forms.Textarea(attrs={'rows':1}),
    }

  def __init__(self, *args, **kwargs):
    super(ConsumableUpdateForm, self).__init__(*args, **kwargs)
    self.fields['notes'].label = 'Notes'
    self.fields['color'].queryset = models.ReservationColor.objects.all().filter(target__in=['K', 'B'])
    self.fields['color'].label = 'Inventory Status'


    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Tag Form
####################################
class TagForm(ModelForm):

  class Meta:
    model = models.Tag
    exclude = ('created_date', 'modified_date')

  def __init__(self, *args, **kwargs):
    super(TagForm, self).__init__(*args, **kwargs)
    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


####################################
# Sub Tag Form
####################################
class SubTagForm(ModelForm):

  class Meta:
    model = models.SubTag
    exclude = ('created_date', 'modified_date')

  def __init__(self, *args, **kwargs):
    super(SubTagForm, self).__init__(*args, **kwargs)
    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text



####################################
# Baxter Box Search Form
####################################
class BaxterBoxSearchForm(forms.Form):

  def __init__(self, *args, **kwargs):
    initials = kwargs.pop('initials')
    super(BaxterBoxSearchForm, self).__init__(*args, **kwargs)

    sub_tag_ids = models.Activity.objects.all().values_list('tags', flat=True)
    tag_ids = models.SubTag.objects.all().filter(id__in=list(sub_tag_ids)).values_list('tag', flat=True)

    for tag_id in list(set(tag_ids)):
      tag = models.Tag.objects.get(id=tag_id)
      if tag.status == 'A':
        sub_tags = models.SubTag.objects.all().filter(tag=tag, status='A', id__in=list(sub_tag_ids))
        self.fields['tag_'+str(tag.id)] = forms.MultipleChoiceField(
                                                required=False,
                                                widget=forms.SelectMultiple(),
                                                choices=[(sub.id, sub.name) for sub in sub_tags],
                                            )
        self.fields['tag_'+str(tag.id)].label = tag.name



    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control select2'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]


####################################
# Baxter Box Inventory Search Form
####################################
class BaxterBoxInventorySearchForm(forms.Form):
  activities = forms.ModelMultipleChoiceField(required=False, label=u'Activities', queryset=models.Activity.objects.all().filter(status='A').order_by('name'), widget=forms.SelectMultiple(attrs={'size':6}))
  consumables = forms.ModelMultipleChoiceField(required=False, label=u'Consumables', queryset=models.Consumable.objects.all().filter(status='A').order_by('name'), widget=forms.SelectMultiple(attrs={'size':6}))
  color = forms.ModelMultipleChoiceField(required=False, label=u'Inventory Status', queryset=models.ReservationColor.objects.all().filter(target__in=['K']))
  expiration_date_after = forms.DateField(required=False, label=u'Expiration Date on/after')
  storage_locations = forms.MultipleChoiceField(required=False, choices=models.INVENTORY_STORAGE_LOCATION)
  inventory_type = forms.ChoiceField(required=False, choices=(('', '---------'),
                                                       ('kit', 'Activity Kit'),
                                                       ('consumable', 'Consumable'),
                                                       ),
                                              initial='name')
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),
                                                       ('name', 'Name'),
                                                       ('expiration_date_asc', 'Expiration Date (Asc)'),
                                                       ('expiration_date_desc', 'Expiration Date (Desc)'),
                                                       ('count_asc', 'Count (Asc)'),
                                                       ('count_desc', 'Count (Desc)'),
                                                       ('total_count_asc', 'Total Count (Asc)'),
                                                       ('total_count_desc', 'Total Count (Desc)')
                                                       ),
                                              initial='name')
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)


  def __init__(self, *args, **kwargs):
    initials = kwargs.pop('initials')
    super(BaxterBoxInventorySearchForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):

      if field_name in ['activities', 'consumables', 'color', 'storage_locations']:
        field.widget.attrs['class'] = 'form-control select2'
      elif field_name == 'expiration_date_after':
        field.widget.attrs['class'] = 'form-control datepicker'
        field.widget.attrs['readonly'] = True
      else:
        field.widget.attrs['class'] = 'form-control'

      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]

####################################
# Equipment Category Form
####################################
class EquipmentTypeForm(ModelForm):

  class Meta:
    model = models.EquipmentType
    exclude = ('created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
    }

  def __init__(self, *args, **kwargs):
    super(EquipmentTypeForm, self).__init__(*args, **kwargs)
    sub_tags = models.EquipmentType.objects.all().values_list('tags', flat=True)
    tags = models.Tag.objects.all().filter(status='A', sub_tags__id__in=sub_tags)
    for tag in tags:
      self.fields['tag_'+str(tag.id)] = forms.MultipleChoiceField(
                                                          required=False,
                                                          widget=forms.SelectMultiple,
                                                          choices=[(sub.id, sub.name) for sub in models.SubTag.objects.all().filter(tag=tag, status='A')],
                                                      )
      self.fields['tag_'+str(tag.id)].label = tag.name

    self.fields['tags'].label = 'Tags'
    for field_name, field in list(self.fields.items()):
      if field_name == 'featured':
        field.widget.attrs['class'] = 'form-check-input'
      else:
        field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Equipment Form
####################################
class EquipmentForm(ModelForm):

  class Meta:
    model = models.Equipment
    exclude = ('created_date', 'modified_date')

  def __init__(self, *args, **kwargs):
    super(EquipmentForm, self).__init__(*args, **kwargs)
    self.fields['equipment_type'].label = 'Equipment Category'

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Equipment Availability Search Form
####################################
class EquipmentAvailabilityForm (forms.Form):

  equipment_types = forms.ModelMultipleChoiceField(required=False, label=u'Equipment Categories', queryset=models.EquipmentType.objects.all().filter(status='A').order_by('name'), widget=forms.SelectMultiple(attrs={'size':6}), help_text='On Windows use Ctrl+Click to make multiple selection. On a Mac use Cmd+Click to make multiple selection')
  selected_month = forms.DateField(required=True, initial=datetime.date.today, label=u'Month/Year', widget=forms.widgets.DateInput(format="%B %Y"))

  def __init__(self, *args, **kwargs):
    super(EquipmentAvailabilityForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

      if field_name == 'selected_month':
        field.widget.attrs['class'] = 'form-control datepicker availability'
        field.widget.attrs['readonly'] = True


class ReservationForm(ModelForm):
  equipment_types = forms.ModelMultipleChoiceField(required=False,
                                  queryset=models.EquipmentType.objects.all().filter(status='A', equipment__status='A').distinct().order_by('order'), widget=forms.CheckboxSelectMultiple())

  confirm_workplace = forms.ChoiceField(required=True, choices=[('', '---------'), ('Y', 'Yes'),('N', 'No, update my workplace'),],)

  class Meta:
    model = models.Reservation
    exclude = ('email_sent', 'confirmation_email_dates', 'feedback_status', 'feedback_email_count', 'feedback_email_date', 'created_by', 'created_date', 'modified_date')
    widgets = {
      'user': autocomplete.ModelSelect2(url='user-autocomplete', attrs={'data-placeholder': 'Start typing the name of the user ...',}),
      'notes': forms.Textarea(attrs={'rows':3}),
      'admin_notes': forms.Textarea(attrs={'rows':3}),
      'delivery_date': forms.DateInput(format='%B %d, %Y'),
      'return_date': forms.DateInput(format='%B %d, %Y'),
      #'other_activity': forms.CheckboxInput(),
    }

  class Media:
    css = {'all': ('/static/path/to/widgets.css',),}
    js = ('/jsi18n',)

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    super(ReservationForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name not in ['other_activity', 'equipment_not_needed', 'additional_help_needed', 'activity_kit_not_needed', 'include_gloves', 'include_goggles']:
        if field_name in ['delivery_date', 'return_date']:
          if field_name == 'delivery_date':
            field.widget.attrs['class'] = 'form-control datepicker reservation_delivery_date reservation_date'
            field.widget.attrs['title'] = 'Click here to open a calender popup to select delivery date'
          else:
            field.widget.attrs['class'] = 'form-control datepicker reservation_return_date reservation_date'
            field.widget.attrs['title'] = 'Click here to open a calender popup to select return date'
          field.widget.attrs['readonly'] = True
        elif field_name in ['activity', 'equipment']:
          field.widget.attrs['class'] = 'form-control select2'
        else:
          field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'

      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


    if self.instance.id:
      equipment_type_qs = models.EquipmentType.objects.all().filter(status='A', equipment__status='A') | models.EquipmentType.objects.all().filter(equipment__in=self.instance.equipment.all())
      self.fields['equipment_types'].queryset = equipment_type_qs.distinct().order_by('order')
      self.fields['equipment_types'].initial = models.EquipmentType.objects.all().filter(equipment__in=self.instance.equipment.all())

      equipment_qs = models.Equipment.objects.all().filter(status='A') | models.Equipment.objects.all().filter(id__in=self.instance.equipment.all())
      self.fields['equipment'].queryset = equipment_qs.distinct().order_by('name')
      self.fields['equipment'].initial = models.Equipment.objects.all().filter(id__in=self.instance.equipment.all())

      self.fields['user'].widget.attrs['disabled'] = True
      if self.instance.activity:
        self.fields['activity'].queryset = models.Activity.objects.all().filter(status='A') | models.Activity.objects.all().filter(id=self.instance.activity.id)
      else:
        self.fields['activity'].queryset = models.Activity.objects.all().filter(status='A')

      self.fields.pop('confirm_workplace')

    else:
      self.fields['equipment_types'].queryset = models.EquipmentType.objects.all().filter(status='A', equipment__status='A').distinct().order_by('order')
      self.fields['activity'].queryset = models.Activity.objects.all().filter(status='A')
      if user.user_role in ['T', 'P']:
        if user.work_place:
          self.fields['confirm_workplace'].label = 'Is "<span>%s</span>" your current workplace?' % user.work_place
      else:
        self.fields['confirm_workplace'].label = 'Is "<span></span>" the user\'s current workplace?'


    self.fields['equipment_types'].label = 'Select one or more equipment.'
    #self.fields['equipment_types'].label_from_instance = lambda obj: "%s (%s)" % (obj.name, obj.short_name)
    self.fields['other_activity'].label = 'I am doing something not listed here.'
    self.fields['other_activity_name'].label = 'What activity are you planning to do?'
    self.fields['activity_kit_not_needed'].label = 'I already have all the kits I need.'
    self.fields['num_of_students'].label = 'Total # of students who will be doing this activity?'
    self.fields['num_of_classes'].label = 'Number of classes'
    self.fields['more_num_of_classes'].label = 'Number of classes more than 4'
    self.fields['include_gloves'].label = 'I would like to get gloves.'
    self.fields['include_goggles'].label = 'I would like to borrow goggles.'
    self.fields['include_goggles'].help_text = 'Goggles will need to be returned.'
    self.fields['equipment_not_needed'].label = 'I already have all the equipment I need.'
    self.fields['notes'].label = 'Please provide any additional information that would be useful, such as your preferred pick-up and return times, and any directions for parking and entering your school.'
    self.fields['assignee'].label = 'Delivery Assigned To'
    self.fields['pickup_assignee'].label = 'Pickup Assigned To'
    self.fields['additional_help_needed'].label = 'I need additional help.'
    self.fields['equipment'].help_text = 'Manually selecting individual equipment sets may result in overbooking. \
    Please manually resolve any overbooking that may occur from this modification. \
    Any overbooking from this reservation will be identified on the Reservation Confirmation page as well as the User Reservations page.'
    self.fields['status'].label = 'Reservation Status'
    self.fields['color'].label = 'Box Sub-Status'

    if user.user_role not in ['A', 'S']:
      self.fields.pop('assignee')
      self.fields.pop('pickup_assignee')
      self.fields.pop('more_num_of_classes')
      self.fields.pop('admin_notes')
      self.fields.pop('color')
      self.fields.pop('consumables')
      self.fields.pop('equipment')
    else:
      self.fields['assignee'].queryset = models.UserProfile.objects.all().filter(user_role__in=['A', 'S'], user__is_active=True).order_by('user__last_name', 'user__first_name')
      self.fields['pickup_assignee'].queryset = models.UserProfile.objects.all().filter(user_role__in=['A', 'S'], user__is_active=True).order_by('user__last_name', 'user__first_name')
      self.fields['activity'].queryset = models.Activity.objects.all()
      self.fields['color'].queryset = models.ReservationColor.objects.all().filter(target__in=['R', 'B'])
      self.fields['consumables'].queryset = models.Consumable.objects.all().filter(status='A')
      if self.instance.id:
        self.fields.pop('equipment_types')
      else:
        self.fields.pop('equipment')

  def is_valid(self):
    valid = super(ReservationForm, self).is_valid()

    cleaned_data = super(ReservationForm, self).clean()
    activity = cleaned_data.get('activity')
    other_activity = cleaned_data.get('other_activity')
    other_activity_name = cleaned_data.get('other_activity_name')
    num_of_classes = cleaned_data.get('num_of_classes')
    more_num_of_classes = cleaned_data.get('more_num_of_classes')
    num_of_students = cleaned_data.get('num_of_students')

    if activity is None and not other_activity:
      self.add_error('activity', 'Please select an activity from the dropdown or select "I am doing something not listed here"')
      valid = False
    elif other_activity and other_activity_name is None:
      self.add_error('other_activity_name', 'Please provide the name of your custom activity')
      valid = False

    if activity and num_of_classes is None:
      self.add_error('num_of_classes', 'Please provide the number of classes doing this activity')
      valid = False

    if num_of_classes is not None and int(num_of_classes) == 5:
      if more_num_of_classes is None or int(more_num_of_classes) < 5:
        self.add_error('more_num_of_classes', 'Please provide the number of classes more than 4')
        valid = False

    if num_of_students is not None and int(num_of_students) < 0:
      self.add_error('num_of_students', 'Please enter 0 or more for the total # of students')
      valid = False

    for x in self.errors:
      attrs = self.fields[x].widget.attrs
      attrs.update({'class': attrs.get('class', '') + ' is-invalid'})

    return valid

##########################################################
# Reservation Workplace Form
# to update reservation workplace association
##########################################################
class ReservationWorkPlaceForm(ModelForm):

  class Meta:
    model = models.ReservationWorkPlace
    fields = ['reservation', 'work_place']
    widgets = {
      'work_place': autocomplete.ModelSelect2(url='workplace-autocomplete',
                                              attrs={'data-placeholder': 'Start typing the name of the workplace ...'}),
    }

  def __init__(self, *args, **kwargs):
    super(ReservationWorkPlaceForm, self).__init__(*args, **kwargs)

    self.fields['work_place'].label = 'Workplace'
    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text


##########################################################
# Reservation Update Form
# For to update select few fields in a reservation
##########################################################
class ReservationUpdateForm(ModelForm):

  class Meta:
    model = models.Reservation
    fields = ['color', 'status', 'admin_notes', 'assignee', 'pickup_assignee']
    widgets = {
      'admin_notes': forms.Textarea(attrs={'rows':3}),
    }

  def __init__(self, *args, **kwargs):
    super(ReservationUpdateForm, self).__init__(*args, **kwargs)

    self.fields['color'].queryset = models.ReservationColor.objects.all().filter(target__in=['R', 'B'])
    self.fields['color'].label = 'Box Sub-Status'
    self.fields['status'].label = 'Reservation Status'
    self.fields['assignee'].label = 'Delivery Assigned To'
    self.fields['pickup_assignee'].label = 'Pickup Assigned To'
    self.fields['assignee'].queryset = models.UserProfile.objects.all().filter(user_role__in=['A', 'S'], user__is_active=True).order_by('user__last_name', 'user__first_name')
    self.fields['pickup_assignee'].queryset = models.UserProfile.objects.all().filter(user_role__in=['A', 'S'], user__is_active=True).order_by('user__last_name', 'user__first_name')

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text

####################################
# ReservationDeliveryAddress Form
####################################
class ReservationDeliveryAddressForm(ModelForm):

  class Meta:
    model = models.ReservationDeliveryAddress
    exclude = ('created_date', 'modified_date', 'latitude', 'longitude', 'time_from_base', 'distance_from_base')

  def __init__(self, *args, **kwargs):
    super(ReservationDeliveryAddressForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text


class ReservationMessageForm(ModelForm):
  class Meta:
    model = models.ReservationMessage
    fields = ['reservation', 'message', 'created_by']

  def __init__(self, *args, **kwargs):

    super(ReservationMessageForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


class BaxterBoxBlackoutDateForm(ModelForm):
  class Meta:
    model = models.BaxterBoxBlackoutDate
    fields = ['start_date', 'end_date']
    widgets = {
      'start_date': forms.DateInput(format='%B %d, %Y'),
      'end_date': forms.DateInput(format='%B %d, %Y'),
    }

  def __init__(self, *args, **kwargs):

    super(BaxterBoxBlackoutDateForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control datepicker'
      field.widget.attrs['readonly'] = True
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

  def is_valid(self):
    valid = super(BaxterBoxBlackoutDateForm, self).is_valid()

    if not valid:
      return valid

    cleaned_data = super(BaxterBoxBlackoutDateForm, self).clean()
    start_date = cleaned_data.get('start_date')
    end_date = cleaned_data.get('end_date')

    if end_date < start_date:
      self.add_error('end_date', 'Please select an end date greater than or equal to the start date')
      valid = False

    return valid


class BaxterBoxMessageForm(ModelForm):
  class Meta:
    model = models.BaxterBoxMessage
    fields = ['message', 'status', 'message_type' ]
    widgets = {
      'message': forms.Textarea(attrs={'rows':3}),
    }

  def __init__(self, *args, **kwargs):

    super(BaxterBoxMessageForm, self).__init__(*args, **kwargs)


    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


class ReservationColorForm(ModelForm):
  class Meta:
    model = models.ReservationColor
    fields = ['name', 'color', 'description', 'low_stock', 'low_stock_message', 'rank', 'target', 'order']
    widgets = {
        'color': TextInput(attrs={'type': 'color'}),
        'low_stock_message': forms.Textarea(attrs={'rows':2}),
    }

  def __init__(self, *args, **kwargs):

    super(ReservationColorForm, self).__init__(*args, **kwargs)

    self.fields['target'].label = 'Applicable Entity'
    for field_name, field in list(self.fields.items()):
      if field_name in ['low_stock']:
        field.widget.attrs['class'] = 'form-check-input'
      else:
        field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


class WorkshopForm(ModelForm):

  class Meta:
    model = models.Workshop
    exclude = ('nid', 'created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
      'display_date': forms.Textarea(attrs={'rows':3}),
      'start_date': forms.DateInput(format='%B %d, %Y'),
      'end_date': forms.DateInput(format='%B %d, %Y'),
      'start_time': forms.TimeInput(format='%I:%M %p'),
      'end_time': forms.TimeInput(format='%I:%M %p'),
    }

  def __init__(self, *args, **kwargs):
    super(WorkshopForm, self).__init__(*args, **kwargs)

    self.fields['workshop_category'].queryset = models.WorkshopCategory.objects.all().filter(status='A').order_by('name')
    self.fields['credits'].label = 'ISBE PD Hours'
    self.fields['collaborators'].queryset = models.Collaborator.objects.all().filter(status='A').order_by('name')
    self.fields['teacher_leaders'].label = 'Facilitators'

    for field_name, field in list(self.fields.items()):
      if field_name not in ['enable_registration', 'featured', 'cancelled']:
        if field_name in ['start_date', 'end_date']:
          field.widget.attrs['class'] = 'form-control datepicker'
          field.widget.attrs['readonly'] = True
        elif field_name in ['start_time', 'end_time']:
          field.widget.attrs['class'] = 'form-control timepicker'
          field.input_formats = ['%I:%M %p']
        elif field_name in ['teacher_leaders', 'tags', 'collaborators']:
          field.widget.attrs['class'] = 'form-control select2'
        else:
          field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'

      if field_name == 'name':
        field.label = 'Title'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

class WorkshopRegistrationSettingForm(ModelForm):

  class Meta:
    model = models.WorkshopRegistrationSetting
    exclude = ('created_date', 'modified_date')
    widgets = {
      'open_date': forms.DateInput(format='%B %d, %Y'),
      'close_date': forms.DateInput(format='%B %d, %Y'),
      'open_time': forms.TimeInput(format='%I:%M %p'),
      'close_time': forms.TimeInput(format='%I:%M %p'),
    }


  def __init__(self, *args, **kwargs):
    super(WorkshopRegistrationSettingForm, self).__init__(*args, **kwargs)

    cancelled = False
    if self.instance.id and self.instance.workshop.cancelled:
      cancelled = True

    for field_name, field in list(self.fields.items()):
      if field_name not in ['enable_waitlist']:
        if field_name in ['open_date', 'close_date']:
          field.widget.attrs['class'] = 'form-control datepicker'
          field.widget.attrs['readonly'] = True
        elif field_name in ['open_time', 'close_time']:
          field.widget.attrs['class'] = 'form-control timepicker'
          field.input_formats = ['%I:%M %p']
        else:
          field.widget.attrs['class'] = 'form-control'
          if field_name == 'application':
            if self.instance.id and self.instance.application:
              if self.instance.application.survey_submission.all().count() > 0:
                field.queryset = models.Survey.objects.all().filter(id=self.instance.application.id)
                field.widget.attrs['disabled'] = True

              else:
                field.queryset = models.Survey.objects.all().filter(id=self.instance.application.id) | models.Survey.objects.all().filter(survey_type='W', status='A', registration_setting__isnull=True)
            else:
              field.queryset = models.Survey.objects.all().filter(survey_type='W', status='A', registration_setting__isnull=True)
          elif field_name == 'isbe_link':
            field.label = 'ISBE Link'

      else:
        field.widget.attrs['class'] = 'form-check-input'

      if cancelled:
        field.widget.attrs['disabled'] = True

      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Workshop Registration Form
####################################
class WorkshopRegistrationForm(ModelForm):

  work_place = forms.ModelChoiceField(required=False, label=u'Workplace', queryset=models.WorkPlace.objects.all().filter(status='A').order_by('name'),
                                                     widget=autocomplete.ModelSelect2(url='workplace-autocomplete',
                                                                                     attrs={'data-placeholder': 'Start typing the name of the workplace ...'}),
                                                     help_text="Updating the workplace here only updates the workshop registration - workplace association and not the workplace on the user profile")
  class Meta:
    model = models.Registration
    exclude = ('created_date', 'modified_date')
    widgets = {
      'user': autocomplete.ModelSelect2(url='registrant-autocomplete', forward=['workshop_registration_setting'], attrs={'data-placeholder': 'Start typing the name of the user ...',})
    }

  def __init__(self, *args, **kwargs):

    super(WorkshopRegistrationForm, self).__init__(*args, **kwargs)

    if self.instance.id:
      if hasattr(self.instance, 'registration_to_work_place'):
        self.fields['work_place'].initial = self.instance.registration_to_work_place.work_place
      else:
        self.fields['work_place'].initial = None

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


####################################
# Workshop Registration Questionnaire Form
####################################
class WorkshopRegistrationQuestionnaireForm(ModelForm):

  class Meta:
    model = models.UserProfile
    fields = ['dietary_preference', 'iein']

  def __init__(self, *args, **kwargs):

    super(WorkshopRegistrationQuestionnaireForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      if field_name == 'dietary_preference':
        field.widget.attrs['placeholder'] = 'Your dietary preference will be saved in your profile'
        field.help_text = 'Your dietary preference will be saved in your profile'
      elif field_name == 'iein':
        field.widget.attrs['placeholder'] = 'Your IEIN will be saved in your profile'
        field.help_text = 'Your IEIN will be saved in your profile'


###########################################
# Workshop Email Form for Ad-hoc emails
###########################################
class WorkshopEmailForm(ModelForm):

  registration_statuses = forms.MultipleChoiceField(choices=models.WORKSHOP_REGISTRATION_STATUS_CHOICES, required=False, widget=forms.SelectMultiple(attrs={'size':6}), help_text='One or more registration statuses this email is sent to. Email will be bcc\'d to these addresses.')
  registration_sub_statuses = forms.MultipleChoiceField(choices=models.WORKSHOP_REGISTRATION_SUB_STATUS_CHOICES, required=False, widget=forms.SelectMultiple(attrs={'size':6}), help_text='One or more registration sub statuses this email is sent to. Email will be bcc\'d to these addresses.')

  class Meta:
    model = models.WorkshopEmail
    exclude = ('registration_status', 'registration_sub_status', 'registration_email_addresses', 'email_status', 'sent_date', 'created_date', 'modified_date')
    widgets = {
      'scheduled_date': forms.DateInput(format='%B %d, %Y'),
      'scheduled_time': forms.TimeInput(format='%I:%M %p'),
    }

  def __init__(self, *args, **kwargs):

    super(WorkshopEmailForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name in ['registration_statuses', 'registration_sub_statuses']:
        field.widget.attrs['class'] = 'form-control select2'
      elif field_name == 'scheduled_date':
        field.widget.attrs['class'] = 'form-control datepicker'
        field.widget.attrs['readonly'] = True
      elif field_name == 'scheduled_time':
        field.widget.attrs['class'] = 'form-control timepicker'
        field.input_formats = ['%I:%M %p']
      elif field_name == 'photo_release_incomplete':
        field.widget.attrs['class'] = 'form-check-input'
      else:
        if field_name == 'email_to':
          field.label = 'To'
        elif field_name == 'email_cc':
          field.label = 'Cc'
        elif field_name == 'email_bcc':
          field.label = 'Bcc'
        elif field_name == 'email_subject':
          field.label = 'Subject'
        field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      #field.widget.attrs['placeholder'] = field.help_text

    if self.instance.id:
      self.fields['registration_statuses'].initial = self.instance.get_registration_status()
      self.fields['registration_sub_statuses'].initial = self.instance.get_registration_sub_status()

  def clean(self):
    cleaned_data = super(WorkshopEmailForm, self).clean()
    registration_statuses = cleaned_data.get('registration_statuses')
    registration_sub_statuses = cleaned_data.get('registration_sub_statuses')
    email_to = cleaned_data.get('email_to')
    email_cc = cleaned_data.get('email_cc')
    email_bcc = cleaned_data.get('email_bcc')

    if not registration_statuses and not registration_sub_statuses and email_to is None and email_cc is None and email_bcc is None:
      self.fields['registration_statuses'].widget.attrs['class'] += ' error'
      self.add_error('registration_statuses', 'This field is required if To, Cc and Bcc fields are empty')


####################################
# Registration Email Message Form
####################################
class RegistrationEmailMessageForm(ModelForm):

  class Meta:
    model = models.RegistrationEmailMessage
    exclude = ('created_date', 'modified_date')

  def __init__(self, *args, **kwargs):
    super(RegistrationEmailMessageForm, self).__init__(*args, **kwargs)
    for field_name, field in list(self.fields.items()):
      if field_name in ['include_calendar_invite']:
        field.widget.attrs['class'] = 'form-check-input'
      else:
        field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

########################################################################
# Worksho Registration Email Form for automated registration emails
########################################################################
class WorkshopRegistrationEmailForm(ModelForm):

  class Meta:
    model = models.WorkshopRegistrationEmail
    exclude = ('created_date', 'modified_date')

  def __init__(self, *args, **kwargs):
    super(WorkshopRegistrationEmailForm, self).__init__(*args, **kwargs)
    for field_name, field in list(self.fields.items()):
      if field_name in ['include_calendar_invite']:
        field.widget.attrs['class'] = 'form-check-input'
      else:
        field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

  def clean(self):
    cleaned_data = super(WorkshopRegistrationEmailForm, self).clean()
    registration_status = cleaned_data.get('registration_status')
    workshop = cleaned_data.get('workshop')
    qs = models.WorkshopRegistrationEmail.objects.all().filter(registration_status=registration_status, workshop=workshop)
    if self.instance.pk:
      qs = qs.exclude(pk=self.instance.pk)

    if qs.exists():
      self.fields['registration_status'].widget.attrs['class'] += ' error'
      self.add_error('registration_status', 'Automated registration email with this Registration status already exists.')




####################################
# Workshop Category Form
####################################
class WorkshopCategoryForm(ModelForm):

  class Meta:
    model = models.WorkshopCategory
    exclude = ('created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
    }

  def __init__(self, *args, **kwargs):
    super(WorkshopCategoryForm, self).__init__(*args, **kwargs)
    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Workshop Categories Search Form
####################################
class WorkshopCategoriesSearchForm(forms.Form):

  name = forms.CharField(required=False, max_length=256, help_text='Name of Workshop Category')
  workshop_type = forms.MultipleChoiceField(required=False, choices=(('', '---------'),)+models.WORKSHOP_TYPE_CHOICES)
  status = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.CONTENT_STATUS_CHOICES)
  keywords = forms.CharField(required=False, max_length=60, label=u'Search by Keyword')
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),
                                                       ('name', 'Name'),
                                                       ('type', 'Type'),
                                                       ),
                                              initial='name')
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)



  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(WorkshopCategoriesSearchForm, self).__init__(*args, **kwargs)

    for field_name, field in self.fields.items():
      if field_name == 'workshop_type':
        field.widget.attrs['class'] = 'form-control select2'
      else:
        field.widget.attrs['class'] = 'form-control'

      if field_name == 'keywords':
        field.help_text = 'Search by Keyword searches into name and description'

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]

####################################
# Workplace Form
####################################
class WorkPlaceForm(ModelForm):

  class Meta:
    model = models.WorkPlace
    exclude = ('id', 'created_date', 'modified_date', 'latitude', 'longitude', 'time_from_base', 'distance_from_base')

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    super(WorkPlaceForm, self).__init__(*args, **kwargs)

    if user.is_anonymous or user.userProfile.user_role not in 'AS':
      self.fields.pop('admin_notes')

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text
      if field_name == 'name':
        field.label = 'Workplace Name'
      if field_name == 'district_number':
        field.label = 'District #'

      if field_name == 'status':
        if not self.instance.id:
          field.initial = 'A'


##########################################################
# Workplace Update Form
# to update select few fields in a workplace
##########################################################
class WorkPlaceUpdateForm(ModelForm):

  class Meta:
    model = models.WorkPlace
    fields = ['admin_notes']
    widgets = {
      'admin_notes': forms.Textarea(attrs={'rows':1}),
    }

  def __init__(self, *args, **kwargs):
    super(WorkPlaceUpdateForm, self).__init__(*args, **kwargs)
    self.fields['admin_notes'].label = 'Workplace Notes'

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text


####################################
# Facilitator Form
####################################
class FacilitatorForm(ModelForm):

  class Meta:
    model = models.TeacherLeader
    exclude = ('created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
      'teacher': autocomplete.ModelSelect2(url='facilitator-autocomplete', attrs={'data-placeholder': 'Start typing the name of the user ...',})

    }

  def __init__(self, *args, **kwargs):
    super(FacilitatorForm, self).__init__(*args, **kwargs)

    self.fields['teacher'].label = 'User'
    self.fields['bcse_role'].label = 'BCSE Role'

    for field_name, field in list(self.fields.items()):
      if field_name in ['highlight']:
        field.widget.attrs['class'] = 'form-check-input'
        field.help_text = 'Check this box to display the teacher leader on Our Teacher  Leaders page'
      else:
        field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Team Member Form
####################################
class TeamMemberForm(ModelForm):

  class Meta:
    model = models.Team
    exclude = ('id', 'created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
    }

  def __init__(self, *args, **kwargs):
    super(TeamMemberForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name == 'former_member':
        field.widget.attrs['class'] = 'form-check-input'
        field.label = 'Former Member?'
      else:
        field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Partner Form
####################################
class PartnerForm(ModelForm):

  class Meta:
    model = models.Partner
    exclude = ('id', 'created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
    }

  def __init__(self, *args, **kwargs):
    super(PartnerForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text


####################################
# Collaborator Form
####################################
class CollaboratorForm(ModelForm):

  class Meta:
    model = models.Collaborator
    exclude = ('id', 'created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
    }

  def __init__(self, *args, **kwargs):
    super(CollaboratorForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):

      field.widget.attrs['placeholder'] = field.help_text

      if field_name == 'highlight':
        field.widget.attrs['class'] = 'form-check-input'
        field.help_text = 'Check this box to display the collaborator on Our Partnership page'
      else:
        field.widget.attrs['class'] = 'form-control'


####################################
# HomepageBlock Form
####################################
class HomepageBlockForm(ModelForm):

  class Meta:
    model = models.HomepageBlock
    exclude = ('id', 'created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
    }

  def __init__(self, *args, **kwargs):
    super(HomepageBlockForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text

####################################
# StandalonePage Form
####################################
class StandalonePageForm(ModelForm):

  class Meta:
    model = models.StandalonePage
    exclude = ('id', 'created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
    }

  def __init__(self, *args, **kwargs):
    super(StandalonePageForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text

  def clean_url_alias(self):
    if self.cleaned_data['url_alias']:
      return self.cleaned_data['url_alias'].replace(" ", "_")
    else:
      return self.cleaned_data['url_alias']

####################################
# Survey Form
####################################
class SurveyForm(ModelForm):

  class Meta:
    model = models.Survey
    exclude = ('id', 'created_date', 'modified_date')

  def __init__(self, *args, **kwargs):
    super(SurveyForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name == 'email_confirmation':
        field.widget.attrs['class'] = 'form-check-input'
        field.label = 'Send Email Confirmation to Respondent'
      elif field_name == 'admin_notification':
        field.widget.attrs['class'] = 'form-check-input'
        field.label = 'Send Email Notification to Admins'
      else:
        field.widget.attrs['class'] = 'form-control'
        if field_name == 'resource_url':
          field.label = 'Resource URL'
      field.widget.attrs['placeholder'] = field.help_text


####################################
# SurveysSearch Form
####################################
class SurveysSearchForm(forms.Form):
  name = forms.CharField(required=False, max_length=256, label=u'Survey Name')
  survey_type = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.SURVEY_TYPE_CHOICES)
  status = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.CONTENT_STATUS_CHOICES, label='Survey Status', initial='A')
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),
                                                       ('name', 'Survey Name'),
                                                      ('survey_type', 'Survey Type'),
                                                      ('status', 'Survey Status'),
                                                      ('responses', '# of Responses')), initial='name')
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)


  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(SurveysSearchForm, self).__init__(*args, **kwargs)

    for field_name, field in self.fields.items():
      field.widget.attrs['class'] = 'form-control'

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]


####################################
# SurveyComponent Form
####################################
class SurveyComponentForm(ModelForm):

  class Meta:
    model = models.SurveyComponent
    exclude = ('id', 'created_date', 'modified_date')

  def __init__(self, *args, **kwargs):
    super(SurveyComponentForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name in ['is_required', 'display_other_option']:
        field.widget.attrs['class'] = 'form-check-input'
      else:
        field.widget.attrs['class'] = 'form-control'

      field.widget.attrs['placeholder'] = field.help_text

####################################
# SurveyResponse Form
####################################
class SurveyResponseForm(ModelForm):

  class Meta:
    model = models.SurveyResponse
    exclude = ('id', 'submission', 'survey_component', 'created_date', 'modified_date')

  def __init__(self, *args, **kwargs):
    super(SurveyResponseForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text

  def save(self, commit=True):
    response = super(SurveyResponseForm, self).save(commit=True)
    response.created_date = response.submission.created_date
    response.modified_date = response.submission.modified_date
    response.save()
    return response

####################################
# SurveySubmission Form
####################################
class SurveySubmissionForm(ModelForm):
  work_place = forms.ModelChoiceField(required=False, label=u'Workplace', queryset=models.WorkPlace.objects.all().filter(status='A').order_by('name'),
                                                      widget=autocomplete.ModelSelect2(url='workplace-autocomplete',
                                                                                       attrs={'data-placeholder': 'Start typing the name of the workplace ...'}),
                                                      help_text="Updating the workplace here only updates the survey submission - workplace association and not the workplace on the user profile")
  response_date = forms.DateField(required=False, label=u'Response Date')

  class Meta:
    model = models.SurveySubmission
    fields = ['user', 'status', 'admin_notes']
    widgets = {
      'admin_notes': forms.Textarea(attrs={'rows':3}),

    }

  def __init__(self, *args, **kwargs):
    super(SurveySubmissionForm, self).__init__(*args, **kwargs)

    if self.instance.UUID and hasattr(self.instance, 'survey_submission_to_work_place'):
      self.fields['work_place'].initial = self.instance.survey_submission_to_work_place.work_place

    if self.instance.UUID and self.instance.created_date:
      self.fields['response_date'].initial = self.instance.created_date

    for field_name, field in list(self.fields.items()):
      if field_name == 'response_date':
         field.widget.attrs['class'] = 'form-control datepicker'
         field.widget.attrs['readonly'] = True
      elif field_name == 'user':
        field.widget.attrs['class'] = 'form-control select2'
        if self.instance.user and self.instance.user.id:
          field.widget.attrs['disabled'] = True

      else:
        field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text

  def save(self, commit=True):
    submission = super(SurveySubmissionForm, self).save(commit=True)
    if self.cleaned_data['response_date']:
      submission.created_date = self.cleaned_data['response_date']
      submission.modified_date = self.cleaned_data['response_date']
    submission.save()
    return submission

####################################
# Survey Submissions Search Form
####################################
class SurveySubmissionsSearchForm(forms.Form):
  email = forms.CharField(required=False, max_length=256, label=u'Email')
  first_name = forms.CharField(required=False, max_length=256, label=u'First Name')
  last_name = forms.CharField(required=False, max_length=256, label=u'Last Name')
  user_role = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.USER_ROLE_CHOICES)
  work_place = forms.ModelChoiceField(required=False, label=u'Workplace', queryset=models.WorkPlace.objects.all().order_by('name'),
                                                      widget=autocomplete.ModelSelect2(url='workplace-all-autocomplete',
                                                                                       attrs={'data-placeholder': 'Start typing the name if your workplace ...'}))

  response_after = forms.DateField(required=False, label=u'Response Date on/after')
  response_before = forms.DateField(required=False, label=u'Response Date on/before')
  status = forms.MultipleChoiceField(required=False, choices=models.SURVEY_SUBMISSION_STATUS_CHOICES, label='Response Status')
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),
                                                       ('email', 'Email'),
                                                      ('first_name', 'First Name'),
                                                      ('last_name', 'Last Name'),
                                                      ('created_date_desc', 'Created Date (Desc)'),
                                                      ('created_date_asc', 'Created Date (Asc)')), initial='created_date_desc')
  columns = forms.MultipleChoiceField(required=False, choices=models.SURVEY_SUBMISSION_TABLE_COLUMN_CHOICES, initial=['SI', 'EM', 'FN', 'WP', 'CE', 'AN', 'CD','ST'],  widget=forms.SelectMultiple(attrs={'size':6}), label=u'Display Columns', help_text='On Windows use Ctrl+Click to make multiple selection. On a Mac use Cmd+Click to make multiple selection')
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)


  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(SurveySubmissionsSearchForm, self).__init__(*args, **kwargs)

    for field_name, field in self.fields.items():
      if field_name in ['response_after', 'response_before']:
        field.widget.attrs['class'] = 'form-control datepicker'
      else:
        field.widget.attrs['class'] = 'form-control'

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]


####################################
# Vignette Form
####################################
class VignetteForm(ModelForm):

  class Meta:
    model = models.Vignette
    exclude = ('id', 'created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
      'attachment': widgets.FileInput,
    }

  def __init__(self, *args, **kwargs):
    super(VignetteForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name == 'featured':
        field.widget.attrs['class'] = 'form-check-input'
      else:
        field.widget.attrs['class'] = 'form-control'

      field.widget.attrs['placeholder'] = field.help_text

####################################
# Reservations Search Form
####################################
class ReservationsSearchForm(forms.Form):

  user = forms.ModelChoiceField(required=False, label=u'Requesting User', queryset=models.UserProfile.objects.all().order_by('user__first_name', 'user__last_name'), widget=autocomplete.ModelSelect2(url='user-autocomplete', attrs={'data-placeholder': 'Start typing the name of the user ...',}))
  work_place = forms.ModelChoiceField(required=False, label=u"Requesting user's Workplace", queryset=models.WorkPlace.objects.all(), widget=autocomplete.ModelSelect2(url='workplace-all-autocomplete', attrs={'data-placeholder': 'Start typing the name of the workplace ...'}),
                                  )
  assignee = forms.ModelChoiceField(required=False, label=u'Delivery Assigned To', queryset=models.UserProfile.objects.all().filter(user_role__in=['A', 'S']).order_by('user__last_name', 'user__first_name'))
  pickup_assignee = forms.ModelChoiceField(required=False, label=u'Pickup Assigned To', queryset=models.UserProfile.objects.all().filter(user_role__in=['A', 'S']).order_by('user__last_name', 'user__first_name'))

  activity = forms.ModelMultipleChoiceField(required=False, queryset=models.Activity.objects.all().order_by('name'), widget=forms.SelectMultiple(attrs={'size':6}))
  consumable = forms.ModelMultipleChoiceField(required=False, queryset=models.Consumable.objects.all().order_by('name'), widget=forms.SelectMultiple(attrs={'size':6}))
  equipment = forms.ModelMultipleChoiceField(required=False, queryset=models.EquipmentType.objects.all().order_by('order'), widget=forms.SelectMultiple(attrs={'size':6}))
  delivery_after = forms.DateField(required=False, label=u'Delivery on/after')
  return_before = forms.DateField(required=False, label=u'Return on/before')
  feedback_status = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.RESERVATION_FEEDBACK_STATUS_CHOICES)
  status = forms.MultipleChoiceField(required=False, label=u'Reservation Status', choices=models.RESERVATION_STATUS_CHOICES, initial=['O', 'R', 'U'], widget=forms.SelectMultiple(attrs={'size':6}))
  keywords = forms.CharField(required=False, max_length=60, label=u'Search by Keyword')
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),
                                                       ('new_messages', 'New Messages'),
                                                       ('user', 'User'),
                                                       ('activity', 'Activity'),
                                                       ('delivery_date_desc', 'Delivery Date (Desc)'),
                                                       ('delivery_date_asc', 'Delivery Date (Asc)'),
                                                       ('return_date_desc', 'Return Date (Desc)'),
                                                       ('return_date_asc', 'Return Date (Asc)'),
                                                       ('created_date_desc', 'Created Date (Desc)'),
                                                       ('created_date_asc', 'Created Date (Asc)'),
                                                       ('status', 'Reservation Status')))
  columns = forms.MultipleChoiceField(required=False, choices=models.RESERVATION_TABLE_COLUMN_CHOICES, initial=['CR', 'UR', 'KT', 'NC', 'NS', 'CO', 'EQ', 'CC', 'DA', 'DD', 'RD', 'AN', 'HP', 'ST', 'GG', 'GO', 'GL'],  widget=forms.SelectMultiple(attrs={'size':6}), label=u'Display Columns')
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)
  color = forms.ModelMultipleChoiceField(required=False, label=u'Box Sub-Status', queryset=models.ReservationColor.objects.all().filter(target__in=['R', 'B']))


  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(ReservationsSearchForm, self).__init__(*args, **kwargs)

    if user.is_anonymous or user.userProfile.user_role not in 'AS':
      self.fields.pop('user')
      self.fields.pop('work_place')
      self.fields.pop('assignee')
      self.fields.pop('pickup_assignee')
      self.fields.pop('color')
      self.fields.pop('feedback_status')
      self.fields.pop('consumable')
    else:
      self.fields['rows_per_page'].initial = 75

    for field_name, field in self.fields.items():
      if field_name in ['delivery_after', 'return_before']:
        field.widget.attrs['class'] = 'form-control datepicker'
        field.widget.attrs['readonly'] = True
      elif field_name in ['activity', 'equipment', 'consumable']:
        field.widget.attrs['class'] = 'form-control select2'
      else:
        field.widget.attrs['class'] = 'form-control'

      if field.help_text:
        field.widget.attrs['placeholder'] = field.help_text

      if field_name in ['equipment', 'status', 'columns', 'color']:
        field.help_text = 'On Windows use Ctrl+Click to make multiple selection. On a Mac use Cmd+Click to make multiple selection'
      if field_name == 'sort_by':
        field.help_text = 'The default sort is (Delivery Date followed by Return date) in descending order for Unconfirmed/Confirmed/Completed/Cancelled reservations and (Return Date) in descending order for Checked Out reservations.'
      if field_name == 'keywords':
        field.help_text = 'Search by Keyword searches into activity name, user first/last name, user notes and admin notes'

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]


####################################
# Workshop Search Form
####################################
class WorkshopsSearchForm(forms.Form):

  workshop_category = forms.ModelChoiceField(required=False, queryset=models.WorkshopCategory.objects.all())
  starts_after = forms.DateField(required=False, label=u'Starts on/after')
  ends_before = forms.DateField(required=False, label=u'Ends on/before')
  registration_open = forms.ChoiceField(choices=(('', '---------'),)+models.YES_NO_CHOICES, initial='', widget=forms.Select(), required=False)
  cancelled = forms.ChoiceField(choices=(('', '---------'),)+models.YES_NO_CHOICES, initial='', widget=forms.Select(), required=False)
  status = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.CONTENT_STATUS_CHOICES, initial='A')
  keywords = forms.CharField(required=False, max_length=60, label=u'Search by Keyword')
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),('title', 'Title'),
                                                       ('start_date_desc', 'Start Date (Desc)'),
                                                       ('start_date_asc', 'Start Date (Asc)'),
                                                       ('created_date_desc', 'Created Date (Desc)'),
                                                       ('created_date_asc', 'Created Date (Asc)'),), initial='start_date_desc')
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(WorkshopsSearchForm, self).__init__(*args, **kwargs)


    self.fields['workshop_category'].queryset = models.WorkshopCategory.objects.all().filter(status='A').order_by('name')

    if user.is_anonymous or user.userProfile.user_role not in 'AS':
      self.fields.pop('workshop_category')
      self.fields.pop('starts_after')
      self.fields.pop('ends_before')
      self.fields.pop('registration_open')
      self.fields.pop('cancelled')
      self.fields.pop('status')
      self.fields['sort_by'].initial = 'start_date_asc'
      #setting rows_per_age to 0 will return all the rows without paging
      self.fields['rows_per_page'].initial = 0

    sub_tag_ids = models.Workshop.objects.all().values_list('tags', flat=True)
    tag_ids = models.SubTag.objects.all().filter(id__in=list(sub_tag_ids)).values_list('tag', flat=True)

    for tag_id in list(set(tag_ids)):
      tag = models.Tag.objects.get(id=tag_id)
      if tag.status == 'A':
        sub_tags = models.SubTag.objects.all().filter(tag=tag, status='A', id__in=list(sub_tag_ids))
        self.fields['tag_'+str(tag.id)] = forms.MultipleChoiceField(
                                                required=False,
                                                widget=forms.SelectMultiple(),
                                                choices=[(sub.id, sub.name) for sub in sub_tags],
                                            )
        self.fields['tag_'+str(tag.id)].label = tag.name


    for field_name, field in self.fields.items():
      if field_name in ['starts_after', 'ends_before']:
        field.widget.attrs['class'] = 'form-control datepicker'
        field.widget.attrs['readonly'] = True
      elif 'tag' in field_name:
        field.widget.attrs['class'] = 'form-control select2'
        field.widget.attrs['aria-describedby'] = field.label
      else:
        field.widget.attrs['class'] = 'form-control'

      if field.help_text:
        field.widget.attrs['placeholder'] = field.help_text
      if field_name == 'keywords':
        field.help_text = 'Search by Keyword searches into workshop name, subtitle, workshop category, facilitator first/last name, summary, description and location'

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]



####################################
# Registrants Search Form
####################################
class WorkshopsRegistrantsSearchForm(forms.Form):

  workshop_category = forms.ModelMultipleChoiceField(required=False, queryset=models.WorkshopCategory.objects.all().order_by(Lower('name')), widget=forms.SelectMultiple(attrs={'size':6}))
  workshop = forms.ModelMultipleChoiceField(required=False, queryset=models.Workshop.objects.all().filter(cancelled=False).order_by(Lower('name'), 'start_date').distinct(), widget=forms.SelectMultiple(attrs={'size':6}))
  #user = forms.ModelChoiceField(required=False, label=u'Registrant', queryset=models.UserProfile.objects.all().order_by('user__first_name', 'user__last_name'), widget=autocomplete.ModelSelect2(url='user-autocomplete', attrs={'data-placeholder': 'Start typing the name of the user ...',}))
  user = forms.ModelMultipleChoiceField(required=False, label=u'Registrant', queryset=models.UserProfile.objects.all().order_by('user__first_name', 'user__last_name'), widget=autocomplete.ModelSelect2Multiple(url='user-autocomplete', attrs={'data-placeholder': 'Start typing the name of the user ...',}))
  user_role = forms.MultipleChoiceField(required=False, label=u"Registrant's User Role", choices=models.USER_ROLE_CHOICES)
  #work_place = forms.ModelChoiceField(required=False, label=u"Registrant's Workplace", queryset=models.WorkPlace.objects.all(), widget=autocomplete.ModelSelect2(url='workplace-autocomplete', attrs={'data-placeholder': 'Start typing the name of the workplace ...'}),)
  work_place = forms.ModelMultipleChoiceField(required=False, label=u"Registrant's Workplace", queryset=models.WorkPlace.objects.all(), widget=forms.SelectMultiple(attrs={'size':6}))
  #year = forms.ChoiceField(required=False, choices=models.YEAR_CHOICES)
  starts_after = forms.DateField(required=False, label=u'Starts on/after')
  ends_before = forms.DateField(required=False, label=u'Ends on/before')

  status = forms.MultipleChoiceField(required=False, label=u"Registration Status", choices=models.WORKSHOP_REGISTRATION_STATUS_CHOICES, widget=forms.SelectMultiple(attrs={'size':6}))
  sub_status = forms.MultipleChoiceField(required=False, label=u"Registration Sub Status",  choices=models.WORKSHOP_REGISTRATION_SUB_STATUS_CHOICES, widget=forms.SelectMultiple(attrs={'size':6}))

  keywords = forms.CharField(required=False, max_length=60, label=u'Search by Keyword')
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),('attendance', 'Attendance'), ('title', 'Workshop Title'), ('start_date', 'Workshop Start Date'), ('status', 'Registration Status'), ('workplace', 'Workplace'), ('user', 'User')))
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(WorkshopsRegistrantsSearchForm, self).__init__(*args, **kwargs)

    sub_tag_ids = models.Workshop.objects.all().values_list('tags', flat=True)
    tag_ids = models.SubTag.objects.all().filter(id__in=list(sub_tag_ids)).values_list('tag', flat=True)

    for tag_id in list(set(tag_ids)):
      tag = models.Tag.objects.get(id=tag_id)
      if tag.status == 'A':
        sub_tags = models.SubTag.objects.all().filter(tag=tag, status='A', id__in=list(sub_tag_ids))
        self.fields['tag_'+str(tag.id)] = forms.MultipleChoiceField(
                                                required=False,
                                                widget=forms.SelectMultiple(),
                                                choices=[(sub.id, sub.name) for sub in sub_tags],
                                            )
        self.fields['tag_'+str(tag.id)].label = tag.name

    for field_name, field in self.fields.items():

      if field_name in ['starts_after', 'ends_before']:
        field.widget.attrs['class'] = 'form-control datepicker'
        field.widget.attrs['readonly'] = True
      elif field_name in ['workshop_category', 'workshop', 'status', 'sub_status', 'user', 'work_place', 'user_role'] or 'tag' in field_name:
        field.widget.attrs['class'] = 'form-control select2'
      else:
        field.widget.attrs['class'] = 'form-control'

      field.widget.attrs['placeholder'] = field.help_text

      if field_name == 'keywords':
        field.help_text = 'Search by Keyword searches into workshop name, subtitle, workshop category, facilitator first/last name, summary, description and location'

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]

    self.fields['workshop'].label_from_instance = lambda obj: "%s%s (%s)" % (obj.name[:50], '...' if len(obj.name) > 50 else '', obj.start_date.year)


####################################
# User Search Form
####################################
class UsersSearchForm(forms.Form):
  email = forms.CharField(required=False, max_length=256, label=u'Email')
  first_name = forms.CharField(required=False, max_length=256, label=u'First Name')
  last_name = forms.CharField(required=False, max_length=256, label=u'Last Name')
  user_role = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.USER_ROLE_CHOICES)
  work_place = forms.ModelChoiceField(required=False, label=u"Workplace", queryset=models.WorkPlace.objects.all().order_by('name'),
                                                      widget=autocomplete.ModelSelect2(url='workplace-all-autocomplete',
                                                                                       attrs={'data-placeholder': 'Start typing the name if your workplace ...'}))
  joined_after = forms.DateField(required=False, label=u'Joined on/after')
  joined_before = forms.DateField(required=False, label=u'Joined on/before')
  status = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.CONTENT_STATUS_CHOICES)
  subscribed = forms.ChoiceField(required=False, choices=(('', '---------'),('Y', 'Yes'),('N', 'No'),))
  photo_release_complete = forms.ChoiceField(required=False, choices=(('', '---------'),('Y', 'Yes'),('N', 'No'),))
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),
                                                       ('email', 'Email'),
                                                      ('first_name', 'First Name'),
                                                      ('last_name', 'Last Name'),
                                                      ('date_joined_desc', 'Date Joined (Desc)'),
                                                      ('date_joined_asc', 'Date Joined (Asc)'),
                                                      ('last_updated_desc', 'Last Updated (Desc)'),
                                                      ('last_updated_asc', 'Last Updated (Asc)')), initial='date_joined_desc')
  columns = forms.MultipleChoiceField(required=False, choices=models.USER_TABLE_COLUMN_CHOICES, initial=['ID', 'EM', 'FN', 'RL', 'WP', 'ST', 'JD', 'LL', 'LU'],  widget=forms.SelectMultiple(attrs={'size':6}), label=u'Display Columns', help_text='On Windows use Ctrl+Click to make multiple selection. On a Mac use Cmd+Click to make multiple selection')
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)


  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(UsersSearchForm, self).__init__(*args, **kwargs)

    for field_name, field in self.fields.items():
      if field_name in ['joined_after', 'joined_before']:
        field.widget.attrs['class'] = 'form-control datepicker'
        field.widget.attrs['readonly'] = True
      else:
        field.widget.attrs['class'] = 'form-control'

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]


####################################
# Workplace Search Form
####################################
class WorkPlacesSearchForm(ModelForm):
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),
                                                       ('name', 'Name'),
                                                       ('users_desc', '# of Users (Desc)'),
                                                       ('users_asc', '# of Users (Asc)'),
                                                      ('status', 'Status'),
                                                      ('created_date_desc', 'Created Date (Desc)'),
                                                      ('created_date_asc', 'Created Date (Asc)')), initial='name')
  status = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.CONTENT_STATUS_CHOICES)
  columns = forms.MultipleChoiceField(required=False, choices=models.WORKPLACE_TABLE_COLUMN_CHOICES, initial=['ID', 'NM', 'WT', 'DN', 'S1', 'S2', 'CT', 'SA', 'NU', 'ST', 'CD'],  widget=forms.SelectMultiple(attrs={'size':6}), label=u'Display Columns', help_text='On Windows use Ctrl+Click to make multiple selection. On a Mac use Cmd+Click to make multiple selection')
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)

  class Meta:
    model = models.WorkPlace
    exclude = ('id', 'created_date', 'modified_date')

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')

    super(WorkPlacesSearchForm, self).__init__(*args, **kwargs)

    self.fields['work_place_type'].label = 'Workplace Type'

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      if field_name == 'district_number':
        field.label = 'District #'

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]


####################################
# Baxter Box Usage Search Form
####################################
class BaxterBoxUsageSearchForm(forms.Form):
  from_date = forms.DateField(required=False, label=u'From')
  to_date = forms.DateField(required=False, label=u'To')
  work_place = forms.ModelMultipleChoiceField(required=False, label=u"Requesting user's Workplace", queryset=models.WorkPlace.objects.all(), widget=forms.SelectMultiple(attrs={'size':7}))
  user = forms.ModelMultipleChoiceField(required=False, label=u'Requesting User', queryset=models.UserProfile.objects.all().order_by('user__first_name', 'user__last_name'), widget=autocomplete.ModelSelect2Multiple(url='user-autocomplete', attrs={'data-placeholder': 'Start typing the name of the user ...',}))
  activity = forms.ModelMultipleChoiceField(required=False, queryset=models.Activity.objects.all().order_by('name'), widget=forms.SelectMultiple(attrs={'size':7}))
  equipment = forms.ModelMultipleChoiceField(required=False, queryset=models.EquipmentType.objects.all().order_by('order'), widget=forms.SelectMultiple(attrs={'size':7}))
  consumable = forms.ModelMultipleChoiceField(required=False, queryset=models.Consumable.objects.all().order_by('name'), widget=forms.SelectMultiple(attrs={'size':5}))
  status = forms.MultipleChoiceField(required=False, choices=models.RESERVATION_STATUS_CHOICES, widget=forms.SelectMultiple(attrs={'size':5}))
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),('name', 'Name'), ('reservations', '# of Reservations'), ('kits', '# of Kits'), ('consumables', '# of Consumables'), ('total_cost', 'Total Cost'), ('teachers', '# of Teachers'), ('workplaces', '# of Workplaces'), ('classes', '# of Classes'), ('students', '# of Students')), initial='name')
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(BaxterBoxUsageSearchForm, self).__init__(*args, **kwargs)

    sub_tag_ids = list(models.EquipmentType.objects.all().values_list('tags', flat=True)) + list(models.Activity.objects.all().values_list('tags', flat=True))
    tag_ids = models.SubTag.objects.all().filter(id__in=sub_tag_ids).values_list('tag', flat=True)

    for tag_id in list(set(tag_ids)):
      tag = models.Tag.objects.get(id=tag_id)
      if tag.status == 'A':
        sub_tags = models.SubTag.objects.all().filter(tag=tag, status='A', id__in=sub_tag_ids)
        self.fields['tag_'+str(tag.id)] = forms.MultipleChoiceField(
                                                required=False,
                                                widget=forms.SelectMultiple(),
                                                choices=[(sub.id, sub.name) for sub in sub_tags],
                                            )
        self.fields['tag_'+str(tag.id)].label = tag.name


    for field_name, field in self.fields.items():
      if field_name in ['from_date', 'to_date']:
        field.widget.attrs['class'] = 'form-control datepicker'
        field.widget.attrs['readonly'] = True
      elif field_name in ['work_place', 'user', 'activity', 'equipment', 'consumable', 'status'] or 'tag' in field_name:
        field.widget.attrs['class'] = 'form-control select2'
      else:
        field.widget.attrs['class'] = 'form-control'

      if field.help_text:
        field.widget.attrs['placeholder'] = field.help_text

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]

##################################################
# Registrants Search Form For A Single Workshop
##################################################
class WorkshopRegistrantsSearchForm(forms.Form):
  email = forms.CharField(required=False, max_length=256, label=u'Email')
  first_name = forms.CharField(required=False, max_length=256, label=u'First Name')
  last_name = forms.CharField(required=False, max_length=256, label=u'Last Name')
  user_role = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.USER_ROLE_CHOICES)
  work_place = forms.ModelChoiceField(required=False, label=u'Workplace', queryset=models.WorkPlace.objects.all().order_by('name'),
                                                      widget=autocomplete.ModelSelect2(url='workplace-all-autocomplete',
                                                                                       attrs={'data-placeholder': 'Start typing the name if your workplace ...'}))
  registration_status = forms.MultipleChoiceField(required=False, choices=models.WORKSHOP_REGISTRATION_STATUS_CHOICES, widget=forms.SelectMultiple(attrs={'size':6}))
  registration_sub_status = forms.MultipleChoiceField(required=False, choices=models.WORKSHOP_REGISTRATION_SUB_STATUS_CHOICES, widget=forms.SelectMultiple(attrs={'size':6}))

  subscribed = forms.ChoiceField(required=False, choices=(('', '---------'),('Y', 'Yes'),('N', 'No'),))
  photo_release_complete = forms.ChoiceField(required=False, choices=(('', '---------'),('Y', 'Yes'),('N', 'No'),))
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),
                                                       ('email', 'Email'),
                                                      ('first_name', 'First Name'),
                                                      ('last_name', 'Last Name'),
                                                      ('created_date_desc', 'Created Date (Desc)'),
                                                      ('created_date_asc', 'Created Date (Asc)')), initial='created_date_desc')

  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(WorkshopRegistrantsSearchForm, self).__init__(*args, **kwargs)

    for field_name, field in self.fields.items():
      if field_name in ['registration_status', 'registration_sub_status']:
        field.widget.attrs['class'] = 'form-control select2'
      else:
        field.widget.attrs['class'] = 'form-control'

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]

##################################################
# Vignettes Search Form
##################################################
class VignettesSearchForm(forms.Form):
  title = forms.CharField(required=False, max_length=256, label=u'Title')
  blurb = forms.CharField(required=False, max_length=256, label=u'Blurb')
  featured = forms.ChoiceField(required=False, choices=(('', '---------'),('Y', 'Yes'),('N', 'No'),))
  status = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.CONTENT_STATUS_CHOICES)
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(VignettesSearchForm, self).__init__(*args, **kwargs)

    if user.is_anonymous or user.userProfile.user_role in ['T', 'P']:
      self.fields.pop('featured')
      self.fields.pop('status')

    for field_name, field in self.fields.items():
      field.widget.attrs['class'] = 'form-control'

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]

##################################################
# Giveaway Form
##################################################
class GiveawayForm(ModelForm):

  class Meta:
    model = models.Giveaway
    exclude = ('id', 'created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
    }

  def __init__(self, *args, **kwargs):
    super(GiveawayForm, self).__init__(*args, **kwargs)

    for field_name, field in self.fields.items():
      field.widget.attrs['class'] = 'form-control'
      if field_name in ['on_hold_quantity', 'given_quantity']:
        field.widget.attrs['readonly'] = True

##################################################
# Giveaway Request Form
##################################################
class GiveawayRequestForm(ModelForm):

  class Meta:
    model = models.GiveawayRequest
    exclude = ('id', 'created_date', 'modified_date')
    widgets = {
      'user': autocomplete.ModelSelect2(url='user-autocomplete', attrs={'data-placeholder': 'Start typing the name of the user ...',}),
      'work_place': autocomplete.ModelSelect2(url='workplace-autocomplete',
                                              attrs={'data-placeholder': 'Start typing the name of the workplace ...'}),
    }

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    super(GiveawayRequestForm, self).__init__(*args, **kwargs)

    for field_name, field in self.fields.items():
      if field_name == 'delivery_date':
        field.widget.attrs['class'] = 'form-control datepicker'
        field.widget.attrs['readonly'] = True
      else:
        field.widget.attrs['class'] = 'form-control'

    if user.user_role not in ['A', 'S']:
      self.fields.pop('delivery_status')
      self.fields.pop('delivery_date')
      self.fields.pop('status')
    elif self.instance.id is None:
      self.fields.pop('delivery_status')
      self.fields.pop('delivery_date')


    if user.user_role in ['A', 'S']:
      self.fields['work_place'].label = 'Please confirm user''s workplace'
    else:
      self.fields['work_place'].label = 'Please confirm your workplace'
      self.fields['work_place'].initial = user.work_place

    if self.instance.id:
      self.fields['giveaway'].queryset = models.Giveaway.objects.all().filter(id=self.instance.giveaway.id)
    else:
      self.fields['giveaway'].queryset = models.Giveaway.objects.all().filter(status='A', available_quantity__gt=0)

    if self.instance.id:
      self.fields['user'].widget.attrs['disabled'] = True
      self.fields['giveaway'].widget.attrs['disabled'] = True
      #self.fields['requested_quantity'].widget.attrs['disabled'] = True

  def is_valid(self):
    valid = super(GiveawayRequestForm, self).is_valid()
    if not valid:
      return valid

    cleaned_data = super(GiveawayRequestForm, self).clean()


    giveaway = cleaned_data.get('giveaway')
    requested_quantity = cleaned_data.get('requested_quantity')
    delivery_status = cleaned_data.get('delivery_status')
    delivery_date = cleaned_data.get('delivery_date')
    current_status = cleaned_data.get('status')

    #check if requested quantity meets the max quantity allowed contraint
    max_quantity = None
    #creating a new request
    if self.instance.id is None:
      if current_status is None or current_status in ['A', 'P']:
        if giveaway.max_quantity_allowed:
          max_quantity = min(giveaway.max_quantity_allowed, giveaway.available_quantity)
        else:
          max_quantity = giveaway.available_quantity

    #editing and existing request
    else:
      initial_data = self.initial
      initial_status = initial_data['status']
      initial_requested_quantity = initial_data['requested_quantity']

      # if status moves between pending and approved and the requested quantity increases
      if initial_status in ['P', 'A'] and current_status in ['P', 'A'] and requested_quantity > initial_requested_quantity:
        if giveaway.max_quantity_allowed:
          max_quantity = min(giveaway.max_quantity_allowed, giveaway.available_quantity+initial_requested_quantity)
        else:
          max_quantity = giveaway.available_quantity+initial_requested_quantity

      # if cancelled/denied request is changed to pending or approved, treat this like a new request
      elif initial_status in ['C', 'D'] and current_status in ['P', 'A']:
        if giveaway.max_quantity_allowed:
          max_quantity = min(giveaway.max_quantity_allowed, giveaway.available_quantity)
        else:
          max_quantity = giveaway.available_quantity

    if max_quantity and requested_quantity > max_quantity:
      self.add_error('requested_quantity', 'Please select a quantity not more than %s' % max_quantity)
      valid = False

    if delivery_status and delivery_status in ['S', 'D']:
      if not delivery_date:
        self.add_error('delivery_date', 'Please select a delivery date')
        valid = False

    return valid

##################################################
# Giveaway Search Form
##################################################
class GiveawaysSearchForm(forms.Form):

  name = forms.CharField(required=False, max_length=256, label=u'Name')
  status = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.CONTENT_STATUS_CHOICES)
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),
                                                       ('name', 'Name'),
                                                       ('status', 'Status'),
                                                       ))
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(GiveawaysSearchForm, self).__init__(*args, **kwargs)

    for field_name, field in self.fields.items():
      field.widget.attrs['class'] = 'form-control'

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]


##################################################
# GiveawayRequest Search Form
##################################################
class GiveawayRequestsSearchForm(forms.Form):

  user = forms.ModelChoiceField(required=False, label=u'Requesting User', queryset=models.UserProfile.objects.all().order_by('user__first_name', 'user__last_name'), widget=autocomplete.ModelSelect2(url='user-autocomplete', attrs={'data-placeholder': 'Start typing the name of the user ...',}))
  work_place = forms.ModelChoiceField(required=False, label=u"Requesting user's Workplace", queryset=models.WorkPlace.objects.all(), widget=autocomplete.ModelSelect2(url='workplace-autocomplete', attrs={'data-placeholder': 'Start typing the name of the workplace ...'}))
  giveaway = forms.ModelMultipleChoiceField(required=False, queryset=models.Giveaway.objects.all(), widget=forms.SelectMultiple(attrs={'size':6}))
  delivery_after = forms.DateField(required=False, label=u'Delivery on/after')
  delivery_before = forms.DateField(required=False, label=u'Delivery on/before')
  request_status = forms.MultipleChoiceField(required=False, choices=models.GIVEAWAY_STATUS_CHOICES, widget=forms.SelectMultiple(attrs={'size':6}))
  delivery_status = forms.MultipleChoiceField(required=False, choices=models.GIVEAWAY_DELIVERY_STATUS_CHOICES, widget=forms.SelectMultiple(attrs={'size':6}))
  keywords = forms.CharField(required=False, max_length=60, label=u'Search by Keyword')
  sort_by = forms.ChoiceField(required=False, choices=(('', '---------'),
                                                       ('user', 'User'),
                                                       ('work_place', 'Workplace'),
                                                       ('giveaway', 'Giveaway'),
                                                       ('delivery_date_desc', 'Delivery Date (Desc)'),
                                                       ('delivery_date_asc', 'Delivery Date (Asc)'),
                                                       ('created_date_desc', 'Created Date (Desc)'),
                                                       ('created_date_asc', 'Created Date (Asc)'),
                                                       ('request_status', 'Request Status'),
                                                       ('delivery_status', 'Delivery Status')))
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(GiveawayRequestsSearchForm, self).__init__(*args, **kwargs)

    for field_name, field in self.fields.items():
      if field_name in ['delivery_after', 'delivery_before']:
        field.widget.attrs['class'] = 'form-control datepicker'
      elif field_name in ['giveaway', 'request_status', 'delivery_status']:
        field.widget.attrs['class'] = 'form-control select2'
      else:
        field.widget.attrs['class'] = 'form-control'

      if field.help_text:
        field.widget.attrs['placeholder'] = field.help_text

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]

