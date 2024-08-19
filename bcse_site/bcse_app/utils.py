# utils.py
import os
from datetime import datetime, timedelta, date
from calendar import HTMLCalendar
import re

def get_filename(filename):
  now = datetime.now()
  dt = now.strftime("%Y-%m-%d-%H-%M-%S-%f")
  filename_base, filename_ext = os.path.splitext(filename)
  return '%s_%s%s' % (filename_base.lower(), dt, filename_ext.lower(),)

class Calendar(HTMLCalendar):
  def __init__(self, year=None, month=None):
    self.year = year
    self.month = month
    super(Calendar, self).__init__()

  def formatday(self, day, availability_matrix, delivery_date, return_date):
    #events_per_day = events.filter(start_time__day=day)
    d = ''

    is_in_range = False

    if day != 0:
      index_date = date(self.year, self.month, day)
      dayofweek = index_date.strftime('%a')
      if index_date >= delivery_date and index_date <= return_date:
        is_in_range = True

      if is_in_range:
        for equipment_type, availability in availability_matrix.items():
          equipment = availability['most_available_equip']
          is_available = availability['availability_dates'][equipment][index_date]
          if is_available:
            d += f'<div class="available"> {equipment_type.short_name}</div>'
          else:
            d += f'<div class="unavailable"> {equipment_type.short_name} </div>'


        return f"<td class='selected_date'> \
                  <div class='date'>\
                    <div> {day} </div> \
                  </div> \
                  <div> {d} </div> \
                </td>"
      else:
        return f"<td class='out_of_range'> \
                  <div class='date'> \
                    <div> {day} </div> \
                  </div> \
                  <div> </div> \
                </td>"

    return "<td></td>"

  def formatweek(self, theweek, availability_matrix, delivery_date, return_date):
    week = ''
    for d, weekday in theweek:
      week += self.formatday(d, availability_matrix, delivery_date, return_date)
    return f'<tr> {week} </tr>'

  def formatmonth(self, withyear=True, availability_matrix={}, delivery_date=None, return_date=None):
    #events = Event.objects.filter(start_time__year=self.year, start_time__month=self.month)
    cal = f'<table class="calendar table table-bordered">\n'
    cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
    cal += f'{self.formatweekheader()}\n'
    for week in self.monthdays2calendar(self.year, self.month):
      cal += f'{self.formatweek(week, availability_matrix, delivery_date, return_date)}\n'
    cal += f'</table>'
    return cal


class AdminCalendar(HTMLCalendar):
  def __init__(self, year=None, month=None):
    self.year = year
    self.month = month
    super(AdminCalendar, self).__init__()

  def formatday(self, day, availability_matrix):
    #events_per_day = events.filter(start_time__day=day)
    d = ''

    is_in_range = False
    availability_class = ''

    if day != 0:
      index_date = date(self.year, self.month, day)
      dayofweek = index_date.strftime('%a')

      if len(availability_matrix) == 1:
        for equipment_type, availability in availability_matrix.items():

          availability_class = ''
          index = 0

          for equip, equip_availability in availability[index_date].items():
            index += 1
            if equip_availability['available']:
              d += f'<div class="availability_row all_available"> \
                   <div>Kit {index} - <i class="fas fa-check"></i></div></div>'
            else:
              location = equip_availability['location']
              if location is None:
                location = "Location not set"
              d += f'<div class="availability_row all_checked_out"> \
                   <div>Kit {index} <i class="fas fa-at"></i> {location}</div></div>'

        return f"<td> \
                  <div class='date'>\
                    <div>{dayofweek}</div> \
                    <div> {day} </div> \
                  </div> \
                  <div> {d} </div> \
                </td>"

      else:
        for equipment_type, availability in availability_matrix.items():

          available = 0
          checked_out = 0
          availability_class = ''

          for equip, equip_availability in availability[index_date].items():

            if equip_availability['available']:
              available += 1
            else:
              checked_out += 1

          if available > 0:
            if checked_out > 0:
              availability_class = "availability_row mixed_availability"
            else:
              availability_class = "availability_row all_available"
          else:
            availability_class = "availability_row all_checked_out"

          d += f'<div class="{availability_class}"> \
                   <div>{equipment_type.short_name}</div>\
                   <div class="availability">'

          if available:
            d += f'<div>{available} <i class="fas fa-check"></i></div>'

          if checked_out:
            d += f'<div>{checked_out} <i class="fas fa-shopping-cart"></i><i class="fas fa-arrow-right"></i></div>'

          d += '</div></div>'


        return f"<td> \
                  <div class='date'> \
                    <div>{dayofweek} </div> \
                    <div>{day}</div> \
                  </div>\
                  <div> {d} </div> \
                </td>"


    return "<td></td>"

  def formatweek(self, theweek, availability_matrix):
    week = ''
    for d, weekday in theweek:
      week += self.formatday(d, availability_matrix)
    return f'<tr> {week} </tr>'

  def formatmonth(self, withyear=True, availability_matrix={}):
    #events = Event.objects.filter(start_time__year=self.year, start_time__month=self.month)
    cal = f'<table class="calendar table table-bordered">\n'
    cal += f'{self.formatmonthname(self.year, self.month, withyear=withyear)}\n'
    #cal += f'{self.formatweekheader()}\n'
    for week in self.monthdays2calendar(self.year, self.month):
      cal += f'{self.formatweek(week, availability_matrix)}\n'
    cal += f'</table>'
    return cal


def get_tag_dictionary(tags):
  tag_dictionary = {}
  for tag in tags:
    if tag.tag.name in tag_dictionary:
      tag_dictionary[tag.tag.name].append(tag.name)
    else:
      tag_dictionary[tag.tag.name] = [tag.name]
  return tag_dictionary.items()

def strip_html(html_string):
  clean = re.compile('<.*?>')
  return re.sub(clean, '', html_string)
