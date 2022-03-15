from django.urls import path

from . import views

app_name = 'bcse'

urlpatterns = [
    path('', views.home, name='home'),
    path('reservation/<int:id>/edit', views.reservationEdit, name='reservationEdit'),
    path('reservation/<int:id>/view', views.reservationView, name='reservationView'),
    path('reservation/new', views.reservationEdit, name='reservationNew'),
    path('reservations', views.reservations, name='reservations'),
    path('workshop/<int:id>/edit', views.workshopEdit, name='workshopEdit'),
    path('workshop/<int:id>/view', views.workshopView, name='workshopView'),
    path('workshop/<int:id>/delete', views.workshopDelete, name='workshopDelete'),
    path('workshopCategory/<int:id>', views.workshopCategory, name='workshopCategory'),
    path('workshopCategory/new', views.workshopCategory, name='workshopCategoryNew'),
    path('workshop/new', views.workshopEdit, name='workshopNew'),
    path('workshops/<str:flag>', views.workshops, name='workshops'),
    path('workshop/<int:id>/registration_setting/edit', views.workshopRegistrationSetting, name='workshopRegistrationSetting'),
    path('workshop/<int:id>/registrants/', views.workshopRegistrants, name='workshopRegistrants'),
    path('workshop/<int:workshop_id>/registration/', views.workshopRegistration, name='workshopRegistration'),
    path('workshop/<int:workshop_id>/registration/<int:id>/edit', views.workshopRegistrationEdit, name='workshopRegistrationEdit'),
    path('workshop/<int:workshop_id>/registration/<int:id>/delete', views.workshopRegistrationDelete, name='workshopRegistrationDelete'),
    path('signin/', views.userSignin, name='signin'),
    path('signin_redirect/', views.signinRedirect, name='signinRedirect'),
    path('signin/<str:user_name>/', views.userSignin, name='signin'),
    path('signup/', views.userSignup, name='signup'),
    path('signout/', views.userSignout, name='signout'),
    path('userProfile/<int:id>/edit', views.userProfileEdit, name='userProfileEdit'),
    path('userProfile/<int:id>/view', views.userProfileView, name='userProfileView'),
    path('adminConfiguration/', views.adminConfiguration, name='adminConfiguration'),
    path('workshopCategories/', views.workshopCategories, name='workshopCategories'),
]
