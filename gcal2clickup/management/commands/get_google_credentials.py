from django.core.management.base import BaseCommand, CommandError
from gcal2clickup.gcal import GoogleCalendar

class Command(BaseCommand):

    def handle(self, *args, **options):
        print(GoogleCalendar.get_credentials())
