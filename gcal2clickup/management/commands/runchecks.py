from django.urls import reverse
from django.core.management.base import BaseCommand, CommandError
from gcal2clickup.models import ClickupUser, ClickupWebhook, GoogleCalendarWebhook, SyncedEvent
from app.settings import DOMAIN

import logging

logger = logging.getLogger('gcal2clikup')

class Command(BaseCommand):
    def handle(self, *args, **options):
        # TODO Save every Clickup user in order to check the webhooks

        # Remove all webhooks that point to the app that are not saved
        endpoint = f'{DOMAIN}{reverse("clickup_endpoint")}'
        deleted = 0
        for cu in ClickupUser.objects.all():
            for team in cu.api.list_teams():
                for w in cu.api.list_webhooks(teams=[team]):
                    if w['endpoint'] == endpoint:
                        try:
                            cw = ClickupWebhook.objects.get(webhook_id=w['id'])
                            if w['health']['status'] != 'active':
                                cw.delete()
                                deleted += 1
                        except ClickupWebhook.DoesNotExist:
                            cu.api.delete_webhook(w)
                            deleted += 1
            logger.info(f'Deleted {deleted} clickup webhooks from {cu.username}')
            cu.save()

        # TODO create and assign GoogleCalendarWebhooks about to expire
        # TODO delete not related GoogleCalendarWebhooks

        # TODO set status of finished synced events to "closed" and delete them
        # TODO set status of started synced events to "active"
        pass