from django.db import models
from django.contrib.auth.models import User
import io
import datetime
import pytz
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
from django.core.mail import EmailMessage
from django.db.models import Func
from PIL import Image
import os
from localflavor.us.models import USStateField
from django.utils.timezone import make_aware
from icalendar import Calendar, Event, vCalAddress, vText

# Create your models here.

CONTENT_STATUS_CHOICES = (
    ('A', 'Active'),
    ('I', 'Inactive'),
)

USER_ROLE_CHOICES = (
    ('A', 'BCSE Admin'),
    ('T', 'K-12 Teacher or Administrator'),
    ('P', 'Other Professional'),
    ('S', 'BCSE Staff'),
)

WORKPLACE_CHOICES = (
  ('S', 'School'),
  ('C', 'Company'),
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
  ('D', 'Denied'),
  ('N', 'Cancelled'),
  ('W', 'Waitlisted'),
  ('P', 'Pending'),
)

RESERVATION_STATUS_CHOICES = (
  ('D', 'Cancelled'),
  ('I', 'Checked In'),
  ('O', 'Checked Out'),
  ('R', 'Confirmed'),
  ('U', 'Unconfirmed'),
)

GRADES_CHOICES = (
  ('E', 'Elementary School'),
  ('M', 'Middle School'),
  ('H', 'High School'),
  ('O', 'Other'),
)

NUM_OF_CLASS_CHOICES = (
  ('1', '1'),
  ('2', '2'),
  ('3', '3'),
  ('4', '4'),
  ('5', 'More than 4'),
)

def upload_file_to(instance, filename):
  import os
  now = datetime.datetime.now()
  dt = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
  filename_base, filename_ext = os.path.splitext(filename)
  file_path = 'misc'

  if isinstance(instance, EquipmentType):
    file_path = 'equipmentType'
  elif isinstance(instance, WorkshopCategory):
    file_path = 'workshopCategory'
  elif isinstance(instance, Workshop):
    file_path = 'workshop'
  elif isinstance(instance, UserProfile):
    file_path = 'user'
  elif isinstance(instance, Activity):
    file_path = 'activity'
  elif isinstance(instance, TeacherLeader):
    file_path = 'teacherLeader'
  elif isinstance(instance, Team):
    file_path = 'team'

  return '%s/%s_%s%s' % (file_path, instance.id, dt, filename_ext.lower(),)


class WorkPlace(models.Model):
  name = models.CharField(null=False, blank=False, max_length=256, help_text='Name of Work Place')
  work_place_type = models.CharField(max_length=1, choices=WORKPLACE_CHOICES)
  district_number = models.CharField(null=True, blank=True, max_length=256, help_text='District Number for School')
  street_address_1 = models.CharField(null=False, blank=False, max_length=256, help_text='Street Address 1')
  street_address_2 = models.CharField(null=True, blank=True, max_length=256, help_text='Street Address 2')
  city = models.CharField(null=False, blank=False, max_length=256, help_text='City')
  state = USStateField(null=False, blank=False, help_text='State')
  zip_code = models.CharField(null=False, blank=False, max_length=256, help_text='Zip Code of Work Place')
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['name']

  def __str__(self):
      return '%s' % (self.name)

class UserProfile(models.Model):
  user = models.OneToOneField(User, unique=True, null=False, related_name="userProfile", on_delete=models.CASCADE)
  work_place = models.ForeignKey(WorkPlace, null=True, related_name="users", on_delete=models.SET_NULL)
  user_role = models.CharField(max_length=1, choices=USER_ROLE_CHOICES)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Profile image')
  validation_code = models.CharField(null=False, max_length=5)
  phone_number = models.CharField(null=True, blank=True, max_length=20)
  iein = models.CharField(null=True, blank=True, max_length=20)
  grades_taught = models.CharField(null=True, blank=True, max_length=1, choices=GRADES_CHOICES)
  twitter_handle = models.CharField(null=True, blank=True, max_length=20)
  instagram_handle = models.CharField(null=True, blank=True, max_length=20)
  subscribe =  models.BooleanField(default=False)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['user__last_name', 'user__first_name']

  def __str__(self):
      return '%s, %s' % (self.user.last_name, self.user.first_name)

class EquipmentType(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of Equipment Type')
  short_name = models.CharField(null=True, blank=True, max_length=256, help_text='Short name for displaying on the calendar')
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
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['name']

  def __str__(self):
      return '%s' % (self.name)

class Workshop (models.Model):
  workshop_category = models.ForeignKey(WorkshopCategory, null=False, related_name="workshop", on_delete=models.CASCADE)
  teacher_leader = models.ForeignKey('TeacherLeader', null=True, blank=True, on_delete=models.SET_NULL)
  name = models.CharField(null=False, max_length=256, help_text='Name of Workshop')
  sub_title = models.CharField(null=True, blank=True, max_length=256)
  summary = RichTextField(null=True, blank=True)
  description = RichTextField(null=True, blank=True)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image that represents this Workshop')
  start_date = models.DateField(null=True, blank=True, help_text='Workshop start date')
  start_time = models.TimeField(null=True, blank=True, help_text='Workshop start time')
  end_date = models.DateField(null=True, blank=True, help_text='Workshop end date')
  end_time = models.TimeField(null=True, blank=True, help_text='Workshop end time')
  location = models.CharField(null=False, max_length=256, help_text='Workshop location')
  enable_registration =  models.BooleanField(default=False)
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['-id']

  def __str__(self):
      return '%s - %s' % (self.workshop_category, self.name)


class TeacherLeader(models.Model):
  first_name = models.CharField(null=False, max_length=256, help_text='First name of the teacher')
  last_name = models.CharField(null=False, max_length=256, help_text='Last name of the teacher')
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image of the teacher leader')
  school = models.ForeignKey(WorkPlace, null=True, on_delete=models.SET_NULL)
  bio = RichTextField(null=True, blank=True)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['-id']

  def __str__(self):
      return '%s %s' % (self.first_name, self.last_name)


class WorkshopRegistrationSetting(models.Model):
  workshop = models.OneToOneField(Workshop, null=False, related_name="registration_setting", on_delete=models.CASCADE)
  registration_type = models.CharField(null=True, blank=True, max_length=1, choices=WORKSHOP_REGISTRATION_TYPE_CHOICES)
  survey_url = models.URLField(null=True, blank=True)
  capacity = models.IntegerField(null=True, blank=True, help_text='Maximum capacity for this workshop. Leave blank for unlimited capacity')
  enable_waitlist = models.BooleanField(default=False)
  waitlist_capacity = models.IntegerField(null=True, blank=True, help_text='Capacity for the waitlist. Leave blank for unlimited waitlist capacity')  
  open_date = models.DateField(null=True, blank=True, help_text="The date registration is open. Leave blank if registration is always open")
  open_time = models.TimeField(null=True, blank=True)
  close_date = models.DateField(null=True, blank=True, help_text="The date registration is closed. Leave blank if registration is always open")
  close_time = models.TimeField(null=True, blank=True)
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
      unique_together = ('workshop_registration_setting', 'user')

  def __str__(self):
      return '%s - Registration' % (self.workshop_registration_setting.workshop.name)

class RegistrationEmailMessage(models.Model):
  registration_status = models.CharField(null=False, blank=False, max_length=1, unique=True, choices=WORKSHOP_REGISTRATION_STATUS_CHOICES)
  email_subject = models.CharField(null=False, max_length=256)
  email_message = RichTextField(null=False, blank=False)
  include_calendar_invite = models.BooleanField(default=False)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['registration_status']

class Activity(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of the Activity')
  description = RichTextField(null=True, blank=True)
  status = models.CharField(default='A',  max_length=1, choices=CONTENT_STATUS_CHOICES)
  workshop = models.ManyToManyField(Workshop, null=True, blank=True, help_text='On Windows use Ctrl+Click to make multiple selection.  On a Mac use Cmd+Click to make multiple selection')
  kit_name = models.CharField(null=False, max_length=256, help_text='Name of the Consumable Kit')
  equipment = models.ManyToManyField(EquipmentType, null=True, blank=True, help_text='On Windows use Ctrl+Click to make multiple selection.  On a Mac use Cmd+Click to make multiple selection')
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image that represents this Consumable Kit')
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['name']

  def __str__(self):
      return '%s' % (self.name)

class Reservation(models.Model):
  user = models.ForeignKey(UserProfile, related_name='user_reservations', on_delete=models.CASCADE)
  activity = models.ForeignKey(Activity, null=True, blank=True, on_delete=models.CASCADE)
  num_of_classes = models.CharField(null=True, blank=True, max_length=1, choices=NUM_OF_CLASS_CHOICES)
  activity_kit_not_needed = models.BooleanField(default=False)
  other_activity = models.BooleanField(default=False)
  other_activity_name = models.CharField(null=True, blank=True, max_length=256, help_text='Name of the other activity')
  num_of_students = models.IntegerField(null=False, blank=False)
  equipment_not_needed = models.BooleanField(default=False)
  equipment = models.ManyToManyField(Equipment, null=True, blank=True)
  delivery_date = models.DateField(null=False, help_text="The date the equipment/kit will be delivered/picked up")
  return_date = models.DateField(null=True, blank=True, help_text="The date the equipment will be returned")
  notes = models.CharField(null=True, blank=True, max_length=256, help_text='Any additional information')
  additional_help_needed = models.BooleanField(default=False)
  status = models.CharField(default='R', max_length=1, choices=RESERVATION_STATUS_CHOICES)
  created_by = models.ForeignKey(UserProfile, default=1, on_delete=models.SET_DEFAULT)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)


  class Meta:
      ordering = ['delivery_date']

  def __str__(self):
    if self.activity:
      return '%s - %s' % (self.activity.name, self.user)
    else:
      return '%s - %s' % (self.other_activity_name, self.user)



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


# signal to check if registration status has changed
# and then send an email to the registrant
@receiver(pre_save, sender=Registration)
def check_registration_status_change(sender, instance, **kwargs):
  try:
    confirmation_message_object = RegistrationEmailMessage.objects.get(registration_status=instance.status)
    userProfile = instance.user
    workshop = Workshop.objects.get(id=instance.workshop_registration_setting.workshop.id)
    registration_setting = workshop.registration_setting

    subject = replace_workshop_tokens(confirmation_message_object.email_subject, workshop)
    body = replace_workshop_tokens(confirmation_message_object.email_message, workshop)
    email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, [userProfile.user.email])

    #check if calendar invite needs to be attached
    if confirmation_message_object.include_calendar_invite:
      filename = create_calendar_invite(workshop, userProfile)
      email.attach_file(filename, 'text/calendar')

    email.content_subtype = "html"
    email.send()
  except RegistrationEmailMessage.DoesNotExist as e:
    pass

#
# Replace workshop registration message tokens before sending out an email
#
def replace_workshop_tokens(text, workshop):
  replaced_text = text
  replaced_text = replaced_text.replace('[workshop_category]', workshop.workshop_category.name or '')
  replaced_text = replaced_text.replace('[workshop_title]', workshop.name or '')
  replaced_text = replaced_text.replace('[workshop_sub_title]', workshop.sub_title or '')
  replaced_text = replaced_text.replace('[workshop_start_date]', workshop.start_date.strftime('%B %-d, %Y') or '')
  replaced_text = replaced_text.replace('[workshop_start_time]', workshop.start_time.strftime('%-I:%M %p') or '')
  replaced_text = replaced_text.replace('[workshop_end_date]', workshop.end_date.strftime('%B %-d, %Y') or '')
  replaced_text = replaced_text.replace('[workshop_end_time]', workshop.end_time.strftime('%-I:%M %p'))
  replaced_text = replaced_text.replace('[workshop_summary]', workshop.summary or '')
  replaced_text = replaced_text.replace('[workshop_location]', workshop.location or '')
  replaced_text = replaced_text.replace('[workshop_survey_url]', workshop.registration_setting.survey_url or '')
  return replaced_text

#
# Create calendar invite (ics) file for the workshop
#
def create_calendar_invite(workshop, userProfile):
  cal = Calendar()
  event = Event()

  event.add('summary', workshop.name)
  event.add('dtstart', datetime.datetime.combine(workshop.start_date, workshop.start_time))
  event.add('dtend', datetime.datetime.combine(workshop.end_date, workshop.end_time))
  event.add('dtstamp', datetime.datetime.now())
  event['location'] = vText(workshop.location)
  cal.add_component(event)
  filename = '/tmp/invite_%s_%s.ics' % (workshop.id, userProfile.id)

  with open(filename, 'wb') as f:
    f.write(cal.to_ical())
    f.close()
  return filename

