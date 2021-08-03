from typing import Tuple

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
import re


class GoogleCalendarWebhook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    calendar_id = models.CharField(max_length=256, unique=True)
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
        expiration = datetime.fromtimestamp(int(response['expiration']) / 1000)
        return cls(
            user=user,
            calendar_id=calendarId,
            channel_id=response['id'],
            resource_id=response['resourceId'],
            expiration=expiration,
            )

    def refresh(self):
        print(self.matcher.user)

    def check_events(self) -> Tuple[int, int]:
        # Check all the related matchers
        google_calendar = self.user.profile.google_calendar
        matchers = self.matcher_set.order_by('order')
        check_since = matchers.earliest(
            'google_calendar_checked_at'
            ).google_calendar_checked_at
        if not check_since:
            kwargs = {'timeMin': datetime.utcnow().isoformat("T") + "Z"}
        else:
            kwargs = {'updateMin': check_since.isoformat("T") + "Z"}
        print(kwargs)

        for event in google_calendar.list_events(
            calendarId=self.calendar_id, **kwargs
            ):
            try:
                synced_event = SyncedEvent.objects.get(event_id=event['id'])
                synced_event.update_event(event)
            except SyncedEvent.DoesNotExist:
                match, matcher = matchers.match(event=event)
                if match:
                    SyncedEvent.create(matcher, match, event=event)
        # TODO set matchers google_calendar_checked_at to now


@receiver(pre_delete, sender=GoogleCalendarWebhook)
def stop_google_calendar_webhook(sender, instance, **kwargs):
    print('Deleting a GCAL webhook!!')
    instance.user.profile.google_calendar.stop_watch(
        id=instance.channel_id, resourceId=instance.resource_id
        )


class ClickupWebhook(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    webhook_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
        )

    # TODO create webhook on creation

    # TODO delete webhook on delete


class MatcherQuerySet(models.QuerySet):
    def match(self, **kwargs) -> Tuple[re.Match, 'Matcher']:
        for matcher in self:
            match = matcher.match(**kwargs)
            if match:
                return match, matcher
        return None, None


class MatcherManager(models.Manager):
    def get_queryset(self):
        return MatcherQuerySet(self.model, using=self._db)


# Constants for the sync_description field
SYNC_GOOGLE_CALENDAR_DESCRIPTION = True
SYNC_CLICKUP_DESCRIPTION = False


class Matcher(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    google_calendar_webhook = models.ForeignKey(
        GoogleCalendarWebhook, on_delete=models.CASCADE, editable=False
        )
    # ! Not necessary in model, could be passed by the form and then retrieved
    # ! from the google_calendar_webhook
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
    _name_regex = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=(
            '''Regular expression that will be used with the event name
            in order to decide if a calendar event should be synced with a
            clickup task'''
            )
        )
    _description_regex = models.CharField(
        max_length=1024,
        blank=True,
        null=True,
        help_text=(
            '''Regular expression that will be used with the event description
            in order to decide if a calendar event should be synced with a
            clickup task'''
            ),
        )
    order = SortOrderField(_("Order"))
    google_calendar_checked_at = models.DateTimeField(
        blank=True,
        null=True,
        help_text=(
            '''Last time that the given calendar has been checked for
            updated events'''
            )
        )
    objects = MatcherManager()

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
            # get_or_create with a custom create method
            try:
                self.google_calendar_webhook = GoogleCalendarWebhook.objects.get(
                    calendar_id=self.calendar_id
                    )
            except GoogleCalendarWebhook.DoesNotExist:
                self.google_calendar_webhook = GoogleCalendarWebhook.create(
                    user=self.user, calendarId=self.calendar_id
                    )
            self.google_calendar_webhook.save()
        super(Matcher, self).save(*args, **kwargs)

    @property
    def name_regex(self):
        return re.compile(
            self._name_regex
            ) if self._name_regex else None

    @property
    def description_regex(self):
        return re.compile(
            self._description_regex, re.MULTILINE
            ) if self._description_regex else None

    def match(self, *, event: dict = None, task: dict = None) -> re.Match:
        if event and task is None:
            return self._match_event(event)
        elif task and event is None:
            return self._match_task(task)
        raise AttributeError(
            f'''Either "event" or "task" must be a non empty dictionary.
            event={event}
            task={task}'''
            )

    def _match_event(self, event: dict) -> re.Match:
        match = None
        name = event['summary']
        if name and self.name_regex:
            match = self.name_regex.search(name)
        if not match:
            description = event.get('description', None)
            if description and self.description_regex:
                match = self.description_regex.search(description)
        return match

    def _match_task(self, task: dict) -> re.Match:
        raise NotImplementedError


class SyncedEvent(models.Model):
    matcher = models.ForeignKey(Matcher, on_delete=models.CASCADE)
    task_id = models.CharField(max_length=64, primary_key=True)
    event_id = models.CharField(max_length=64)
    end_time = models.DateTimeField()
    sync_description = models.BooleanField(null=True)

    @property
    def event(self):
        return self.matcher.user.profile.google_calendar.events.get(
            calendarId=self.matcher.google_calendar_webhook.calendar_id,
            eventId=self.event_id,
            ).execute()

    def update_task(self, event=None):
        if event is None:
            event = self.event
        raise NotImplementedError

    @classmethod
    def _create_task(self, event, match=None):
        print(event)
        raise NotImplementedError

    @classmethod
    def _create_event(self, task, match):
        raise NotImplementedError

    @classmethod
    def create(cls, matcher, match, *, event=None, task=None) -> 'SyncedEvent':
        if event and task is None:
            task_id = cls._create_task(event, match)
        elif task and event is None:
            event_id = cls._create_event(task, match)
        else:
            raise AttributeError(
                f'''Either "event" or "task" must be a non empty dictionary.
                But not both.
                event={event}
                task={task}'''
                )
        raise NotImplementedError
        return cls()
