from django.core.management.base import BaseCommand, CommandError
from gcal2clickup.models import ClickupUser, GoogleCalendarWebhook, SyncedEvent


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Save every Clickup user in order to check the webhooks

        # TODO create and assign GoogleCalendarWebhooks about to expire
        # TODO delete not related GoogleCalendarWebhooks
        
        # TODO set status of finished synced events to "closed" and delete them
        # TODO set status of started synced events to "active"
        pass