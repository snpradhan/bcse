from datetime import datetime
from django.core.cache import cache
from django.conf import settings
from django.contrib import auth, messages
from bcse_app import models, views
from django.utils.deprecation import MiddlewareMixin
from django.http import HttpResponse
from django import shortcuts
from django.contrib.auth.models import User
from django.contrib.sites.models import Site

class UpdateSession(MiddlewareMixin):

  def process_request(self, request):
    if not request.user.is_authenticated:
      #Can't log out if not logged in
      return
    # only update non ajax requests
    if not request.is_ajax():
      request.session['last_touch'] = str(datetime.now())

ONLINE_THRESHOLD = getattr(settings, 'ONLINE_THRESHOLD', 60*15)

def get_online_now(self):
  return User.objects.filter(id__in=self.online_now_ids or [])

class OnlineNowMiddleware(MiddlewareMixin):
  """
  Maintains a list of users who have interacted with the website recently.
  Their user IDs are available as ``online_now_ids`` on the request object,
  and their corresponding users are available (lazily) as the
  ``online_now`` property on the request object.
  """


  def process_request(self, request):
    # First get the index
    uids = cache.get('online-now', [])

    # Perform the multiget on the individual online uid keys
    online_keys = ['online-%s' % (u,) for u in uids]
    fresh = cache.get_many(online_keys).keys()
    online_now_ids = [int(k.replace('online-', '')) for k in fresh]

    # If the user is authenticated, add their id to the list
    if request.user.is_authenticated:
        uid = request.user.id
        # If their uid is already in the list, we want to bump it
        # to the top, so we remove the earlier entry.
        if uid in online_now_ids:
            online_now_ids.remove(uid)
        online_now_ids.append(uid)

    # Attach our modifications to the request object
    request.__class__.online_now_ids = online_now_ids
    request.__class__.online_now = property(get_online_now)

    # Set the new cache
    cache.set('online-%s' % (request.user.pk,), True, ONLINE_THRESHOLD)
    cache.set('online-now', online_now_ids, ONLINE_THRESHOLD)

class NextParameterMiddleware(MiddlewareMixin):

  def process_request(self, request):

    redirect_url = request.GET.get('next', '')
    target = None
    if redirect_url.find('password_reset') == 1:
      target = '#password'
    elif redirect_url.find('reset') == 1:
      target = '#password'
    elif redirect_url.find('signin') == 1:
      target = '#signin'
    elif redirect_url.find('signup') == 1:
      target = '#signup'
    elif redirect_url.find('survey') == 1 or redirect_url.find('vignette') == 1:
      target = '#general'
    elif redirect_url.find('userProfile') == 1:
      target = '#profile'
    elif redirect_url.find('activity') == 1:
      target = '#kit'
    elif redirect_url.find('subscribe') == 1:
      target = '#general'
    elif redirect_url.find('giveaway') == 1:
      target = '#general'
      print(target)
      print(redirect_url)

    if request.user.is_authenticated and redirect_url.find('signin') == 1 and redirect_url.find('survey') > 1:
      redirect_url = redirect_url.replace('/signin/?next=/?next=', '')
      target = '#general'

    if request.user.is_authenticated and views.profile_update_required(request.user.userProfile):
      target = '#profile'
      if redirect_url:
        redirect_url = '/userProfile/%s/edit?next=/?next=%s' % (request.user.userProfile.id, redirect_url)
      else:
        redirect_url = '/userProfile/%s/edit' % request.user.userProfile.id


    if target and redirect_url:
      print('setting ', target, redirect_url)
      request.target = target
      request.redirect_url = redirect_url

class DomainMiddleware(MiddlewareMixin):
  def process_request(self, request):
    current_site = Site.objects.get_current()
    domain = current_site.domain

    if 'localhost' in domain:
      request.domain = 'localhost'
    elif 'stage' in domain:
      request.domain = 'stage'


class AjaxDetectionMiddleware:
    """
    Re-adds the `is_ajax()` method to the request object
    to support older code in Django 4.x+.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.is_ajax = lambda: request.headers.get('x-requested-with') == 'XMLHttpRequest'
        return self.get_response(request)
