from django.core.management.base import BaseCommand, CommandError
from gcal2clickup.gcal import Gcal

class Command(BaseCommand):

    def handle(self, *args, **options):
        print(Gcal.get_credentials())
