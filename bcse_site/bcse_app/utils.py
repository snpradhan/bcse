# utils.py
import os
from datetime import datetime, timedelta, date
from calendar import HTMLCalendar

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
                  <div class='date'>{day}</div> \
                  <div> {d} </div> \
                </td>"
      else:
        return f"<td class='out_of_range'> \
                  <div class='date'>{day}</div> \
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
