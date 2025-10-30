"""bcse_site URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.auth import views as auth_views
from ckeditor_uploader import views as ckeditor_views
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.i18n import JavaScriptCatalog
from bcse_app.forms import SecondaryEmailPasswordResetForm
from bcse_app.views import UserAutocomplete, RegistrantAutocomplete, WorkplaceAutocomplete, WorkplaceAllAutocomplete, TeacherLeaderAutocomplete

urlpatterns = [
    path('', include('bcse_app.urls', namespace="bcse")),
    path('admin/', admin.site.urls),

    path('password_reset/',
         auth_views.PasswordResetView.as_view(
             form_class=SecondaryEmailPasswordResetForm,
             template_name='password_reset/password_reset_form.html',
             html_email_template_name='password_reset/password_reset_email.html',
             email_template_name='password_reset/password_reset_email.txt',
             subject_template_name='password_reset/password_reset_subject.txt',
             success_url='/password_reset/done/'
         ), name='password_reset'),
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='password_reset/password_reset_done.html'
         ), name='password_reset_done'),
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='password_reset/password_reset_confirm.html',
             success_url='/reset/done/',
             post_reset_login=False,
         ), name='password_reset_confirm'),
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='password_reset/password_reset_complete.html'
         ), name='password_reset_complete'),

    path('user-autocomplete/', UserAutocomplete.as_view(), name='user-autocomplete'),
    path('teacher-leader-autocomplete/', TeacherLeaderAutocomplete.as_view(), name='teacher-leader-autocomplete'),
    path('registrant-autocomplete/', RegistrantAutocomplete.as_view(), name='registrant-autocomplete'),
    path('workplace-autocomplete/', WorkplaceAutocomplete.as_view(), name='workplace-autocomplete'),
    path('workplace-all-autocomplete/', WorkplaceAllAutocomplete.as_view(), name='workplace-all-autocomplete'),
    re_path(r"^ckeditor/upload/", login_required(ckeditor_views.upload), name="ckeditor_upload"),
    re_path(r"^ckeditor/browse/", never_cache(login_required(ckeditor_views.browse)), name="ckeditor_browse"),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    
]
