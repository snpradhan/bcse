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
from ckeditor_uploader import views as ckeditor_views
from django.contrib.auth.decorators import login_required
from django.views.decorators.cache import never_cache
from django.views.i18n import JavaScriptCatalog
from bcse_app.views import UserAutocomplete, RegistrantAutocomplete

urlpatterns = [
    path('', include('bcse_app.urls', namespace="bcse")),
    path('admin/', admin.site.urls),
    path('password_reset/', include('password_reset.urls')),
    path('user-autocomplete/', UserAutocomplete.as_view(), name='user-autocomplete'),
    path('registrant-autocomplete/', RegistrantAutocomplete.as_view(), name='registrant-autocomplete'),
    re_path(r"^ckeditor/upload/", login_required(ckeditor_views.upload), name="ckeditor_upload"),
    re_path(r"^ckeditor/browse/", never_cache(login_required(ckeditor_views.browse)), name="ckeditor_browse"),
    path('jsi18n/', JavaScriptCatalog.as_view(), name='javascript-catalog'),
    
]
