from django.urls import path

from . import views

app_name = 'bcse'

urlpatterns = [
    path('', views.home, name='home'),
    path('reservation/<int:id>', views.reservation, name='reservation'),
    path('reservation/new', views.reservation, name='newReservation'),
    path('reservations', views.reservations, name='reservations'),
    path('workshop/<int:id>', views.workshop, name='workshop'),
    path('workshop/new', views.workshop, name='newWorkshop'),
    path('workshops', views.workshops, name='workshops'),
    path('workshop_registration_setting/<int:id>', views.workshop_registration_setting, name='workshop_registration_setting'),
    path('workshop_registrants/<int:id>', views.workshop_registrants, name='workshop_registrants'),

]
