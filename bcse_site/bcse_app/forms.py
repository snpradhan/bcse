from django import forms
from django.forms import ModelForm
from bcse_app import models
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout


####################################
# Login Form
####################################
class SignInForm (forms.Form):
  username_email = forms.CharField(required=True, max_length=75, label='Username or Email',
                              error_messages={'required': 'Username or email is required'})
  password = forms.CharField(required=True, widget=forms.PasswordInput(render_value=False), label='Password',
                              error_messages={'required': 'Password is required'})

  def __init__(self, *args, **kwargs):
    super(SignInForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


  def clean_username_email(self):
    return self.cleaned_data['username_email'].strip()

  def clean(self):
    cleaned_data = super(SignInForm, self).clean()
    username_email = cleaned_data.get('username_email')
    password = cleaned_data.get('password')

    if username_email is None:
      self.fields['username_email'].widget.attrs['class'] += ' error'
    if password is None:
      self.fields['password'].widget.attrs['class'] += ' error'

    if username_email is not None:
      if User.objects.filter(username=username_email.lower()).count() == 0 and User.objects.filter(email=username_email.lower()).count() == 0:
        self.add_error('username_email', 'Username or email is incorrect.')
        self.fields['username_email'].widget.attrs['class'] += ' error'
      elif password is not None:
        username = None
        if User.objects.filter(username=username_email.lower()).count() == 1:
          username = username_email.lower()
        elif User.objects.filter(email=username_email.lower()).count() == 1:
          username = User.objects.get(email=username_email.lower()).username.lower()

        user = authenticate(username=username, password=password)
        if user is None:
          self.add_error('password', 'Password is incorrect.')
          self.fields['password'].widget.attrs['class'] += ' error'

####################################
# Registration Form
####################################
class SignUpForm (forms.Form):
  email = forms.EmailField(required=True, max_length=75, label='Email')
  confirm_email = forms.EmailField(required=True, max_length=75, label='Confirm Email')
  username = forms.RegexField(required=True, regex=r'^\w+$', max_length=30, label='Username',
                              error_messages={'invalid': 'Usernames may only contain letters, numbers, and underscores (_)'})
  first_name = forms.CharField(required=True, max_length=30, label='First name')
  last_name = forms.CharField(required=True, max_length=30, label='Last name')
  password1 = forms.CharField(required=True, widget=forms.PasswordInput(render_value=False), label='Password')
  password2 = forms.CharField(required=True, widget=forms.PasswordInput(render_value=False), label='Confirm Password')
  user_role = forms.ChoiceField(required=True, choices = models.USER_ROLE_CHOICES)
  work_place = forms.ModelChoiceField(required=False,
                                  queryset=models.WorkPlace.objects.all().filter(status='A').order_by('name'),
                                  #widget=autocomplete.ModelSelect2(url='workplace-autocomplete',
                                                                  # attrs={'data-placeholder': 'Start typing the name if your work place ...',}),
                                  )
  new_work_place_flag = forms.BooleanField(required=False, label='My work place is not listed')

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')

    super(SignUpForm, self).__init__(*args, **kwargs)
    if user.is_authenticated and hasattr(user, 'administrator'):
      self.fields.pop('confirm_email')
    else:
      self.fields['user_role'].choices = models.USER_ROLE_CHOICES[1:3]

    for field_name, field in list(self.fields.items()):
      if field_name not in ['new_work_place_flag']:
        field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'

      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

  def clean_username(self):
    return self.cleaned_data['username'].strip()

  def clean_email(self):
    return self.cleaned_data['email'].strip()

  def clean_confirm_email(self):
    return self.cleaned_data['confirm_email'].strip()

  def clean(self):
    cleaned_data = super(RegistrationForm, self).clean()
    username = cleaned_data.get('username')
    first_name = cleaned_data.get('first_name')
    last_name = cleaned_data.get('last_name')
    password1 = cleaned_data.get('password1')
    password2 = cleaned_data.get('password2')
    email = cleaned_data.get('email')
    confirm_email = cleaned_data.get('confirm_email')
    user_role = cleaned_data.get('user_role')
    work_place = cleaned_data.get('work_place')
    new_work_place_flag = cleaned_data.get('new_work_place_flag')

    if username is None:
      self.fields['username'].widget.attrs['class'] += ' error'
    elif User.objects.filter(username=username.lower()).count() > 0:
      self.add_error('username', 'This username is already taken. Please choose another.')
      self.fields['username'].widget.attrs['class'] += ' error'

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
    if email is None:
      self.fields['email'].widget.attrs['class'] += ' error'
    elif User.objects.filter(email=email).count() > 0:
      self.add_error('email', 'This email is already taken. Please choose another.')
      self.fields['email'].widget.attrs['class'] += ' error'
    elif 'confirm_email' in self.fields and email != confirm_email:
      self.add_error('confirm_email', 'Emails do not match.')
      self.fields['email'].widget.attrs['class'] += ' error'
      self.fields['confirm_email'].widget.attrs['class'] += ' error'
    #check fields for Teacher, Student and School Administrator
    if work_place is None and new_work_place_flag == 'F':
      self.fields['work_place'].widget.attrs['class'] += ' error'
      self.add_error('work_place', 'Work Place is required.')


####################################
# User Form
####################################
class UserForm(ModelForm):
  password1 = forms.CharField(widget=forms.PasswordInput, required=False, label='Password', help_text="Leave this field blank to retain old password")
  password2 = forms.CharField(widget=forms.PasswordInput, required=False, label='Confirm Password')

  class Meta:
    model = models.User
    fields = ["username","first_name", "last_name", "email", "password1", "password2", "is_active"]

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    super(UserForm, self).__init__(*args, **kwargs)
    for field_name, field in list(self.fields.items()):
      if field_name not in ['is_active']:
        field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

  def clean_username(self):
    return self.cleaned_data['username'].strip()

  def clean_email(self):
    return self.cleaned_data['email'].strip()

  def save(self, commit=True):
    if self.cleaned_data['password1'] is not None and self.cleaned_data['password1'] != "":
      user = super(UserForm, self).save(commit=True)
      user.set_password(self.cleaned_data['password1'])
      user.save()
      return user
    else:
      user = super(UserForm, self).save(commit=True)
      user.save()
      return user

  def is_valid(self, user_id):
    valid = super(UserForm, self).is_valid()
    if not valid:
      return valid

    cleaned_data = super(UserForm, self).clean()
    username = cleaned_data.get('username')
    first_name = cleaned_data.get('first_name')
    last_name = cleaned_data.get('last_name')
    password1 = cleaned_data.get('password1')
    password2 = cleaned_data.get('password2')
    email = cleaned_data.get('email')

    if username is None or username == '':
      self.add_error('username', 'Username is required')
      valid = False
    elif User.objects.filter(username=username.lower()).exclude(id=user_id).count() > 0:
      self.add_error('username', 'This username is already taken. Please choose another.')
      valid = False

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
    elif User.objects.filter(email=email).exclude(id=user_id).count() > 0:
      self.add_error('email', 'This email is already taken. Please choose another.')
      valid = False

    return valid


####################################
# UserProfile Form
####################################
class UserProfileForm (ModelForm):

  class Meta:
    model = models.UserProfile
    fields = ['work_place', 'user_role', 'image', 'validation_code']
    widgets = {
      #'work_place': autocomplete.ModelSelect2(url='school-autocomplete', attrs={'data-placeholder': 'Start typing the school name ...',})
    }

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')

    super(UserProfileForm, self).__init__(*args, **kwargs)

    if user.is_authenticated:
      if user.userProfile.user_role == 'A':
        self.fields['validation_code'].widget.attrs['readonly'] = True
      else:
        self.fields['user_role'].widget.attrs['readonly'] = True
        self.fields.pop('validation_code')

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


class ReservationForm(ModelForm):
  equipment_types = forms.ModelMultipleChoiceField(required=False,
                                  queryset=models.EquipmentType.objects.all().filter(status='A').order_by('name'))
 
  class Meta:
    model = models.Reservation
    exclude = ('equipment', 'created_by', 'created_date', 'modified_date')
    widgets = {
      'equipment_type': forms.SelectMultiple(attrs={'size':5}),
      #'other_activity': forms.CheckboxInput(),
    }

  def __init__(self, *args, **kwargs):
    super(ReservationForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name not in ['other_activity', 'need_equipment', 'additional_help', 'need_activity_kit']:
        if field_name in ['delivery_date', 'return_date']:
          field.widget.attrs['class'] = 'form-control datepicker'
        else:
          field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

    if self.instance.id:
      initial = []
      for equipment in self.instance.equipment.all():
        initial.append(equipment.equipment_type.id)
      self.fields['equipment_types'].initial = initial


class WorkshopForm(ModelForm):

  class Meta:
    model = models.Workshop
    exclude = ('created_date', 'modified_date')


  def __init__(self, *args, **kwargs):
    super(WorkshopForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name not in ['enable_registration']:
        if field_name in ['start_date', 'end_date']:
          field.widget.attrs['class'] = 'form-control datepicker'
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


  def __init__(self, *args, **kwargs):
    super(WorkshopRegistrationSettingForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name not in ['enable_waitlist']:
        if field_name in ['open_date', 'close_date']:
          field.widget.attrs['class'] = 'form-control datepicker'
        else:
          field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

class WorkshopRegistrationForm(ModelForm):

  class Meta:
    model = models.Registration
    exclude = ('created_date', 'modified_date')


  def __init__(self, *args, **kwargs):

    super(WorkshopRegistrationForm, self).__init__(*args, **kwargs)

    #print(self.instance.workshop_registration_setting)
    if not self.instance.id:
      registered_users = models.Registration.objects.all().filter(workshop_registration_setting=self.instance.workshop_registration_setting).values_list('user', flat=True)
      self.fields['user'].queryset = models.UserProfile.objects.all().exclude(id__in=registered_users)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


####################################
# Workshop Category Form
####################################
class WorkshopCategoryForm(ModelForm):

  class Meta:
    model = models.WorkshopCategory
    exclude = ('created_date', 'modified_date')

  def __init__(self, *args, **kwargs):
    super(WorkshopCategoryForm, self).__init__(*args, **kwargs)
    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Work Place Form
####################################
class WorkPlaceForm(ModelForm):

  class Meta:
    model = models.WorkPlace
    exclude = ('id', 'status', 'created_date', 'modified_date')

  def __init__(self, *args, **kwargs):
    super(WorkPlaceForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text


