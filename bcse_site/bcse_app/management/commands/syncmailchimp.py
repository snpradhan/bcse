from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from bcse_app import views

class Command(BaseCommand):

    def handle(self, *args, **options):
        users = User.objects.all()
        for user in users:
            userDetails = {'email_address': user.email.lower(), 'first_name':  user.first_name, 'last_name':  user.last_name}
            if user.userProfile.phone_number:
                userDetails['phone_number'] = user.userProfile.phone_number

            if user.userProfile.subscribe:
                views.subscription(userDetails, 'add')
            else:
                views.subscription(userDetails, 'delete')

            if user.userProfile.secondary_email:
                userSecondaryDetails = {'email_address': user.userProfile.secondary_email.lower(), 'first_name':  user.first_name, 'last_name':  user.last_name}
                if user.userProfile.phone_number:
                    userSecondaryDetails['phone_number'] = user.userProfile.phone_number

                if user.userProfile.subscribe:
                    views.subscription(userSecondaryDetails, 'add')
                else:
                    views.subscription(userSecondaryDetails, 'delete')
