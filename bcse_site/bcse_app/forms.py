from django import forms
from django.forms import ModelForm
from bcse_app import models, widgets, utils
from django.forms.widgets import TextInput
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout
from django.db.models.functions import Lower
from localflavor.us.models import USStateField
from django.contrib.admin.widgets import FilteredSelectMultiple
from dal import autocomplete
import datetime
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

####################################
# Login Form
####################################
class SignInForm (forms.Form):
  email = forms.CharField(required=True, max_length=75, label='Email',
                              error_messages={'required': 'Email is required'})
  password = forms.CharField(required=True, widget=forms.PasswordInput(render_value=False), label='Password',
                              error_messages={'required': 'Password is required'})

  def __init__(self, *args, **kwargs):
    super(SignInForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text


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
      if User.objects.filter(email=email.lower()).count() == 0:
        self.add_error('email', 'Email is incorrect.')
        self.fields['email'].widget.attrs['class'] += ' error'
      elif password is not None:
        user = authenticate(username=email.lower(), password=password)
        if user is None:
          self.add_error('password', 'Password is incorrect.')
          self.fields['password'].widget.attrs['class'] += ' error'

####################################
# Registration Form
####################################
class SignUpForm (forms.Form):
  email = forms.EmailField(required=True, max_length=75, label='Email')
  confirm_email = forms.EmailField(required=True, max_length=75, label='Confirm Email')
  first_name = forms.CharField(required=True, max_length=30, label='First Name')
  last_name = forms.CharField(required=True, max_length=30, label='Last Name')
  password1 = forms.CharField(required=True, widget=forms.PasswordInput(render_value=False), label='Password')
  password2 = forms.CharField(required=True, widget=forms.PasswordInput(render_value=False), label='Confirm Password')
  user_role = forms.ChoiceField(required=True, choices=(('', '---------'),)+models.USER_ROLE_CHOICES, label='I am a')
  work_place = forms.ModelChoiceField(required=False, label=u"Workplace",
                                  queryset=models.WorkPlace.objects.all(),
                                  widget=autocomplete.ModelSelect2(url='workplace-autocomplete',
                                                                  attrs={'data-placeholder': 'Start typing the name if your workplace ...', 'dropdownParent': '#signup_workplace_select'}),
                                  )
  phone_number = forms.CharField(required=False, max_length=20, label='Phone Number')
  iein = forms.CharField(required=False, max_length=20, label='IEIN #')
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
      field.widget.attrs['placeholder'] = field.help_text

  def clean_email(self):
    return self.cleaned_data['email'].strip()

  def clean_confirm_email(self):
    return self.cleaned_data['confirm_email'].strip()

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

    if email is None:
      self.fields['email'].widget.attrs['class'] += ' error'
    elif User.objects.filter(email=email.lower()).count() > 0:
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
    elif User.objects.filter(email=email.lower()).exclude(id=user_id).count() > 0:
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
    fields = ['work_place', 'user_role', 'image', 'phone_number', 'iein', 'grades_taught', 'twitter_handle', 'instagram_handle', 'subscribe', 'photo_release_complete', 'dietary_preference']
    widgets = {
      'image': widgets.ClearableFileInput,
      'work_place': autocomplete.ModelSelect2(url='workplace-autocomplete',
                                              attrs={'data-placeholder': 'Start typing the name if your workplace ...', 'dropdownparent': '#profile_workplace_select'}),
    }

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
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

      self.fields['work_place'].required = False

    for field_name, field in list(self.fields.items()):
      if field_name not in ['new_work_place_flag', 'subscribe', 'photo_release_complete']:
        field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

  def clean(self):
    user = self.user
    cleaned_data = super(UserProfileForm, self).clean()
    work_place = cleaned_data.get('work_place')
    new_work_place_flag = cleaned_data.get('new_work_place_flag')

    #check fields for Teacher, Student and School Administrator
    if user.is_authenticated:
      if user.userProfile.user_role not in ['A', 'S']:
        if work_place is None and not new_work_place_flag:
          self.fields['work_place'].widget.attrs['class'] += ' error'
          self.add_error('work_place', 'Workplace is required.')



####################################
# Subscription Form
####################################
class SubscriptionForm (forms.Form):
  email = forms.EmailField(required=True, max_length=75, label='Email')
  first_name = forms.CharField(required=True, max_length=30, label='First Name')
  last_name = forms.CharField(required=True, max_length=30, label='Last Name')
  phone_number = forms.CharField(required=False, max_length=20, label='Phone Number')
  captcha = ReCaptchaField()

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
      'inventory': forms.Textarea(attrs={'rows':2}),
      'notes': forms.Textarea(attrs={'rows':2}),
    }

  def __init__(self, *args, **kwargs):
    super(ActivityForm, self).__init__(*args, **kwargs)
    self.fields['materials_equipment'].label = 'Materials/Equipment'
    self.fields['manuals_resources'].label = 'Instruction Manuals/Resources'
    self.fields['inventory'].label = 'Kit Inventory'
    self.fields['notes'].label = 'Inventory Notes'
    self.fields['color'].queryset = models.ReservationColor.objects.all().filter(target__in=['K', 'B'])
    self.fields['color'].label = 'Inventory Color'

    for field_name, field in list(self.fields.items()):
      if field_name == 'tags':
        field.widget.attrs['class'] = 'form-control select2'
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
    fields = ['inventory', 'kit_unit_cost', 'notes', 'color']
    widgets = {
      'inventory': forms.Textarea(attrs={'rows':1}),
      'notes': forms.Textarea(attrs={'rows':1}),
    }

  def __init__(self, *args, **kwargs):
    super(ActivityUpdateForm, self).__init__(*args, **kwargs)
    self.fields['inventory'].label = 'Kit Inventory'
    self.fields['notes'].label = 'Inventory Notes'
    self.fields['color'].queryset = models.ReservationColor.objects.all().filter(target__in=['K', 'B'])
    self.fields['color'].label = 'Inventory Color'


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
      'inventory': forms.Textarea(attrs={'rows':2}),
      'notes': forms.Textarea(attrs={'rows':2}),
    }

  def __init__(self, *args, **kwargs):
    super(ConsumableForm, self).__init__(*args, **kwargs)
    self.fields['inventory'].label = 'Inventory'
    self.fields['notes'].label = 'Notes'
    self.fields['color'].queryset = models.ReservationColor.objects.all().filter(target__in=['K', 'B'])
    self.fields['color'].label = 'Color'

    for field_name, field in list(self.fields.items()):
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
    fields = ['inventory', 'unit_cost', 'notes', 'color']
    widgets = {
      'inventory': forms.Textarea(attrs={'rows':1}),
      'notes': forms.Textarea(attrs={'rows':1}),
    }

  def __init__(self, *args, **kwargs):
    super(ConsumableUpdateForm, self).__init__(*args, **kwargs)
    self.fields['inventory'].label = 'Inventory'
    self.fields['notes'].label = 'Notes'
    self.fields['color'].queryset = models.ReservationColor.objects.all().filter(target__in=['K', 'B'])
    self.fields['color'].label = 'Color'


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
# Equipment Type Form
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
    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

####################################
# Equipment Availability Search Form
####################################
class EquipmentAvailabilityForm (forms.Form):

  equipment_types = forms.ModelMultipleChoiceField(required=False, queryset=models.EquipmentType.objects.all().filter(status='A').order_by('name'), widget=forms.SelectMultiple(attrs={'size':6}), help_text='On Windows use Ctrl+Click to make multiple selection. On a Mac use Cmd+Click to make multiple selection')
  selected_month = forms.DateField(required=True, initial=datetime.date.today, label=u'Month/Year', widget=forms.widgets.DateInput(format="%B %Y"))

  def __init__(self, *args, **kwargs):
    super(EquipmentAvailabilityForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

      if field_name == 'selected_month':
        field.widget.attrs['class'] = 'form-control datepicker availability'


class ReservationForm(ModelForm):
  equipment_types = forms.MultipleChoiceField(required=False,
                                  choices=[(equip.id, equip.name) for equip in models.EquipmentType.objects.all().filter(status='A', equipment__status='A').distinct().order_by('order')], widget=forms.CheckboxSelectMultiple())
  confirm_workplace = forms.ChoiceField(required=True, choices=[('', '---------'), ('Y', 'Yes'),('N', 'No, update my workplace'),],)

  class Meta:
    model = models.Reservation
    exclude = ('equipment', 'email_sent', 'confirmation_email_dates', 'feedback_status', 'feedback_email_count', 'feedback_email_date', 'created_by', 'created_date', 'modified_date')
    widgets = {
      'user': autocomplete.ModelSelect2(url='user-autocomplete', attrs={'data-placeholder': 'Start typing the name of the user ...',}),
      'notes': forms.Textarea(attrs={'rows':3}),
      'admin_notes': forms.Textarea(attrs={'rows':3}),
      #'other_activity': forms.CheckboxInput(),
    }

  class Media:
    css = {'all': ('/static/path/to/widgets.css',),}
    js = ('/jsi18n',)

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    super(ReservationForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name not in ['other_activity', 'equipment_not_needed', 'additional_help_needed', 'activity_kit_not_needed', 'include_gloves_goggles']:
        if field_name in ['delivery_date', 'return_date']:
          if field_name == 'delivery_date':
            field.widget.attrs['class'] = 'form-control datepicker reservation_delivery_date reservation_date'
            field.widget.attrs['title'] = 'Click here to open a calender popup to select delivery date'
          else:
            field.widget.attrs['class'] = 'form-control datepicker reservation_return_date reservation_date'
            field.widget.attrs['title'] = 'Click here to open a calender popup to select return date'
          field.widget.attrs['readonly'] = True
        else:
          field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-check-input'

      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

    self.fields['equipment_types'].choices = [(equip.id, equip.name) for equip in models.EquipmentType.objects.all().filter(status='A', equipment__status='A').distinct().order_by('order')]
    if self.instance.id:
      initial = []
      for equipment in self.instance.equipment.all():
        initial.append(equipment.equipment_type.id)
      self.fields['equipment_types'].initial = initial
      self.fields['user'].widget.attrs['disabled'] = True
      if self.instance.activity:
        self.fields['activity'].queryset = models.Activity.objects.all().filter(status='A') | models.Activity.objects.all().filter(id=self.instance.activity.id)
      else:
        self.fields['activity'].queryset = models.Activity.objects.all().filter(status='A')

      self.fields.pop('confirm_workplace')

    else:
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
    self.fields['include_gloves_goggles'].label = 'I would like to borrow gloves and goggles.'
    self.fields['equipment_not_needed'].label = 'I already have all the equipment I need.'
    self.fields['notes'].label = 'Please provide any additional information that would be useful, such as your preferred pick-up and return times, and any directions for parking and entering your school.'
    self.fields['assignee'].label = 'Select the BCSE team member in-charge of this reservation.'
    self.fields['additional_help_needed'].label = 'I need additional help.'

    if user.user_role not in ['A', 'S']:
      self.fields.pop('assignee')
      self.fields.pop('more_num_of_classes')
      self.fields.pop('admin_notes')
      self.fields.pop('color')
      self.fields.pop('consumables')
    else:
      self.fields['assignee'].queryset = models.UserProfile.objects.all().filter(user_role__in=['A', 'S']).order_by('user__last_name', 'user__first_name')
      self.fields['activity'].queryset = models.Activity.objects.all()
      self.fields['color'].queryset = models.ReservationColor.objects.all().filter(target__in=['R', 'B'])
      self.fields['consumables'].queryset = models.Consumable.objects.all().filter(status='A')

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
    fields = ['color', 'status']

  def __init__(self, *args, **kwargs):
    super(ReservationUpdateForm, self).__init__(*args, **kwargs)

    self.fields['color'].queryset = models.ReservationColor.objects.all().filter(target__in=['R', 'B'])

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

  def __init__(self, *args, **kwargs):

    super(BaxterBoxBlackoutDateForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control datepicker'
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
    fields = ['name', 'color', 'description', 'low_stock', 'low_stock_message', 'rank', 'target']
    widgets = {
        'color': TextInput(attrs={'type': 'color'}),
        'low_stock_message': forms.Textarea(attrs={'rows':2}),
    }

  def __init__(self, *args, **kwargs):

    super(ReservationColorForm, self).__init__(*args, **kwargs)

    self.fields['target'].label = 'Applicable Entity(s)'
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
    }

  def __init__(self, *args, **kwargs):
    super(WorkshopForm, self).__init__(*args, **kwargs)

    self.fields['workshop_category'].queryset = models.WorkshopCategory.objects.all().filter(status='A').order_by('name')
    self.fields['credits'].label = 'ISBE PD Credits'

    for field_name, field in list(self.fields.items()):
      if field_name not in ['enable_registration', 'featured']:
        if field_name in ['start_date', 'end_date']:
          field.widget.attrs['class'] = 'form-control datepicker'
        elif field_name in ['start_time', 'end_time']:
          field.widget.attrs['class'] = 'form-control timepicker'
        elif field_name in ['teacher_leaders', 'tags']:
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


  def __init__(self, *args, **kwargs):
    super(WorkshopRegistrationSettingForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      if field_name not in ['enable_waitlist']:
        if field_name in ['open_date', 'close_date']:
          field.widget.attrs['class'] = 'form-control datepicker'
        elif field_name in ['open_time', 'close_time']:
          field.widget.attrs['class'] = 'form-control timepicker'
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
      self.fields['work_place'].initial = self.instance.registration_to_work_place.work_place

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
    fields = ['dietary_preference']

  def __init__(self, *args, **kwargs):

    super(WorkshopRegistrationQuestionnaireForm, self).__init__(*args, **kwargs)

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['aria-describedby'] = field.label
      field.widget.attrs['placeholder'] = field.help_text

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


      if initials:
        if field_name in initials:
          field.initial = initials[field_name]

####################################
# Workplace Form
####################################
class WorkPlaceForm(ModelForm):

  class Meta:
    model = models.WorkPlace
    exclude = ('id', 'term_id', 'created_date', 'modified_date', 'latitude', 'longitude', 'time_from_base', 'distance_from_base')

  def __init__(self, *args, **kwargs):
    super(WorkPlaceForm, self).__init__(*args, **kwargs)

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


####################################
# Teacher Leader Form
####################################
class TeacherLeaderForm(ModelForm):

  class Meta:
    model = models.TeacherLeader
    exclude = ('created_date', 'modified_date')
    widgets = {
      'image': widgets.ClearableFileInput,
      'teacher': autocomplete.ModelSelect2(url='teacher-leader-autocomplete', attrs={'data-placeholder': 'Start typing the name of the teacher ...',})

    }

  def __init__(self, *args, **kwargs):
    super(TeacherLeaderForm, self).__init__(*args, **kwargs)
    for field_name, field in list(self.fields.items()):
      if field_name in ['highlight']:
        field.widget.attrs['class'] = 'form-check-input'
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
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text


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
      else:
        field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text

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

####################################
# SurveySubmission Form
####################################
class SurveySubmissionForm(ModelForm):
  work_place = forms.ModelChoiceField(required=False, label=u'Workplace', queryset=models.WorkPlace.objects.all().filter(status='A').order_by('name'),
                                                      widget=autocomplete.ModelSelect2(url='workplace-autocomplete',
                                                                                       attrs={'data-placeholder': 'Start typing the name of the workplace ...'}),
                                                      help_text="Updating the workplace here only updates the survey submission - workplace association and not the workplace on the user profile")
  class Meta:
    model = models.SurveySubmission
    fields = ['status', 'admin_notes']
    widgets = {
      'admin_notes': forms.Textarea(attrs={'rows':3}),
    }

  def __init__(self, *args, **kwargs):
    super(SurveySubmissionForm, self).__init__(*args, **kwargs)

    if self.instance.UUID and hasattr(self.instance, 'survey_submission_to_work_place'):
      self.fields['work_place'].initial = self.instance.survey_submission_to_work_place.work_place

    for field_name, field in list(self.fields.items()):
      field.widget.attrs['class'] = 'form-control'
      field.widget.attrs['placeholder'] = field.help_text


####################################
# Survey Submissions Search Form
####################################
class SurveySubmissionsSearchForm(forms.Form):
  email = forms.CharField(required=False, max_length=256, label=u'Email')
  first_name = forms.CharField(required=False, max_length=256, label=u'First Name')
  last_name = forms.CharField(required=False, max_length=256, label=u'Last Name')
  user_role = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.USER_ROLE_CHOICES)
  work_place = forms.ModelChoiceField(required=False, label=u'Workplace', queryset=models.WorkPlace.objects.all().filter(status='A').order_by('name'),
                                                      widget=autocomplete.ModelSelect2(url='workplace-autocomplete',
                                                                                       attrs={'data-placeholder': 'Start typing the name if your workplace ...'}))

  status = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.SURVEY_SUBMISSION_STATUS_CHOICES)
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
  work_place = forms.ModelChoiceField(required=False, label=u"Requesting user's Workplace", queryset=models.WorkPlace.objects.all(), widget=autocomplete.ModelSelect2(url='workplace-autocomplete', attrs={'data-placeholder': 'Start typing the name of the workplace ...'}),
                                  )
  assignee = forms.ModelChoiceField(required=False, label=u'Assigned To', queryset=models.UserProfile.objects.all().filter(user_role__in=['A', 'S']).order_by('user__last_name', 'user__first_name'))

  activity = forms.ModelChoiceField(required=False, queryset=models.Activity.objects.all().order_by('name'))
  consumable = forms.ModelMultipleChoiceField(required=False, queryset=models.Consumable.objects.all().order_by('name'), widget=forms.SelectMultiple(attrs={'size':6}))
  equipment = forms.ModelMultipleChoiceField(required=False, queryset=models.EquipmentType.objects.all().order_by('order'), widget=forms.SelectMultiple(attrs={'size':6}))
  delivery_after = forms.DateField(required=False, label=u'Delivery on/after')
  return_before = forms.DateField(required=False, label=u'Return on/before')
  feedback_status = forms.ChoiceField(required=False, choices=(('', '---------'),)+models.RESERVATION_FEEDBACK_STATUS_CHOICES)
  status = forms.MultipleChoiceField(required=False, choices=models.RESERVATION_STATUS_CHOICES, initial=['O', 'R', 'U'], widget=forms.SelectMultiple(attrs={'size':6}))
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
                                                       ('status', 'Status')))
  columns = forms.MultipleChoiceField(required=False, choices=models.RESERVATION_TABLE_COLUMN_CHOICES, initial=['CR', 'UR', 'KT', 'CO', 'EQ', 'CC', 'DA', 'DD', 'RD', 'AN', 'HP', 'ST', 'GG'],  widget=forms.SelectMultiple(attrs={'size':6}), label=u'Display Columns')
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)
  color = forms.ModelMultipleChoiceField(required=False, label=u'Color', queryset=models.ReservationColor.objects.all().filter(target__in=['R', 'B']).order_by('name'))


  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(ReservationsSearchForm, self).__init__(*args, **kwargs)

    if user.is_anonymous or user.userProfile.user_role not in 'AS':
      self.fields.pop('user')
      self.fields.pop('work_place')
      self.fields.pop('assignee')
      self.fields.pop('color')
      self.fields.pop('feedback_status')
      self.fields.pop('consumable')
    else:
      self.fields['rows_per_page'].initial = 75

    for field_name, field in self.fields.items():
      if field_name in ['delivery_after', 'return_before']:
        field.widget.attrs['class'] = 'form-control datepicker'
      elif field_name in ['equipment', 'consumable']:
        field.widget.attrs['class'] = 'form-control select2'
      else:
        field.widget.attrs['class'] = 'form-control'

      if field.help_text:
        field.widget.attrs['placeholder'] = field.help_text

      if field_name in ['equipment', 'status', 'columns', 'color']:
        field.help_text = 'On Windows use Ctrl+Click to make multiple selection. On a Mac use Cmd+Click to make multiple selection'
      if field_name == 'sort_by':
        field.help_text = 'The default sort is (Delivery Date followed by Return date) in descending order for Unconfirmed/Confirmed/Checked In/Cancelled reservations and (Return Date) in descending order for Checked Out reservations.'


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
      elif 'tag' in field_name:
        field.widget.attrs['class'] = 'form-control select2'
        field.widget.attrs['aria-describedby'] = field.label
      else:
        field.widget.attrs['class'] = 'form-control'

      if field.help_text:
        field.widget.attrs['placeholder'] = field.help_text

      if initials:
        if field_name in initials:
          field.initial = initials[field_name]



####################################
# Registrants Search Form
####################################
class WorkshopsRegistrantsSearchForm(forms.Form):

  workshop_category = forms.ModelMultipleChoiceField(required=False, queryset=models.WorkshopCategory.objects.all().order_by(Lower('name')), widget=forms.SelectMultiple(attrs={'size':6}))
  workshop = forms.ModelMultipleChoiceField(required=False, queryset=models.Workshop.objects.all().order_by(Lower('name'), 'start_date').distinct(), widget=forms.SelectMultiple(attrs={'size':6}))
  #user = forms.ModelChoiceField(required=False, label=u'Registrant', queryset=models.UserProfile.objects.all().order_by('user__first_name', 'user__last_name'), widget=autocomplete.ModelSelect2(url='user-autocomplete', attrs={'data-placeholder': 'Start typing the name of the user ...',}))
  user = forms.ModelMultipleChoiceField(required=False, label=u'Registrant', queryset=models.UserProfile.objects.all().order_by('user__first_name', 'user__last_name'), widget=forms.SelectMultiple(attrs={'size':6}))

  #work_place = forms.ModelChoiceField(required=False, label=u"Registrant's Workplace", queryset=models.WorkPlace.objects.all(), widget=autocomplete.ModelSelect2(url='workplace-autocomplete', attrs={'data-placeholder': 'Start typing the name of the workplace ...'}),)
  work_place = forms.ModelMultipleChoiceField(required=False, label=u"Registrant's Workplace", queryset=models.WorkPlace.objects.all(), widget=forms.SelectMultiple(attrs={'size':6}))
  #year = forms.ChoiceField(required=False, choices=models.YEAR_CHOICES)
  starts_after = forms.DateField(required=False, label=u'Starts on/after')
  ends_before = forms.DateField(required=False, label=u'Ends on/before')

  status = forms.MultipleChoiceField(required=False, label=u"Registration Status", choices=models.WORKSHOP_REGISTRATION_STATUS_CHOICES, widget=forms.SelectMultiple(attrs={'size':6}))
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
      elif field_name in ['workshop_category', 'workshop', 'status', 'user', 'work_place'] or 'tag' in field_name:
        field.widget.attrs['class'] = 'form-control select2'
      else:
        field.widget.attrs['class'] = 'form-control'

      field.widget.attrs['placeholder'] = field.help_text

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
  work_place = forms.ModelChoiceField(required=False, label=u"Workplace", queryset=models.WorkPlace.objects.all().filter(status='A').order_by('name'),
                                                      widget=autocomplete.ModelSelect2(url='workplace-autocomplete',
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
  work_place = forms.ModelChoiceField(required=False, label=u"Requesting user's Workplace", queryset=models.WorkPlace.objects.all(), widget=autocomplete.ModelSelect2(url='workplace-autocomplete', attrs={'data-placeholder': 'Start typing the name of the workplace ...'}),)
  user = forms.ModelChoiceField(required=False, label=u'Requesting User', queryset=models.UserProfile.objects.all().order_by('user__first_name', 'user__last_name'), widget=autocomplete.ModelSelect2(url='user-autocomplete', attrs={'data-placeholder': 'Start typing the name of the user ...',}))
  activity = forms.ModelMultipleChoiceField(required=False, queryset=models.Activity.objects.all().order_by('name'), widget=forms.SelectMultiple(attrs={'size':7}))
  equipment = forms.ModelMultipleChoiceField(required=False, queryset=models.EquipmentType.objects.all().order_by('order'), widget=forms.SelectMultiple(attrs={'size':7}))
  consumable = forms.ModelMultipleChoiceField(required=False, queryset=models.Consumable.objects.all().order_by('name'), widget=forms.SelectMultiple(attrs={'size':5}))
  status = forms.MultipleChoiceField(required=False, choices=models.RESERVATION_STATUS_CHOICES, widget=forms.SelectMultiple(attrs={'size':5}))
  rows_per_page = forms.ChoiceField(required=True, choices=models.TABLE_ROWS_PER_PAGE_CHOICES, initial=25)

  def __init__(self, *args, **kwargs):
    user = kwargs.pop('user')
    initials = kwargs.pop('initials')
    super(BaxterBoxUsageSearchForm, self).__init__(*args, **kwargs)

    for field_name, field in self.fields.items():
      if field_name in ['from_date', 'to_date']:
        field.widget.attrs['class'] = 'form-control datepicker'
      elif field_name in ['activity', 'equipment', 'consumable', 'status']:
        field.widget.attrs['class'] = 'form-control'
      else:
        field.widget.attrs['class'] = 'form-control'

      if field_name in ['activity', 'equipment', 'consumable', 'status']:
        field.help_text = 'On Windows use Ctrl+Click to make multiple selection. On a Mac use Cmd+Click to make multiple selection'

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
  work_place = forms.ModelChoiceField(required=False, label=u'Workplace', queryset=models.WorkPlace.objects.all().filter(status='A').order_by('name'),
                                                      widget=autocomplete.ModelSelect2(url='workplace-autocomplete',
                                                                                       attrs={'data-placeholder': 'Start typing the name if your workplace ...'}))
  registration_status = forms.MultipleChoiceField(required=False, choices=models.WORKSHOP_REGISTRATION_STATUS_CHOICES, widget=forms.SelectMultiple(attrs={'size':6}), help_text='On Windows use Ctrl+Click to make multiple selection. On a Mac use Cmd+Click to make multiple selection')
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

