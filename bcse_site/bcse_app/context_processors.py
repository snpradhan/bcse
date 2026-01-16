from django.conf import settings
from bcse_app import models

def partners_processor(request):
  return {
    'partners': models.Partner.objects.all().filter(status='A')
  }

def recaptcha_public_key(request):
  return {
      'RECAPTCHA_PUBLIC_KEY': settings.RECAPTCHA_PUBLIC_KEY
  }

