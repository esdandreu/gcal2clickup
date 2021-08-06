from django.core.management.base import BaseCommand, CommandError
from admin_sso.models import Profile


class Command(BaseCommand):
    def handle(self, *args, **options):
        for profile in Profile.objects.filter(user__is_active=True):
            profile.refresh_gooogle_calendar_webhooks()