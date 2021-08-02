from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _
from sort_order_field import SortOrderField

import uuid


class Matcher(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    calendar_id = models.CharField(
        max_length=64, help_text=("Google Calendar's calendar identifier")
        )
    list_id = models.CharField(
        max_length=64, help_text=("Clickup list identifier")
        )
    tag_name = models.CharField(
        max_length=64,
        help_text=("Clickup tag name that will be added to matched events")
        )
    name_regex = models.CharField(
        max_length=1024,
        help_text=(
            '''Regular expression that will be used with the event name
            in order to decide if a calendar event should be synced with a
            clickup task'''
            )
        )
    description_regex = models.CharField(
        max_length=1024,
        help_text=(
            '''Regular expression that will be used with the event description
            in order to decide if a calendar event should be synced with a
            clickup task'''
            )
        )
    order = SortOrderField(_("Order"))

    class Meta:
        ordering = ('order', 'user__username')
        unique_together = [['user', 'list_id']]


class GoogleCalendarWebhook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    calendar_id = models.CharField(
        max_length=64, help_text=("Google Calendar's calendar identifier")
        )
    channel_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
        )
    resource_id = models.CharField(max_length=256, editable=False)

    # TODO send watch on creation

    # TODO send stop on delete


class ClickupWebhook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    webhook_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
        )

    # TODO create webhook on creation

    # TODO delete webhook on delete


# Constants for the sync_description field
SYNC_GOOGLE_CALENDAR_DESCRIPTION = True
SYNC_CLICKUP_DESCRIPTION = False


class SyncedEvent(models.Model):
    task_id = models.CharField(max_length=64, primary_key=True)
    event_id = models.CharField(max_length=64)
    end_time = models.DateTimeField()
    sync_description = models.BooleanField(null=True)
