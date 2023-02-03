from django.core.management.base import BaseCommand
from django.contrib.auth.models import User

class Command(BaseCommand):

    def handle(self, *args, **options):
        users = User.objects.all().exclude(userProfile__user_role__in=['A', 'S'])
        for user in users:
            user.email = 'user%s@email.com'% user.userProfile.id
            user.save()
