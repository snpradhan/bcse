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
from django.db.models import signals, Q, F
from django.dispatch import receiver
from django.db.models.signals import pre_save, post_save, m2m_changed, pre_delete, post_delete
from django.db.models.functions import Upper
from django.conf import settings
from django.core.mail import EmailMessage
from django.db.models import Func
from PIL import Image
import os
from localflavor.us.models import USStateField
from django.utils.timezone import make_aware
from icalendar import Calendar, Event, vCalAddress, vText
from django.template.loader import render_to_string, get_template
from django.contrib.sites.models import Site
import uuid
import requests
from requests.structures import CaseInsensitiveDict
import urllib.parse
from django.core.validators import MaxValueValidator, MinValueValidator, FileExtensionValidator

# Create your models here.

CONTENT_STATUS_CHOICES = (
    ('A', 'Active'),
    ('I', 'Inactive'),
)

SURVEY_SUBMISSION_STATUS_CHOICES  = (
    ('I', 'In Progress'),
    ('S', 'Submitted'),
    ('R', 'Reviewed'),
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
  ('E', 'External'),
)

WORKSHOP_REGISTRATION_STATUS_CHOICES = (
  ('R', 'Registered'),
  ('A', 'Applied'),
  ('C', 'Accepted'),
  ('D', 'Denied'),
  ('N', 'Cancelled'),
  ('W', 'Waitlisted'),
  ('P', 'Pending'),
  ('T', 'Attended'),
)

RESERVATION_STATUS_CHOICES = (
  ('U', 'Unconfirmed'),
  ('R', 'Confirmed'),
  ('O', 'Checked Out'),
  ('I', 'Completed'),
  ('N', 'Cancelled'),
)

RESERVATION_FEEDBACK_STATUS_CHOICES = (
  ('E', 'Email Sent'),
  ('I', 'Feedback In Progress'),
  ('S', 'Feedback Submitted'),
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

SURVEY_TYPE_CHOICES = (
  ('A', 'Async Learning'),
  ('C', 'Case Study'),
  ('W', 'Workshop Application/Questionnaire'),
  ('B', 'Baxter Box Feedback'),
  ('O', 'Other'),
)

SURVEY_COMPONENT_TYPE_CHOICES = (
  ('IN', 'Info'),
  ('DD', 'Drop Down'),
  ('MC', 'Multiple Choice'),
  ('MS', 'Multi-Select'),
  ('TF', 'Textfield'),
  ('TA', 'Textarea'),
  ('FI', 'File Upload'),
  ('DT', 'Date'),
  ('EM', 'Email'),
  ('UL', 'URL'),
)

RESERVATION_TABLE_COLUMN_CHOICES = (
  ('ID', 'ID'),
  ('CR', 'Created Date'),
  ('UR', 'User'),
  ('EM', 'User Email'),
  ('AC', 'Activity'),
  ('KT', 'Kit'),
  ('CO', 'Consumables'),
  ('NC', 'Classes'),
  ('NS', 'Students'),
  ('GL', 'Include Gloves'),
  ('GO', 'Include Goggles'),
  ('IV', 'Inventory'),
  ('IN', 'Inventory Notes'),
  ('EQ', 'Equipment'),
  ('CC', 'Comment Count'),
  ('DD', 'Delivery Date'),
  ('RD', 'Return Date'),
  ('UN', 'Pickup/Return Notes'),
  ('HP', 'Help Needed'),
  ('DA', 'Delivery Address'),
  ('WN', 'Workplace Notes'),
  ('DI', 'Delivery Distance'),
  ('DT', 'Delivery Time'),
  ('AN', 'Admin Notes'),
  ('AT', 'Delivery Assigned To'),
  ('PA', 'Pickup Assigned To'),
  ('ST', 'Reservation Status'),
  ('ES', 'Confirmation Email Sent'),
  ('FS', 'Feedback Status'),
)

USER_TABLE_COLUMN_CHOICES = (
  ('ID', 'User ID'),
  ('FN', 'Full Name'),
  ('NP', 'Name Pronounciation'),
  ('EM', 'Email'),
  ('RL', 'Role'),
  ('WP', 'Workplace'),
  ('JD', 'Joined Date'),
  ('LL', 'Last Login'),
  ('PN', 'Phone Number'),
  ('IE', 'IEIN'),
  ('GT', 'Grades Taught'),
  ('IH', 'Instagram Handle'),
  ('TH', 'Twitter Handle'),
  ('SC', 'Subscribed'),
  ('PC', 'Photo Release Complete'),
  ('DP', 'Dietary Preference'),
  ('AN', 'Admin Notes'),
  ('ST', 'Status'),
  ('LU', 'Last Updated'),

)

WORKPLACE_TABLE_COLUMN_CHOICES = (
  ('ID', 'ID'),
  ('NM', 'Name'),
  ('WT', 'Workplace Type'),
  ('DN', 'District #'),
  ('S1', 'Street Address 1'),
  ('S2', 'Street Address 2'),
  ('CT', 'City'),
  ('SA', 'State'),
  ('ZP', 'Zip Code'),
  ('LT', 'Latitude'),
  ('LO', 'Longitude'),
  ('TM', 'Travel Time'),
  ('DT', 'Distance'),
  ('NU', '# of Users'),
  ('AR', '# of Reservations'),
  ('AW', '# of Workshop Registrations'),
  ('AN', 'Admin Notes'),
  ('ST', 'Status'),
  ('CD', 'Created Date'),
  ('MD', 'Modified Date'),
)

SURVEY_SUBMISSION_TABLE_COLUMN_CHOICES = (
  ('SN', 'Serial #'),
  ('SI', 'Response ID'),
  ('IP', 'IP Address'),
  ('UI', 'User ID'),
  ('FN', 'Full Name'),
  ('EM', 'Email'),
  ('WP', 'Workplace'),
  ('CE', 'Connected Entity'),
  ('AN', 'Admin Notes'),
  ('ST', 'Status'),
  ('CD', 'Created Date'),
)

COLOR_TARGET_CHOICES = (
  ('R', 'Reservation'),
  ('K', 'Activity and Consumable'),
  ('B', 'Reservation, Activity and Consumable'),
)

BAXTER_BOX_MESSAGE_TYPE_CHOICES = (
  ('B', 'Blackout Message'),
  ('D', 'Date Rule'),
)

EMAIL_STATUS_CHOICES = (
  ('D', 'Draft'),
  ('S', 'Sent'),
)

BCSE_FACILITATOR_ROLE_CHOICES = (
  ('T', 'Teacher Leader'),
  ('F', 'Other Facilitator'),
)


TABLE_ROWS_PER_PAGE_CHOICES = (
  (25, '25'),
  (50, '50'),
  (75, '75'),
  (100, '100'),
  (0, 'All')
)

YES_NO_CHOICES = (
  (False, 'No'),
  (True, 'Yes'),
)

INVENTORY_STORAGE_LOCATION = (
  ('RO', 'Room Temp'),
  ('RE', 'Refrigerator'),
  ('FR', 'Freezer')
)

YEAR_CHOICES = [('', '---------')]
for x in range(2008, datetime.datetime.now().year + 5):
  YEAR_CHOICES.append((x, x))

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
  elif isinstance(instance, Consumable):
    file_path = 'consumable'
  elif isinstance(instance, TeacherLeader):
    file_path = 'teacherLeader'
  elif isinstance(instance, Team):
    file_path = 'team'
  elif isinstance(instance, Partner):
    file_path = 'partner'
  elif isinstance(instance, HomepageBlock):
    file_path = 'homepage'
  elif isinstance(instance, Collaborator):
    file_path = 'collaborator'
  elif isinstance(instance, SurveyResponse):
    file_path = 'surveyResponse'
  elif isinstance(instance, Vignette):
    if(filename_ext.lower() == 'pdf'):
      file_path = 'vignette/attachment'
    else:
      file_path = 'vignette/image'

  return '%s/%s_%s%s' % (file_path, instance.id, dt, filename_ext.lower(),)


class WorkPlace(models.Model):
  name = models.CharField(null=False, blank=False, max_length=256, help_text='Name of Workplace')
  work_place_type = models.CharField(max_length=1, choices=WORKPLACE_CHOICES)
  district_number = models.CharField(null=True, blank=True, max_length=256, help_text='District Number for School')
  street_address_1 = models.CharField(null=False, blank=False, max_length=256, help_text='Street Address 1')
  street_address_2 = models.CharField(null=True, blank=True, max_length=256, help_text='Street Address 2')
  city = models.CharField(null=False, blank=False, max_length=256, help_text='City')
  state = USStateField(null=False, blank=False, help_text='State')
  zip_code = models.CharField(null=False, blank=False, max_length=256, help_text='Zip Code of Workplace')
  latitude = models.CharField(null=True, blank=True, max_length=256)
  longitude = models.CharField(null=True, blank=True, max_length=256)
  time_from_base = models.CharField(null=True, blank=True, max_length=256)
  distance_from_base = models.CharField(null=True, blank=True, max_length=256)
  term_id = models.IntegerField(null=True, blank=True)#delete this field after import
  admin_notes = models.CharField(null=True, blank=True, max_length=2048, help_text='Notes only admins can add/view')
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['name']

  def __str__(self):
      return '%s' % (self.name)

  def get_full_address(self):
    return '%s <br> %s %s, %s, %s' % (self.street_address_1, self.street_address_2 + '<br>' if self.street_address_2 else '', self.city, self.state, self.zip_code)

#
# Placeholder workplace to assign to users when the users' workplace is deleted
#
def get_placeholder_workplace():
  return WorkPlace.objects.all().filter(name='Placeholder workplace')[0].id



class UserProfile(models.Model):
  user = models.OneToOneField(User, unique=True, null=False, related_name="userProfile", on_delete=models.CASCADE)
  secondary_email = models.EmailField(null=True, blank=True, max_length=256, help_text="Secondary email can be used to Sign In.  Any email sent to the primary email will also be sent to the secondary email.")
  work_place = models.ForeignKey(WorkPlace, null=False, blank=False, related_name="users", default=get_placeholder_workplace, on_delete=models.SET(get_placeholder_workplace))
  user_role = models.CharField(max_length=1, choices=USER_ROLE_CHOICES)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Profile image')
  validation_code = models.CharField(null=False, max_length=5)
  phone_number = models.CharField(null=True, blank=True, max_length=20)
  iein = models.CharField(null=True, blank=True, max_length=20)
  grades_taught = models.CharField(null=True, blank=True, max_length=1, choices=GRADES_CHOICES)
  twitter_handle = models.CharField(null=True, blank=True, max_length=20)
  instagram_handle = models.CharField(null=True, blank=True, max_length=20)
  subscribe =  models.BooleanField(default=False)
  photo_release_complete = models.BooleanField(default=False)
  dietary_preference = models.CharField(null=True, blank=True, max_length=256)
  admin_notes = models.CharField(null=True, blank=True, max_length=2048, help_text='Notes only admins can add/view')
  name_pronounciation = models.CharField(null=True, blank=True, max_length=256)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['user__last_name', 'user__first_name']

  def __str__(self):
      return '%s, %s (%s)' % (self.user.last_name, self.user.first_name, self.user.email)

  @property
  def initials(self):
    first = self.user.first_name[:1] if self.user.first_name else ''
    last = self.user.last_name[:1] if self.user.last_name else ''
    return '%s.%s.' % (first.upper(), last.upper())

class EquipmentType(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of Equipment Category')
  short_name = models.CharField(null=True, blank=True, max_length=256, help_text='Short name for displaying on the calendar')
  description = RichTextField(null=True, blank=True)
  unit_cost = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.0)], help_text='Unit cost for the equipment')
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image at least 400x289 in resolution that represents this equipment category')
  tags = models.ManyToManyField('SubTag', null=True, blank=True, help_text='On Windows use Ctrl+Click to make multiple selection.  On a Mac use Cmd+Click to make multiple selection')
  order = models.IntegerField(null=False, blank=False)
  featured =  models.BooleanField(default=True, help_text='If marked "Featured", this equipment will be displayed on "The Baxter Box Program" page')
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['order']

  def __str__(self):
      return '%s' % (self.name)

class Equipment (models.Model):
  equipment_type = models.ForeignKey(EquipmentType, null=False, related_name="equipment", on_delete=models.CASCADE)
  name = models.CharField(null=False, max_length=256, help_text='Name of Equipment')
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['equipment_type__order', 'name']

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
  collaborators = models.ManyToManyField('Collaborator', null=True, blank=True, related_name="workshops")
  teacher_leaders = models.ManyToManyField('TeacherLeader', null=True, blank=True, related_name="workshops")
  name = models.CharField(null=False, max_length=256, help_text='Name of Workshop')
  sub_title = models.CharField(null=True, blank=True, max_length=256)
  summary = RichTextField(null=True, blank=True)
  description = RichTextField(null=True, blank=True)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image that represents this Workshop')
  start_date = models.DateField(null=False, blank=False, help_text='Workshop start date')
  start_time = models.TimeField(null=True, blank=True, help_text='Workshop start time')
  end_date = models.DateField(null=False, blank=False, help_text='Workshop end date')
  end_time = models.TimeField(null=True, blank=True, help_text='Workshop end time')
  display_date = models.TextField(null=True, blank=True, help_text='For multi-day workshop, enter start and end times for each day')
  location = models.CharField(null=False, max_length=256, help_text='Workshop location')
  perks = models.CharField(null=True, blank=True, max_length=512, help_text='Workshop perks')
  credits = models.CharField(null=True, blank=True, max_length=512, help_text='Credits the attendees earn')
  enable_registration =  models.BooleanField(default=False)
  featured =  models.BooleanField(default=False, help_text='If marked "Featured", this workshop will be displayed under "Past Workshop Examples" tab')
  cancelled =  models.BooleanField(default=False, help_text='If marked "Cancelled", registration will be closed and any pre-existing registration data will not be included in the registration report')
  meetup_link = models.URLField(null=True, blank=True, max_length=500)
  nid = models.IntegerField(null=True, blank=True)#delete this field after import
  tags = models.ManyToManyField('SubTag', null=True, blank=True, help_text='On Windows use Ctrl+Click to make multiple selection.  On a Mac use Cmd+Click to make multiple selection')
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['-id']

  def __str__(self):
    if self.cancelled:
      return 'Cancelled: %s' % self.name
    else:
      return self.name


class TeacherLeader(models.Model):
  teacher = models.ForeignKey(UserProfile, null=False, blank=False, on_delete=models.CASCADE)
  bio = RichTextField(null=True, blank=True)
  highlight = models.BooleanField(default=False)
  bcse_role = models.CharField(default='T', max_length=1, choices=BCSE_FACILITATOR_ROLE_CHOICES)
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['teacher__user__last_name', 'teacher__user__first_name']

  def __str__(self):
      return '%s %s' % (self.teacher.user.first_name, self.teacher.user.last_name)


class WorkshopRegistrationSetting(models.Model):
  workshop = models.OneToOneField(Workshop, null=False, related_name="registration_setting", on_delete=models.CASCADE)
  registration_type = models.CharField(null=True, blank=True, max_length=1, choices=WORKSHOP_REGISTRATION_TYPE_CHOICES)
  application = models.ForeignKey('Survey', null=True, blank=True, related_name="registration_setting", on_delete=models.SET_NULL, help_text='If selected, users must complete the chosen application or questionnaire before their registration is recorded.')
  capacity = models.IntegerField(null=True, blank=True, help_text='Maximum capacity for this workshop. Leave blank for unlimited capacity')
  enable_waitlist = models.BooleanField(default=True)
  waitlist_capacity = models.IntegerField(null=True, blank=True, help_text='Capacity for the waitlist. Leave blank for unlimited waitlist capacity')
  open_date = models.DateField(null=True, blank=True, help_text="The date registration is open. Leave blank if registration is always open")
  open_time = models.TimeField(null=True, blank=True)
  close_date = models.DateField(null=True, blank=True, help_text="The date registration is closed. Leave blank if registration is always open")
  close_time = models.TimeField(null=True, blank=True)
  registrants = models.ManyToManyField(UserProfile, through='Registration', null=True, blank=True)
  isbe_link = models.URLField(null=True, blank=True)
  external_registration_link = models.URLField(null=True, blank=True, max_length=2048)
  external_link_label = models.CharField(null=True, blank=True, max_length=256)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['-id']

  def __str__(self):
      return '%s' % (self.workshop.name)

  def capacity_reached(self):
    if self.registration_type == 'R' and self.capacity:
      registrants = self.workshop_registrants.all().filter(status='R')
      if registrants.count() >= self.capacity:
        return True

    return False

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


#################################################################
# Workplace associated with creating the registration record
#############################################################
class RegistrationWorkPlace(models.Model):
  registration = models.OneToOneField(Registration, on_delete=models.CASCADE, related_name='registration_to_work_place')
  work_place = models.ForeignKey(WorkPlace, on_delete=models.SET(get_placeholder_workplace), related_name='work_place_to_registration')


class WorkshopApplication(models.Model):
  registration = models.ForeignKey(Registration, on_delete=models.CASCADE, related_name='registration_to_application')
  application = models.ForeignKey('SurveySubmission', on_delete=models.CASCADE, related_name='application_to_registration')

  class Meta:
      ordering = ['-id']
      unique_together = ('registration', 'application')

class RegistrationEmailMessage(models.Model):
  registration_status = models.CharField(null=False, blank=False, max_length=1, unique=True, choices=WORKSHOP_REGISTRATION_STATUS_CHOICES)
  email_subject = models.CharField(null=False, max_length=256)
  email_message = RichTextField(null=False, blank=False)
  include_calendar_invite = models.BooleanField(default=False)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['registration_status']

class WorkshopRegistrationEmail(models.Model):
  workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name="workshop_registration_email")
  registration_status = models.CharField(null=False, blank=False, max_length=1, choices=WORKSHOP_REGISTRATION_STATUS_CHOICES)
  email_subject = models.CharField(null=False, max_length=256)
  email_message = RichTextField(null=False, blank=False)
  include_calendar_invite = models.BooleanField(default=False)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['registration_status']
      unique_together = ('workshop', 'registration_status')

class WorkshopEmail(models.Model):
  workshop = models.ForeignKey(Workshop, on_delete=models.CASCADE, related_name="workshop_email")
  registration_status = models.CharField(null=True, blank=True, max_length=50, help_text='One or more registration statuses this email is sent to. Email will be bcc''d to these addresses.')
  photo_release_incomplete = models.BooleanField(default=False, help_text='If checked, this email will be sent to users with incomplete photo release within the selected registration status.')
  registration_email_addresses = models.TextField(null=True, blank=True)
  email_to = models.CharField(null=True, blank=True, max_length=1024, help_text='One or more email addresses separated by a semicolon.')
  email_cc = models.CharField(null=True, blank=True, max_length=1024, help_text='One or more email addresses separated by a semicolon.')
  email_bcc = models.CharField(null=True, blank=True, max_length=1024, help_text='One or more email addresses separated by a semicolon.')
  email_subject = models.CharField(null=False, max_length=256)
  email_message = RichTextField(null=False, blank=False)
  email_status = models.CharField(null=False, blank=False, max_length=1, choices=EMAIL_STATUS_CHOICES, default='D')
  scheduled_date = models.DateField(null=True, blank=True, help_text="The date the email is scheduled to be sent.")
  scheduled_time = models.TimeField(null=True, blank=True, help_text='The time the email is scheduled to be sent. If date is set but time is not set, the email will be scheduled for midnight.')
  sent_date = models.DateTimeField(null=True, blank=True)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)


  class Meta:
      ordering = ['modified_date']

  def get_email_status(self):
    if self.sent_date:
      return 'Sent'
    elif self.scheduled_date:
      return 'Scheduled'
    else:
      return 'Draft'

  def get_registration_status(self):
    return self.registration_status.split(',') if self.registration_status else []

  def get_registration_status_display(self):
    if self.registration_status:
      return '<br>'.join([value for key, value in WORKSHOP_REGISTRATION_STATUS_CHOICES if key in self.registration_status.split(',')])
    else:
      return ""

  def set_registration_status(self, status_list):
    self.registration_status = ','.join(status_list)



class Activity(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of the Activity')
  description = RichTextField(null=True, blank=True, help_text='Describe the activity')
  materials_equipment = RichTextField(null=True, blank=True, help_text='Enter a list of materials the Baxter Center provides, equipment the users can borrow and materials the user has to arrange themselves')
  manuals_resources = RichTextField(null=True, blank=True, config_name='resource_url_ckeditor', help_text='Enter a list of urls for instruction manuals and resoruces')
  kit_name = models.CharField(null=False, max_length=256, help_text='Name of the Activity Kit')
  kit_unit_cost = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.0)], help_text='Unit cost for the kit')
  inventory = RichTextField(null=True, blank=True, config_name='simple_ckeditor', help_text='Activity Kit inventory')
  notes = RichTextField(null=True, blank=True, config_name='simple_ckeditor', help_text='Inventory notes')
  consumables = models.ManyToManyField('Consumable', null=True, blank=True, help_text='On Windows use Ctrl+Click to make multiple selection.  On a Mac use Cmd+Click to make multiple selection')
  equipment_mapping = models.ManyToManyField(EquipmentType, null=True, blank=True, help_text='On Windows use Ctrl+Click to make multiple selection.  On a Mac use Cmd+Click to make multiple selection')
  tags = models.ManyToManyField('SubTag', null=True, blank=True, help_text='On Windows use Ctrl+Click to make multiple selection.  On a Mac use Cmd+Click to make multiple selection')
  color = models.ForeignKey('ReservationColor', null=True, blank=True, on_delete=models.SET_NULL)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image that represents this Activity Kit')
  status = models.CharField(default='A',  max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['name']

  def __str__(self):
      return '%s' % (self.name)

class ActivityInventory(models.Model):
  activity = models.ForeignKey(Activity, null=False, blank=False, on_delete=models.CASCADE)
  count = models.IntegerField(null=False, blank=False, validators=[MinValueValidator(0)])
  expiration_date = models.DateField(null=True, blank=True)
  storage_location = models.CharField(null=False, max_length=2, choices=INVENTORY_STORAGE_LOCATION)
  notes = models.CharField(null=True, blank=True, max_length=2048, help_text='Any additional information')
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['activity__name', 'storage_location', 'expiration_date']


class Consumable(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of the Consumable')
  inventory = RichTextField(null=True, blank=True, config_name='simple_ckeditor', help_text='Consumable Kit inventory')
  unit_cost = models.FloatField(null=True, blank=True, validators=[MinValueValidator(0.0)], help_text='Unit cost for the consumable')
  notes = RichTextField(null=True, blank=True, config_name='simple_ckeditor', help_text='Inventory notes')
  color = models.ForeignKey('ReservationColor', null=True, blank=True, on_delete=models.SET_NULL)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image that represents this Consumable')
  status = models.CharField(default='A',  max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['name']

  def __str__(self):
      return '%s' % (self.name)

class ConsumableInventory(models.Model):
  consumable = models.ForeignKey(Consumable, null=False, blank=False, on_delete=models.CASCADE)
  count = models.IntegerField(null=False, blank=False, validators=[MinValueValidator(0)])
  expiration_date = models.DateField(null=True, blank=True)
  storage_location = models.CharField(null=False, max_length=2, choices=INVENTORY_STORAGE_LOCATION)
  notes = models.CharField(null=True, blank=True, max_length=2048, help_text='Any additional information')
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['consumable__name', 'storage_location', 'expiration_date']

class Tag(models.Model):
  name = models.CharField(null=False, max_length=256, unique=True, help_text='Name of the Tag')
  order = models.IntegerField(null=False, blank=False)
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['order']

  def __str__(self):
      return '%s' % (self.name)

class SubTag(models.Model):
  tag = models.ForeignKey(Tag, related_name='sub_tags', null=False, on_delete=models.CASCADE)
  name = models.CharField(null=False, max_length=256, help_text='Name of Sub Tag')
  order = models.IntegerField(null=False, blank=False)
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['tag__order', 'order']
      unique_together = ('tag', 'name')

  def __str__(self):
      return '%s - %s' % (self.tag.name, self.name)

#
# Placeholder assignee for a reservation
#
def get_placeholder_reservation_assignee():
  return UserProfile.objects.get(user__email='bcse@northwestern.edu').id

class Reservation(models.Model):
  user = models.ForeignKey(UserProfile, related_name='user_reservations', on_delete=models.CASCADE)
  assignee = models.ForeignKey(UserProfile, null=True, blank=True, default=get_placeholder_reservation_assignee, related_name='assigned_reservations', on_delete=models.SET_NULL)
  pickup_assignee = models.ForeignKey(UserProfile, null=True, blank=True, default=get_placeholder_reservation_assignee, related_name='pickup_assigned_reservations', on_delete=models.SET_NULL)
  activity = models.ForeignKey(Activity, null=True, blank=True, on_delete=models.CASCADE)
  consumables = models.ManyToManyField('Consumable', null=True, blank=True, help_text='On Windows use Ctrl+Click to make multiple selection.  On a Mac use Cmd+Click to make multiple selection')
  num_of_classes = models.CharField(null=False, blank=False, max_length=1, choices=NUM_OF_CLASS_CHOICES)
  more_num_of_classes = models.CharField(null=True, blank=True, max_length=3, help_text='Enter number of classes')
  activity_kit_not_needed = models.BooleanField(default=False)
  other_activity = models.BooleanField(default=False)
  other_activity_name = models.CharField(null=True, blank=True, max_length=256, help_text='Name of the other activity')
  num_of_students = models.IntegerField(null=False, blank=False)
  include_gloves = models.BooleanField(default=False)
  include_goggles = models.BooleanField(default=False)
  equipment_not_needed = models.BooleanField(default=False)
  equipment = models.ManyToManyField(Equipment, null=True, blank=True)
  delivery_date = models.DateField(null=False)
  return_date = models.DateField(null=True, blank=True)
  notes = models.CharField(null=True, blank=True, max_length=2048, help_text='Any additional information')
  additional_help_needed = models.BooleanField(default=False)
  admin_notes = models.CharField(null=True, blank=True, max_length=2048, help_text='Notes only admins can add/view')
  color = models.ForeignKey('ReservationColor', null=True, blank=True, on_delete=models.SET_NULL)
  status = models.CharField(default='U', max_length=1, choices=RESERVATION_STATUS_CHOICES)
  email_sent = models.BooleanField(default=False)
  confirmation_email_dates = models.TextField(null=True, blank=True)
  feedback_status = models.CharField(null=True, max_length=1, choices=RESERVATION_FEEDBACK_STATUS_CHOICES)
  feedback_email_count = models.IntegerField(null=True, blank=True)
  feedback_email_date = models.DateField(null=True, blank=True)
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

  def get_activity_name(self):
    if self.activity:
      return self.activity
    else:
      return self.other_activity_name

################################################################################
# LINK BETWEEN RESERVATION AND WORKPLACE WHEN THE RESERVATION IS MADE
###############################################################################
class ReservationWorkPlace(models.Model):
  reservation = models.OneToOneField(Reservation, on_delete=models.CASCADE, related_name='reservation_to_work_place')
  work_place = models.ForeignKey(WorkPlace, on_delete=models.SET(get_placeholder_workplace), related_name='work_place_to_reservation')


class ReservationFeedback(models.Model):
  reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='reservation_to_feedback')
  feedback = models.ForeignKey('SurveySubmission', on_delete=models.CASCADE, related_name='feedback_to_reservation')

  class Meta:
      ordering = ['-id']
      unique_together = ('reservation', 'feedback')


class ReservationDeliveryAddress(models.Model):
  reservation = models.OneToOneField(Reservation, related_name='delivery_address', on_delete=models.CASCADE)
  street_address_1 = models.CharField(null=False, blank=False, max_length=256, help_text='Street Address 1')
  street_address_2 = models.CharField(null=True, blank=True, max_length=256, help_text='Street Address 2')
  city = models.CharField(null=False, blank=False, max_length=256, help_text='City')
  state = USStateField(null=False, blank=False, help_text='State')
  zip_code = models.CharField(null=False, blank=False, max_length=256, help_text='Zip Code')
  latitude = models.CharField(null=True, blank=True, max_length=256)
  longitude = models.CharField(null=True, blank=True, max_length=256)
  time_from_base = models.CharField(null=True, blank=True, max_length=256)
  distance_from_base = models.CharField(null=True, blank=True, max_length=256)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['reservation__id']

class ReservationMessage(models.Model):
  reservation = models.ForeignKey(Reservation, related_name='reservation_messages', on_delete=models.CASCADE)
  message = RichTextField(null=False, blank=False, config_name='message_ckeditor', help_text="Type your message here")
  viewed_by = models.ManyToManyField(UserProfile, null=True, blank=True)
  created_by = models.ForeignKey(UserProfile, related_name='reservation_messages', on_delete=models.CASCADE)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['created_date']

class BaxterBoxBlackoutDate(models.Model):
  start_date = models.DateField(null=False, blank=False, help_text='Blackout start date')
  end_date = models.DateField(null=False, blank=False, help_text='Blackout end date')
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['start_date', 'end_date']

class BaxterBoxMessage(models.Model):
  message = models.CharField(null=False, blank=False, max_length=2048)
  message_type = models.CharField(default='B',  max_length=1, choices=BAXTER_BOX_MESSAGE_TYPE_CHOICES)
  status = models.CharField(default='I',  max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['message_type']


class ReservationColor(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of the Color')
  color = models.CharField(null=False, max_length=8, unique=True, help_text='Hex code of the Color')
  description = models.CharField(null=False, blank=False, max_length=512, help_text='Describe the types of reservations/labs/consumables this color will be applied to')
  low_stock = models.BooleanField(default=False)
  low_stock_message = models.CharField(null=True, blank=True, max_length=2048, help_text='Message to display to the user when they pick an activity/consumable marked as low stock')
  rank = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1)], help_text='Rank to determine the low stock message to display')
  order = models.IntegerField(null=True, blank=True, validators=[MinValueValidator(1)], help_text='Display order')
  target = models.CharField(default='R', max_length=1, choices=COLOR_TARGET_CHOICES, help_text='The entities this color is applicable to')
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['order']

  def __str__(self):
    if self.low_stock:
      return '%s - %s (Low stock)' % (self.name, self.description)
    else:
      return '%s - %s' % (self.name, self.description)

class Team(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of the Team Member')
  description = RichTextField(null=True, blank=True, config_name='resource_url_ckeditor')
  email = models.EmailField(null=False, max_length=256)
  position = models.CharField(null=True, blank=True,  max_length=256, help_text='Position of the Team Member')
  organization = models.CharField(null=True, blank=True, max_length=256, help_text='Org. of the Team Member')
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image of this team member')
  order = models.IntegerField(null=False, blank=False)
  former_member = models.BooleanField(default=False)
  status = models.CharField(default='A',  max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['order']

  def __str__(self):
      return '%s' % (self.name)

class Partner(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of the Partner')
  description = RichTextField(null=True, blank=True)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image of this partner')
  url = models.URLField(null=False, blank=False)
  order = models.IntegerField(null=False, blank=False)
  status = models.CharField(default='A',  max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['order']

  def __str__(self):
      return '%s' % (self.name)

class Collaborator(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of the Collaborator')
  description = RichTextField(null=True, blank=True)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image of this collaborator')
  url = models.URLField(null=False, blank=False)
  order = models.IntegerField(null=False, blank=False)
  status = models.CharField(default='A',  max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['order']

  def __str__(self):
      return '%s' % (self.name)

class Survey(models.Model):
  name = models.CharField(null=False, max_length=256, help_text='Name of the Survey')
  survey_type = models.CharField(max_length=1, choices=SURVEY_TYPE_CHOICES)
  resource_url = models.URLField(null=True, blank=True, help_text="URL to a document/artifact/certificate that is downloaded to the user's device once the survey is submitted.")
  email_confirmation =  models.BooleanField(default=False, help_text='Email confirmation is only sent if the user is logged in while filling out the survey or there is in email field component in the survey.')
  email_confirmation_message = models.CharField(null=True, blank=True, max_length=256, help_text='Confirmation message to send via email')
  admin_notification =  models.BooleanField(default=False, help_text='Send email notification to admins when a survey is submitted.')
  status = models.CharField(default='A',  max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['created_date']

  def __str__(self):
      return '%s' % (self.name)

class SurveyComponent(models.Model):
  survey = models.ForeignKey(Survey, related_name='survey_component', on_delete=models.CASCADE)
  page = models.IntegerField(null=False, blank=False)
  order = models.IntegerField(null=False, blank=False)
  component_type = models.CharField(null=False, max_length=2, choices=SURVEY_COMPONENT_TYPE_CHOICES, default='IN')
  content = RichTextField(null=True, blank=True)
  options = models.TextField(null=True, blank=True)
  display_other_option = models.BooleanField(default=False)
  other_option_label = models.CharField(null=True, blank=True, max_length=256)
  is_required = models.BooleanField(default=False)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['page', 'order']
      unique_together = ('survey', 'page', 'order')

class SurveySubmission(models.Model):
  UUID = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
  survey = models.ForeignKey(Survey, related_name='survey_submission', on_delete=models.CASCADE)
  user = models.ForeignKey(UserProfile, blank=True, null=True, related_name='user_survey', on_delete=models.CASCADE)
  ip_address = models.GenericIPAddressField()
  status = models.CharField(default='I',  max_length=1, choices=SURVEY_SUBMISSION_STATUS_CHOICES)
  admin_notes = models.CharField(null=True, blank=True, max_length=2048, help_text='Notes only admins can add/view')
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)


#################################################################
# Workplace associated with Survey Submission
#############################################################
class SurveySubmissionWorkPlace(models.Model):
  submission = models.OneToOneField(SurveySubmission, on_delete=models.CASCADE, related_name='survey_submission_to_work_place')
  work_place = models.ForeignKey(WorkPlace, on_delete=models.SET(get_placeholder_workplace), related_name='work_place_to_survey_submission')


class SurveyResponse(models.Model):
  submission = models.ForeignKey(SurveySubmission, related_name='survey_response', on_delete=models.CASCADE)
  survey_component = models.ForeignKey(SurveyComponent, related_name='survey_response', on_delete=models.CASCADE)
  response = models.TextField(null=True, blank=True)
  responseFile = models.FileField(upload_to=upload_file_to, null=True, blank=True)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)


class HomepageBlock(models.Model):
  title = models.CharField(null=False, max_length=256, help_text='Block title')
  sub_title = models.CharField(null=True, blank=True, max_length=256)
  description = RichTextUploadingField(null=True, blank=True)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image for this block')
  button_text = models.CharField(null=True, blank=True, max_length=256)
  button_url = models.CharField(null=True, blank=True, max_length=256)
  order = models.IntegerField(null=False, blank=False)
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['-id']

  def __str__(self):
      return '%s' % (self.title)

class StandalonePage(models.Model):
  title = models.CharField(null=False, max_length=256, help_text='Page title')
  sub_title = models.CharField(null=True, blank=True, max_length=256)
  body = RichTextUploadingField(null=True, blank=True)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image for this page')
  image_position = models.CharField(default='L', max_length=1, choices=(('L', 'Left'), ('R', 'Right'),))
  button_text = models.CharField(null=True, blank=True, max_length=256)
  button_url = models.CharField(null=True, blank=True, max_length=256)
  url_alias = models.CharField(null=True, blank=True, max_length=256, unique=True)
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['-id']

  def __str__(self):
      return '%s' % (self.title)


class Vignette(models.Model):
  title = models.CharField(null=False, max_length=256, help_text='Vignette title')
  blurb = RichTextField(null=True, blank=True)
  image = models.ImageField(upload_to=upload_file_to, blank=True, null=True, help_text='Upload an image for this vignette')
  external_link = models.URLField(null=True, blank=True, max_length=2048)
  featured =  models.BooleanField(default=False, help_text='If marked "Featured", this vignette will be displayed on the "Teacher Leadership Opportunities" page')
  status = models.CharField(default='A', max_length=1, choices=CONTENT_STATUS_CHOICES)
  order = models.IntegerField(null=False, blank=False)
  created_date = models.DateTimeField(auto_now_add=True)
  modified_date = models.DateTimeField(auto_now=True)

  class Meta:
      ordering = ['order']

  def __str__(self):
      return '%s' % (self.title)

# signal to check if registration status has changed
# and then send an email to the registrant
@receiver(post_save, sender=Registration)
def check_registration_status_change(sender, instance, **kwargs):
  try:
    workshop = Workshop.objects.get(id=instance.workshop_registration_setting.workshop.id)
    current_datetime = datetime.datetime.now()
    current_date = current_datetime.date()
    #only send email notification if the workshop hasn't ended
    if current_date < workshop.end_date:
      try:
        #get email message from Workshop first
        confirmation_message_object = WorkshopRegistrationEmail.objects.get(workshop=workshop, registration_status=instance.status)
      except WorkshopRegistrationEmail.DoesNotExist:
        #get general registration email message for the respective registration status
        confirmation_message_object = RegistrationEmailMessage.objects.get(registration_status=instance.status)

      userProfile = instance.user
      registration_setting = workshop.registration_setting

      subject = replace_workshop_tokens(confirmation_message_object.email_subject, workshop, instance)

      current_site = Site.objects.get_current()
      domain = current_site.domain
      if domain != 'bcse.northwestern.edu':
        subject = '***** TEST **** '+ subject + ' ***** TEST **** '

      email_body = replace_workshop_tokens(confirmation_message_object.email_message, workshop, instance)

      context = {'email_body': email_body, 'domain': domain}
      body = get_template('bcse_app/EmailGeneralTemplate.html').render(context)

      email_addresses = [userProfile.user.email]
      if userProfile.secondary_email:
        email_addresses.append(userProfile.secondary_email)
      email = EmailMessage(subject, body, settings.DEFAULT_FROM_EMAIL, email_addresses)

      #check if calendar invite needs to be attached
      if confirmation_message_object.include_calendar_invite:
        filename = create_calendar_invite(workshop, userProfile)
        email.attach_file(filename, 'text/calendar')

      email.content_subtype = "html"
      email.send(fail_silently=True)

      check_registration_promotion(workshop)

  except RegistrationEmailMessage.DoesNotExist as e:
    pass

# signal to check if registration has been deleted
# and promote other registrations in the waitlist if applicable
@receiver(post_delete, sender=Registration)
def check_registration_delete(sender, instance, **kwargs):
  try:
    workshop = Workshop.objects.get(id=instance.workshop_registration_setting.workshop.id)
    check_registration_promotion(workshop)

  except Workshop.DoesNotExist as e:
    pass

# signal to check if workshop capacity has changed
# and promote other registrations in the waitlist if applicable
@receiver(pre_save, sender=WorkshopRegistrationSetting)
def check_workshop_capacity_change(sender, instance, **kwargs):
  try:
    obj = sender.objects.get(pk=instance.pk)
    if obj.capacity != instance.capacity:
      check_registration_promotion(instance.workshop)
  except sender.DoesNotExist:
    pass


# when a workshop registration is cancelled, deleted or workshop capacity increased,
# promote registrations in the waitlist if applicable
def check_registration_promotion(workshop):
  current_datetime = datetime.datetime.now()
  current_date = current_datetime.date()
  if current_date < workshop.end_date:
    registration_type = workshop.registration_setting.registration_type
    capacity = workshop.registration_setting.capacity
    if registration_type == 'R':
      registered_count = Registration.objects.all().filter(workshop_registration_setting=workshop.registration_setting, status='R').count()
      waitlist = Registration.objects.all().filter(workshop_registration_setting=workshop.registration_setting, status='W').order_by('created_date')
      if waitlist.count() > 0:
        if capacity is not None and capacity > 0:
          available_space = capacity - registered_count
          if available_space > 0:
            if available_space < waitlist.count():
              waitlist = waitlist[:available_space]
          else:
            waitlist = None

        if waitlist:
          for registration in waitlist:
            registration.status = 'R'
            registration.save()

# signal to check if workplace address has changed
# then update latitude and longitude
@receiver(pre_save, sender=WorkPlace)
@receiver(pre_save, sender=ReservationDeliveryAddress)
def check_workplace_address_change(sender, instance, **kwargs):
  calculate = False
  try:
    obj = sender.objects.get(pk=instance.pk)
    if obj.street_address_1 != instance.street_address_1 or obj.street_address_2 != instance.street_address_2 or obj.city != instance.city or obj.state != instance.state or obj.zip_code != instance.zip_code or instance.distance_from_base is None:
      if instance.street_address_1 is not None and instance.street_address_1 != '' and instance.city is not None and instance.city != '' and instance.state is not None and instance.state != '' and instance.zip_code is not None and instance.zip_code != '':
        calculate = True
  except sender.DoesNotExist:
    # Object is new, so field hasn't technically changed, but you may want to do something else here.
    calculate = True

  if calculate:
    full_address = "%s %s %s %s %s" % (instance.street_address_1, instance.street_address_2, instance.city, instance.state, instance.zip_code)
    full_address = urllib.parse.quote(full_address)

    headers = CaseInsensitiveDict()
    headers["Accept"] = "application/json"

    url = "%sgeocode/search?text=%s&apiKey=%s" % (settings.GEOAPIFY_BASE_URL, full_address, settings.GEOAPIFY_KEY)
    resp = requests.get(url, headers=headers)
    geocode = resp.json()
    if "features" in geocode and geocode["features"] and "geometry" in geocode["features"][0] and "coordinates" in geocode["features"][0]["geometry"]:
      latlong = geocode["features"][0]["geometry"]["coordinates"]
      longitude = latlong[0]
      latitude = latlong[1]

      latlong_param = "%f,%f|%f,%f" % (settings.COLFAX_LATITUDE, settings.COLFAX_LONGITUDE, latitude, longitude)
      latlong_param = urllib.parse.quote(latlong_param)

      url = "%srouting?waypoints=%s&mode=drive&units=imperial&apiKey=%s" % (settings.GEOAPIFY_BASE_URL, latlong_param, settings.GEOAPIFY_KEY)
      resp = requests.get(url, headers=headers)
      drive = resp.json()
      if "features" in drive:
        distance = drive["features"][0]["properties"]["distance"]
        unit = drive["features"][0]["properties"]["distance_units"]
        time = drive["features"][0]["properties"]["time"]
        instance.latitude = latitude
        instance.longitude = longitude
        instance.time_from_base = round(time/60, 2)
        instance.distance_from_base = distance


#
# Replace workshop registration message tokens before sending out an email
#
def replace_workshop_tokens(text, workshop, registration=''):
  replaced_text = text
  replaced_text = replaced_text.replace('[workshop_category]', workshop.workshop_category.name or '')
  replaced_text = replaced_text.replace('[workshop_title]', workshop.name or '')
  replaced_text = replaced_text.replace('[workshop_sub_title]', workshop.sub_title or '')
  replaced_text = replaced_text.replace('[workshop_start_date]', workshop.start_date.strftime('%B %-d, %Y') if workshop.start_date else '')
  replaced_text = replaced_text.replace('[workshop_start_time]', workshop.start_time.strftime('%-I:%M %p') if workshop.start_time else '')
  replaced_text = replaced_text.replace('[workshop_end_date]', workshop.end_date.strftime('%B %-d, %Y') if workshop.end_date else '')
  replaced_text = replaced_text.replace('[workshop_end_time]', workshop.end_time.strftime('%-I:%M %p') if workshop.end_time else '')
  replaced_text = replaced_text.replace('[workshop_summary]', workshop.summary or '')
  replaced_text = replaced_text.replace('[workshop_location]', workshop.location or '')
  replaced_text = replaced_text.replace('[workshop_meetup_url]', workshop.meetup_link or '')
  replaced_text = replaced_text.replace('[isbe_url]', workshop.registration_setting.isbe_link or '')

  photo_release_text = ''
  if registration and not registration.user.photo_release_complete:
    photo_release_text = 'We do not have a photo release on file for you. Please click <a href="%s">here</a> to complete it before attending this event.' % settings.PHOTO_RELEASE_URL
  replaced_text = replaced_text.replace('[photo_release_url]', photo_release_text or '')

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

