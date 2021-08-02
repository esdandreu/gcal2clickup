from django.db import models
from django.urls import reverse
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models.signals import pre_delete
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _

from sort_order_field import SortOrderField

from app.settings import DOMAIN

from datetime import datetime

import uuid


class GoogleCalendarWebhook(models.Model):
    channel_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
        )
    resource_id = models.CharField(max_length=256, editable=False)
    expiration = models.DateTimeField()

    @classmethod
    def create(
        cls,
        user: 'User',
        calendarId: str,
        ) -> 'GoogleCalendarWebhook':
        channel_id = str(uuid.uuid4())
        response = user.profile.google_calendar.add_events_watch(
            calendarId=calendarId,
            id=channel_id,
            address=f'{DOMAIN}{reverse("google_calendar_endpoint")}',
            )
        expiration = datetime.fromtimestamp(int(response['expiration'])/1000)
        return cls(
            channel_id=response['id'],
            resource_id=response['resourceId'],
            expiration=expiration,
            )

    def refresh(self):
        print(self.matcher.user)


@receiver(pre_delete, sender=GoogleCalendarWebhook)
def stop_google_calendar_webhook(sender, instance, **kwargs):
    print('Deleting a GCAL webhook!!')
    instance.matcher.user.profile.google_calendar.stop_watch(
        id=instance.channel_id, resourceId=instance.resource_id
        )


class ClickupWebhook(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    webhook_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
        )

    # TODO create webhook on creation

    # TODO delete webhook on delete


# Constants for the sync_description field
SYNC_GOOGLE_CALENDAR_DESCRIPTION = True
SYNC_CLICKUP_DESCRIPTION = False


class Matcher(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    google_calendar_webhook = models.ForeignKey(
        GoogleCalendarWebhook, on_delete=models.CASCADE, editable=False
        )
    calendar_id = models.CharField(
        max_length=64, help_text=("Google Calendar's calendar identifier")
        )
    list_id = models.CharField(
        max_length=64, help_text=("Clickup list identifier")
        )
    tag_name = models.CharField(
        max_length=64,
        blank=True,
        help_text=("Clickup tag name that will be added to matched events")
        )
    name_regex = models.CharField(
        max_length=1024,
        blank=True,
        help_text=(
            '''Regular expression that will be used with the event name
            in order to decide if a calendar event should be synced with a
            clickup task'''
            )
        )
    description_regex = models.CharField(
        max_length=1024,
        blank=True,
        help_text=(
            '''Regular expression that will be used with the event description
            in order to decide if a calendar event should be synced with a
            clickup task'''
            )
        )
    order = SortOrderField(_("Order"))

    class Meta:
        ordering = ('user__username', 'order')
        unique_together = [['user', 'list_id']]

    def clean(self):
        """
        Require at least one regex
        """
        if not (self.name_regex or self.description_regex):
            raise ValidationError(
                "A name or description regular expression is required"
                )

    def save(self, *args, **kwargs):
        if not getattr(self, 'google_calendar_webhook', None):
            self.google_calendar_webhook = GoogleCalendarWebhook.create(
                user=self.user, calendarId=self.calendar_id
                )
            self.google_calendar_webhook.save()
        super(Matcher, self).save(*args, **kwargs)


class SyncedEvent(models.Model):
    matcher = models.ForeignKey(Matcher, on_delete=models.CASCADE)
    task_id = models.CharField(max_length=64, primary_key=True)
    event_id = models.CharField(max_length=64)
    end_time = models.DateTimeField()
    sync_description = models.BooleanField(null=True)
