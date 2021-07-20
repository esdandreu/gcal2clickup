from django.contrib.auth.models import User
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    def handle(self, *args, **options):
        for user in User.objects.filter(
            is_superuser=False, is_active=True, is_staff=True
            ):
            gcal = user.profile.google_calendar
            print(gcal)
            calendars = gcal.calendar_list
            print(calendars)
