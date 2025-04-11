from bcse_app import models, utils, views
from datetime import datetime, timedelta
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.core import management
from django.utils import timezone
from django.db.models import Q
import subprocess
import xlwt
from PIL import ImageColor
import copy

def backup_db():
  print('start db backup', datetime.today())
  #remove old backups from the file system
  #cmd = 'rm %s/*'% settings.DBBACKUP_STORAGE_OPTIONS['location']
  #subprocess.call(cmd, shell=True)
  management.call_command('dbbackup', '--compress')
  '''cmd = 's3cmd --access_key=%s --secret_key=%s -s put %s/default-* s3://%s' % (settings.AWS_ACCESS_KEY_ID,
                                                                               settings.AWS_SECRET_ACCESS_KEY,
                                                                               settings.DBBACKUP_STORAGE_OPTIONS['location'],
                                                                              settings.DBBACKUP_AWS_S3_BUCKET)
  '''
  #subprocess.call(cmd, shell=True)
  print('end db backup', datetime.today())


####################################
# Export Reservations to Excel
####################################
def export_reservations():
  print('start reservations export', datetime.today())

  reservations = models.Reservation.objects.all().filter(status__in=['O', 'R', 'U']).order_by('delivery_date')

  #response = http.HttpResponse(content_type='application/ms-excel')
  #response['Content-Disposition'] = 'attachment; filename="reservations_%s.xls"'%datetime.datetime.now()
  wb = xlwt.Workbook(encoding='utf-8')

  reservation_colors = models.ReservationColor.objects.all()
  color_index = 8
  color_map = {}
  for color in reservation_colors:
    xlwt.add_palette_colour(color.name, color_index)
    rgb = ImageColor.getrgb(color.color)
    wb.set_colour_RGB(color_index, rgb[0], rgb[1], rgb[2])
    color_map[color.color] = color_index
    color_index += 1

  borders = xlwt.Borders()
  borders.left = xlwt.Borders.THIN
  borders.right = xlwt.Borders.THIN
  borders.top = xlwt.Borders.THIN
  borders.bottom = xlwt.Borders.THIN

  bold_font_style = xlwt.XFStyle()
  bold_font_style.font.bold = True
  bold_font_style.borders = borders
  font_style = xlwt.XFStyle()
  font_style.alignment.wrap = 1
  font_style.borders = borders
  date_format = xlwt.XFStyle()
  date_format.num_format_str = 'mm/dd/yyyy'
  date_format.borders = borders

  columns = ['ID', 'Reservation Made On', 'User', 'User Email', 'Activity', 'Kit', 'Consumables', 'Include Gloves/Goggles', 'Equipment', 'Pickup/Return Notes', 'Delivery Date', 'Return Date', 'Delivery Address', 'Delivery Distance (miles)', 'Delivery Travel Time (mins)', 'Admin Notes', 'Help Needed?', 'Assigned To', 'Confirmation Email Sent?', 'Status']
  font_styles = [font_style, date_format, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, date_format, date_format, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style]

  ws = wb.add_sheet('Reservations')
  row_num = 0
  #write the headers
  header_style = copy.deepcopy(bold_font_style)
  header_style.font.colour_index = xlwt.Style.colour_map['ivory']
  header_style.font.height = 240
  pattern = xlwt.Pattern()
  pattern.pattern = pattern.SOLID_PATTERN
  pattern.pattern_fore_colour = xlwt.Style.colour_map['gray50']
  header_style.pattern = pattern
  for col_num in range(len(columns)):
    ws.write(row_num, col_num, columns[col_num], header_style)

  for reservation in reservations:
    activity = kit = equipment = delivery_address = delivery_distance = delivery_time = assignee_name = consumables = ''

    if reservation.activity:
      activity = reservation.activity.name
    elif reservation.other_activity:
      activity = reservation.other_activity_name

    if reservation.activity and not reservation.activity_kit_not_needed:
      kit = reservation.activity.kit_name + 'x'
      if reservation.num_of_classes and reservation.num_of_classes != '5':
        kit += reservation.num_of_classes
      elif reservation.more_num_of_classes:
        kit += reservation.more_num_of_classes

      for consumable in reservation.activity.consumables.all():
        consumables = consumables + consumable.name + '\n'

    for equip in reservation.equipment.all():
      equipment = equip.equipment_type.name + (equip.name) + '\n'

    if hasattr(reservation, 'delivery_address') and reservation.delivery_address:
      delivery_address = reservation.delivery_address.street_address_1 + '\n'
      if reservation.delivery_address.street_address_2:
        delivery_address += reservation.delivery_address.street_address_2 + '\n'
      delivery_address += reservation.delivery_address.city +', '+ reservation.delivery_address.state + ' ' +reservation.delivery_address.zip_code
      delivery_distance = reservation.delivery_address.distance_from_base
      delivery_time = reservation.delivery_address.time_from_base
    elif reservation.user.work_place:
      delivery_address = reservation.user.work_place.name + '\n'
      delivery_address += reservation.user.work_place.street_address_1 + '\n'
      if reservation.user.work_place.street_address_2:
        delivery_address += reservation.user.work_place.street_address_2 + '\n'
      if reservation.user.work_place.city:
        delivery_address += reservation.user.work_place.city + ','
      delivery_address += reservation.user.work_place.state + ' '+ reservation.user.work_place.zip_code
      delivery_distance = reservation.user.work_place.distance_from_base
      delivery_time = reservation.user.work_place.time_from_base

    if reservation.assignee:
      assignee_name = reservation.assignee.user.get_full_name()

    row = [reservation.id,
           reservation.created_date.replace(tzinfo=None),
           reservation.user.user.get_full_name(),
           reservation.user.user.email,
           activity,
           kit,
           consumables,
           "Yes" if reservation.include_gloves_goggles else "No",
           equipment,
           reservation.notes,
           reservation.delivery_date,
           reservation.return_date,
           delivery_address,
           delivery_distance,
           delivery_time,
           reservation.admin_notes,
           "Yes" if reservation.additional_help_needed else "No",
           assignee_name,
           "Yes" if reservation.email_sent else "No",
           reservation.get_status_display()

           ]

    row_num += 1
    for col_num in range(len(row)):
      if reservation.color:
        style = copy.deepcopy(font_styles[col_num])
        pattern = xlwt.Pattern()
        pattern.pattern = pattern.SOLID_PATTERN
        pattern.pattern_fore_colour = color_map[reservation.color.color]
        style.pattern = pattern
        ws.write(row_num, col_num, row[col_num], style)
      else:
        ws.write(row_num, col_num, row[col_num], font_styles[col_num])

  ws = wb.add_sheet('Export Details')
  ws.write(0, 0, 'Exported Date', bold_font_style)
  date_format.num_format_str = 'mm/dd/yyyy h:mm:ss AM/PM'
  ws.write(0, 1, datetime.today(), date_format)
  ws.write(1, 0, 'Reservations Count', bold_font_style)
  ws.write(1, 1, row_num, font_style)


  cmd = 'rm /tmp/reservations.xls'
  subprocess.call(cmd, shell=True)

  wb.save('/tmp/reservations.xls')

  print('exporting %s reservations' % reservations.count())

  cmd = 's3cmd --access_key=%s --secret_key=%s -s put %s s3://%s/export/reservations.xls' % (settings.AWS_ACCESS_KEY_ID,
                                                                     settings.AWS_SECRET_ACCESS_KEY,
                                                                     '/tmp/reservations.xls',
                                                                     settings.AWS_STORAGE_BUCKET_NAME)
  subprocess.call(cmd, shell=True)

  print('end reservations export', datetime.today())


####################################
# Export Activities to Excel
####################################
def export_activities():
  print('start activities export', datetime.today())

  activities = models.Activity.objects.all().order_by('name')

  wb = xlwt.Workbook(encoding='utf-8')

  activites_colors = models.ReservationColor.objects.all().filter(target__in=['K', 'B'])
  color_index = 8
  color_map = {}
  for color in activites_colors:
    xlwt.add_palette_colour(color.name, color_index)
    rgb = ImageColor.getrgb(color.color)
    wb.set_colour_RGB(color_index, rgb[0], rgb[1], rgb[2])
    color_map[color.color] = color_index
    color_index += 1

  borders = xlwt.Borders()
  borders.left = xlwt.Borders.THIN
  borders.right = xlwt.Borders.THIN
  borders.top = xlwt.Borders.THIN
  borders.bottom = xlwt.Borders.THIN

  bold_font_style = xlwt.XFStyle()
  bold_font_style.font.bold = True
  bold_font_style.borders = borders
  font_style = xlwt.XFStyle()
  font_style.alignment.wrap = 1
  font_style.borders = borders
  date_format = xlwt.XFStyle()
  date_format.num_format_str = 'mm/dd/yyyy'
  date_format.borders = borders

  columns = ['ID', 'Name', 'Description', 'Materials/Equipment', 'Manuals/Resources', 'Kit Name', 'Kit Unit Cost', 'Inventory', 'Admin Notes', 'Equipment Mapping', 'Tags', 'Image', 'Status', 'Modified Date', 'Created Date']
  font_styles = [font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, font_style, date_format, date_format]

  ws = wb.add_sheet('Activities')
  row_num = 0
  #write the headers
  header_style = copy.deepcopy(bold_font_style)
  header_style.font.colour_index = xlwt.Style.colour_map['ivory']
  header_style.font.height = 240
  pattern = xlwt.Pattern()
  pattern.pattern = pattern.SOLID_PATTERN
  pattern.pattern_fore_colour = xlwt.Style.colour_map['gray50']
  header_style.pattern = pattern
  for col_num in range(len(columns)):
    ws.write(row_num, col_num, columns[col_num], header_style)

  equipment_mapping = ''
  tags = ''

  for activity in activities:

    equipment_mapping = ''
    tags = ''

    for category, subcategories in utils.get_tag_dictionary(activity.tags.all()):
      tags += '• ' + category +'\n'
      for subcategory in subcategories:
        tags += '  • ' + subcategory +'\n'

    for equipment in activity.equipment_mapping.all():
      equipment_mapping += '• ' + equipment.name + '\n'

    row = [activity.id,
           activity.name,
           utils.strip_html(activity.description) if activity.description else ' ',
           utils.strip_html(activity.materials_equipment) if activity.materials_equipment else ' ',
           utils.strip_html(activity.manuals_resources) if activity.manuals_resources else ' ',
           activity.kit_name,
           activity.kit_unit_cost,
           utils.strip_html(activity.inventory) if activity.inventory else ' ',
           utils.strip_html(activity.notes) if activity.notes else ' ',
           equipment_mapping,
           tags,
           activity.image.url if activity.image else ' ',
           activity.get_status_display(),
           activity.modified_date.replace(tzinfo=None),
           activity.created_date.replace(tzinfo=None)
          ]

    row_num += 1
    for col_num in range(len(row)):
      if activity.color:
        style = copy.deepcopy(font_styles[col_num])
        pattern = xlwt.Pattern()
        pattern.pattern = pattern.SOLID_PATTERN
        pattern.pattern_fore_colour = color_map[activity.color.color]
        style.pattern = pattern
        ws.write(row_num, col_num, row[col_num], style)
      else:
        ws.write(row_num, col_num, row[col_num], font_styles[col_num])

  ws = wb.add_sheet('Export Details')
  ws.write(0, 0, 'Exported Date', bold_font_style)
  date_format.num_format_str = 'mm/dd/yyyy h:mm:ss AM/PM'
  ws.write(0, 1, datetime.today(), date_format)
  ws.write(1, 0, 'Activity Count', bold_font_style)
  ws.write(1, 1, row_num, font_style)


  cmd = 'rm /tmp/activities.xls'
  subprocess.call(cmd, shell=True)

  wb.save('/tmp/activities.xls')

  print('exporting %s activities' % activities.count())

  cmd = 's3cmd --access_key=%s --secret_key=%s -s put %s s3://%s/export/activities.xls' % (settings.AWS_ACCESS_KEY_ID,
                                                                     settings.AWS_SECRET_ACCESS_KEY,
                                                                     '/tmp/activities.xls',
                                                                     settings.AWS_STORAGE_BUCKET_NAME)
  subprocess.call(cmd, shell=True)

  print('end activities export', datetime.today())


def send_workshop_emails():
  print('start workshop emails', datetime.today())
  now = datetime.now()
  current_date = now.strftime('%Y-%m-%d')
  current_time = now.strftime('%H:%M:%S')

  workshop_emails = models.WorkshopEmail.objects.all().filter(email_status='D', workshop__cancelled=False)
  workshop_emails = workshop_emails.filter(Q(scheduled_date__lt=current_date) | Q(Q(scheduled_date=current_date), Q(Q(scheduled_time__isnull=True) | Q(scheduled_time__lte=current_time))))
  print('sending %s workshop emails' % len(workshop_emails))
  for workshop_email in workshop_emails:
    message = views.send_workshop_email(workshop_email.id, True)
    print(message[1])

  print('end workshop emails', datetime.today())
