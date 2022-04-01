from django import template
from bcse_app import models, views
from django.contrib import messages
import datetime
from django.db.models import Q
from django.utils import timezone
from collections import OrderedDict

register = template.Library()

@register.filter
def get_item(dictionary, key):
  return dictionary.get(key)

@register.filter
def daterange(start_date, end_date):
  delta = end_date - start_date
  days = delta.days + 1
  for n in range(int(days)):
    yield start_date + datetime.timedelta(n)

@register.filter
def get_page_start_index(paginator, page_number):
  return paginator.page(page_number).start_index()

@register.filter
def get_page_end_index(paginator, page_number):
  return paginator.page(page_number).end_index()
