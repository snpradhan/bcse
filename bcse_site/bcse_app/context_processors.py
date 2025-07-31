from bcse_app import models

def partners_processor(request):
  return {
    'partners': models.Partner.objects.all().filter(status='A')
  }
