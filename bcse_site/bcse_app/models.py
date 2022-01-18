from django.db import models
from django.contrib.auth.models import User
import io
import datetime
import string
from ckeditor_uploader.fields import RichTextUploadingField
from ckeditor.fields import RichTextField
from django.utils.crypto import get_random_string
from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.models import signals
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, m2m_changed, pre_delete
from django.db.models.functions import Upper
from django.conf import settings
from django.core.mail import send_mail
from django.db.models import Func
from PIL import Image
import os
from localflavor.us.models import USStateField

# Create your models here.

CONTENT_STATUS_CHOICES = (
    ('A', 'Active'),
    ('I', 'Inactive'),
)

USER_ROLE_CHOICES = (
    ('A', 'Admin'),
    ('T', 'Teacher'),
    ('O', 'Other Professional'),
    ('S', 'Staff'),
)

WORKPLACE_CHOICES = (
  ('S', 'School'),
  ('C', 'Company'),
)

HUB_CHOICES = (
  ('N', 'North'),
  ('C', 'Chicago'),
)

WORKSHOP_TYPE_CHOICES = (
  ('I', 'In-Person'),
  ('V', 'Virtual'),
  ('H', 'Hybrid')
)

WORKSHOP_REGISTRATION_TYPE_CHOICES = (
  ('R', 'Register'),
  ('A', 'Apply'),
)

WORKSHOP_REGISTRATION_STATUS_CHOICES = (
  ('R', 'Registered'),
  ('A', 'Applied'),
  ('C', 'Accepted'),
  ('N', 'Cancelled'),
  ('W', 'Waitlisted'),
  ('P', 'Pending'),
)

RESERVATION_STATUS_CHOICES = (
  ('U', 'Unconfirmed'),
  ('C', 'Confirmed'),
  ('O', 'Checked Out'),
  ('I', 'Checked In'),
  ('N', 'Cancelled'),
)

def upload_file_to(instance, filename):
  import os
  now = datetime.datetime.now()
  dt = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
  filename_base, filename_ext = os.path.splitext(filename)
  file_path = 'misc'

  if isinstance(instance, EquipmentType):
    file_path = 'equipmentType'
  elif isinstance(instance, WorkshopType):
    file_path = 'workshopType'
  elif isinstance(instance, Workshop):
    file_path = 'workshop'
  elif isinstance(instance, UserProfile):
    file_path = 'user'
  elif isinstance(instance, ActivityKit):
    file_path = 'activityKit'

  return '%s/%s_%s%s' % (file_path, instance.id, dt, filename_ext.lower(),)


class WorkPlace(models.Model):
  name = models.CharField(null=False, blank=True, max_length=256, help_text='Name of Work Place')
  work_place_type = models.CharField(max_length=1, choices=WORKPLACE_CHOICES)
  district_number = models.CharField(null=True, blank=True, max_length=256, help_text='District Number for School')
  hub = models.CharField(null=True, blank=True, max_length=1, choices=HUB_CHOICES, help_text='Hub for School')
  street_address_1 = models.CharField(null=True, blank=True, max_length=256, help_text='Street Address 1')
  street_address_2 = models.CharField(null=True, blank=True, max_length=256, help_text='Street Address 2')
  city = models.CharField(null=True, blank=True, max_length=256, help_text='City')
  state = USStateField(null=True, blank=True, help_text='State')
  zip_code = models.CharField(null=False, blank=True, max_length=256, help_text='Zip Code of Work Place')
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['name']

  def __str__(self):
      return '%s' % (self.name)

class UserProfile(models.Model):
  user = models.OneToOneField(User, unique=True, null=False, on_delete=models.CASCADE)
  work_place = models.ForeignKey(WorkPlace, null=True, related_name="users", on_delete=models.SET_NULL)
  user_role = models.CharField(max_length=1, choices=USER_ROLE_CHOICES)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Profile image')
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['user__last_name', 'user__first_name']

  def __str__(self):
      return '%s, %s' % (self.user.last_name, self.user.first_name)

class EquipmentType(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of Equipment Type')
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image at least 400x289 in resolution that represents this equipment type')
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['name']

  def __str__(self):
      return '%s' % (self.name)

class Equipment (models.Model):
  equipment_type = models.ForeignKey(EquipmentType, null=False, related_name="equipment", on_delete=models.CASCADE)
  name = models.CharField(null=False, max_length=256, help_text='Name of Equipment')
  hub = models.CharField(null=False, max_length=1, choices=HUB_CHOICES, help_text='Hub for Equipment')
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['-id']

  def __str__(self):
      return '%s - %s' % (self.equipment_type, self.name)


class WorkshopCategory(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of Workshop Category')
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image that represents this Workshop Category')
  description = RichTextField(null=True, blank=True)
  workshop_type = models.CharField(null=False, max_length=1, choices=WORKSHOP_TYPE_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['name']

  def __str__(self):
      return '%s' % (self.name)

class Workshop (models.Model):
  workshop_category = models.ForeignKey(WorkshopCategory, null=False, related_name="workshop", on_delete=models.CASCADE)
  name = models.CharField(null=False, max_length=256, help_text='Name of Workshop')
  description = RichTextField(null=True, blank=True)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image that represents this Workshop')
  start_date = models.DateField(null=True, blank=True, help_text='Workshop start date')
  end_date = models.DateField(null=True, blank=True, help_text='Workshop end date')
  location = models.CharField(null=False, max_length=256, help_text='Workshop location')
  enable_registration =  models.BooleanField(default=False)
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['-id']

  def __str__(self):
      return '%s - %s' % (self.workshop_category, self.name)


class WorkshopRegistrationSetting(models.Model):
  workshop = models.OneToOneField(Workshop, null=False, related_name="registration", on_delete=models.CASCADE)
  registration_type = models.CharField(null=True, blank=True, max_length=1, choices=WORKSHOP_REGISTRATION_TYPE_CHOICES)
  capacity = models.IntegerField(null=True, blank=True, help_text='Maximum capacity for this workshop. Leave blank for unlimited capacity')
  enable_waitlist = models.BooleanField(default=False)
  waitlist_capacity = models.IntegerField(null=True, blank=True, help_text='Capacity for the waitlist. Leave blank for unlimited waitlist capacity')  
  open_date = models.DateTimeField(null=True, blank=True, help_text="The date registration is open. Leave blank if registration is always open")
  close_date = models.DateTimeField(null=True, blank=True, help_text="The date registration is closed. Leave blank if registration is always open")
  registrants = models.ManyToManyField(UserProfile, through='Registration', null=True, blank=True)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['-id']

  def __str__(self):
      return '%s' % (self.workshop.name)

class Registration(models.Model):
  workshop_registration_setting = models.ForeignKey(WorkshopRegistrationSetting, verbose_name='Workshop', related_name='workshop_registrants', on_delete=models.CASCADE)
  user = models.ForeignKey(UserProfile, related_name='registered_workshops', on_delete=models.CASCADE)
  status = models.CharField(default='R', max_length=1, choices=WORKSHOP_REGISTRATION_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['-id']

  def __str__(self):
      return '%s - Registration' % (self.workshop_registration_setting.workshop.name)

class ActivityKit(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of the Consumable Kit')
  description = RichTextField(null=True, blank=True)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image that represents this Consumable Kit')
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['name']

  def __str__(self):
      return '%s' % (self.name)


class Activity(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of the Activity')
  description = RichTextField(null=True, blank=True)
  status = models.CharField(default='A',  max_length=1, choices=CONTENT_STATUS_CHOICES)
  workshop = models.ManyToManyField(Workshop, null=True, blank=True, help_text='On Windows use Ctrl+Click to make multiple selection.  On a Mac use Cmd+Click to make multiple selection')
  kit = models.OneToOneField(ActivityKit, null=False, blank=False, on_delete=models.CASCADE, help_text='Kit required for this activity')
  equipment = models.ManyToManyField(EquipmentType, null=True, blank=True, help_text='On Windows use Ctrl+Click to make multiple selection.  On a Mac use Cmd+Click to make multiple selection')
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['name']

  def __str__(self):
      return '%s' % (self.name)

class Reservation(models.Model):
  user = models.ForeignKey(UserProfile, related_name='user_reservations', on_delete=models.CASCADE)
  activity = models.ForeignKey(Activity, null=True, on_delete=models.CASCADE)
  other_activity = models.BooleanField(default=False)
  other_activity_name = models.CharField(null=True, blank=True, max_length=256, help_text='Name of the other activity')
  need_activity_kit = models.BooleanField(default=True)
  num_of_classes = models.IntegerField(null=False, blank=False)
  num_of_students = models.IntegerField(null=False, blank=False)
  additional_help = models.BooleanField(default=False)
  need_equipment = models.BooleanField(default=True)
  equipment = models.ManyToManyField(Equipment, null=True, blank=True)
  delivery_date = models.DateField(null=False, help_text="The date the equipment/kit will be delivered/picked up")
  return_date = models.DateField(null=True, blank=True, help_text="The date the equipment will be returned")
  notes = models.CharField(null=True, blank=True, max_length=256, help_text='Any additional information')
  status = models.CharField(default='C', max_length=1, choices=RESERVATION_STATUS_CHOICES)
  created_by = models.ForeignKey(UserProfile, default=1, on_delete=models.SET_DEFAULT)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)


  class Meta:
      ordering = ['delivery_date']

  def __str__(self):
      return '%s - %s' % (self.activity.name, self.user)



class Team(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of the Team Member')
  description = RichTextField(null=True, blank=True)
  email = models.EmailField(null=False, max_length=256)
  position = models.CharField(null=False, max_length=256, help_text='Position of the Team Member')
  organization = models.CharField(null=False, max_length=256, help_text='Org. of the Team Member')
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image of this team member')
  order = models.IntegerField(null=False, blank=False)

  class Meta:
      ordering = ['order']

  def __str__(self):
      return '%s' % (self.name)

