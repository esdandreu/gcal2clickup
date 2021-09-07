from datetime import datetime, timedelta, timezone
from django.urls import reverse
from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth.models import User

from gcal2clickup.models import (
    ClickupUser, ClickupWebhook, GoogleCalendarWebhook, Matcher, SyncedEvent
    )
from app.settings import DOMAIN

import logging

logger = logging.getLogger('gcal2clikup')

EXPIRATION_GAP = timedelta(days=1)
END_GAP = timedelta(days=1)


class Command(BaseCommand):
    def handle(self, *args, **options):
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
            logger.info(
                f'Deleted {deleted} clickup webhooks from {cu.username}'
                )
            cu.save()

        # Refresh Google Calendar webhooks about to expire
        refreshed = 0
        for w in GoogleCalendarWebhook.objects.filter(
            expiration__lte=datetime.now(timezone.utc) + EXPIRATION_GAP
            ):
            w = w.refresh()
            w.save()
            refreshed += 1
        logger.info(f'Refreshed {refreshed} google calendar webhooks')

        # Delete not related GoogleCalendarWebhooks
        GoogleCalendarWebhook.objects.filter(matcher=None).delete()

        # Check Google Calendar webhooks
        for obj in GoogleCalendarWebhook.objects.all():
            (created, updated) = obj.check_events()
            logger.info(
                f'''Checked {obj}: Created {created} synced events, updated
                {updated} existing ones'''
                )

        # ? set status of started synced events to "active"

        # Stop syncing finished events
        deleted = 0
        for e in SyncedEvent.objects.filter(
            end__lte=datetime.now(timezone.utc) - END_GAP
            ):
            e.delete()
            deleted += 1
        logger.info(f'Stopped syncing {deleted} events')
        # ? set status of finished synced events to "closed"
