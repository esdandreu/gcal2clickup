from typing import Tuple

from django.db import models
from django.urls import reverse
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils.timezone import make_aware
from django.db.models.signals import pre_delete
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from app.settings import DOMAIN

from sort_order_field import SortOrderField
from datetime import datetime
from markdownify import markdownify

import logging
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
    checked_at = models.DateTimeField(
        null=True,
        editable=False,
        help_text=(
            '''Last time that the given calendar has been checked for
            updated events'''
            ),
        )

    def __str__(self):
        return self.calendar[1]

    @property
    def calendar(self) -> Tuple[str, str]:  # (name, id)
        name = self.user.profile.google_calendar.calendars.get(
            calendarId=self.calendar_id
            ).execute()['summary']
        return (self.calendar_id, name)

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
        # TODO check if it is expired and create new if needed
        print(self.user)

    def check_events(self) -> Tuple[int, int]:  # (created, updated)
        # Check all the related matchers
        google_calendar = self.user.profile.google_calendar
        matchers = self.matcher_set.order_by('order')
        if not self.checked_at:
            kwargs = {
                'timeMin': datetime.utcnow().isoformat('T') + 'Z',
                'singleEvents': True,
                }
        else:
            kwargs = {
                'updatedMin': self.checked_at.isoformat('T'),
                'orderBy': 'updated',
                }
        kwargs['showDeleted'] = True
        created = 0
        updated = 0
        deleted = 0
        for event in google_calendar.list_events(
            calendarId=self.calendar_id, **kwargs
            ):
            try:
                synced_event = SyncedEvent.objects.get(event_id=event['id'])
                if event['status'] == 'cancelled':
                    synced_event.delete_task()
                    synced_event.delete()
                    deleted += 1
                else:
                    synced_event.update_task(event)
                    synced_event.save()
                    updated += 1
            except SyncedEvent.DoesNotExist:
                # Create a new synced event on confirmed events that match
                if event['status'] != 'cancelled':
                    match, matcher = matchers.match(event=event)
                    if match:
                        SyncedEvent.create(matcher, match, event=event).save()
                        created += 1
        self.checked_at = make_aware(datetime.utcnow())
        self.save()
        return (created, updated)


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
            # address=f'{DOMAIN}{reverse("google_calendar_endpoint")}',

    def refresh(self):
        # TODO check if it is expired and create new if needed
        print(self.user)


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


class Matcher(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    google_calendar_webhook = models.ForeignKey(
        GoogleCalendarWebhook, on_delete=models.CASCADE, editable=False
        )
    list_id = models.CharField(max_length=64, help_text=('Clickup list.'))
    _tags = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        help_text=(
            '''Clickup tag name that will be added to matched events.
            One can add more than one tag by separating them with commas'''
            )
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
        # Reset the checks when modified
        self.google_calendar_webhook.checked_at = None
        self.google_calendar_webhook.save()
        super().save(*args, **kwargs)

    @property
    def tags(self):
        print(self._tags)
        return [s.strip() for s in self._tags.split(',')] if self._tags else []

    @property
    def name_regex(self):
        return re.compile(self._name_regex) if self._name_regex else None

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

    def _create_task(
        self,
        event: dict,
        match: re.Match = None,
        ) -> Tuple[dict, datetime, datetime]:
        logging.debug(f'Creating task from event {event["summary"]}')
        data = {
            'name': event['summary'],
            'tags': ['google_calendar'] + self.tags,
            }
        print(data)
        if 'description' in event:
            data['markdown_description'] = markdownify(event['description'])
        (start_date, due_date, all_day) = \
            self.user.profile.google_calendar.event_bounds(event)
        task = self.user.profile.clickup.create_task(
            list_id=self.list_id,
            start_date=start_date,
            due_date=due_date,
            all_day=all_day,
            **data
            )
        return (task, start_date, due_date)

    def _create_event(
        self,
        task: dict,
        match: re.Match = None,
        ) -> Tuple[dict, datetime, datetime]:
        logging.debug(f'Creating event from task {task["name"]}')
        raise NotImplementedError


# Constants for the sync_description field
SYNC_GOOGLE_CALENDAR_DESCRIPTION = True
SYNC_CLICKUP_DESCRIPTION = False


class SyncedEvent(models.Model):
    matcher = models.ForeignKey(Matcher, on_delete=models.CASCADE)
    task_id = models.CharField(
        max_length=64, primary_key=True, null=False, blank=False
        )
    event_id = models.CharField(max_length=64, null=False, blank=False)
    start = models.DateTimeField()
    end = models.DateTimeField()
    sync_description = models.BooleanField(null=True)

    @property
    def event(self):
        return self.matcher.user.profile.google_calendar.events.get(
            calendarId=self.matcher.google_calendar_webhook.calendar_id,
            eventId=self.event_id,
            ).execute()

    def update_task(self, event: dict = None) -> dict:
        if event is None:
            event = self.event
        logging.debug(f'Updating task from event {event["summary"]}')
        data = {'name': event['summary']}
        if self.sync_description is SYNC_GOOGLE_CALENDAR_DESCRIPTION:
            if 'description' in event:
                data['markdown_description'] = markdownify(
                    event['description']
                    )
        else:
            self.sync_description = None
        (start_date, due_date, all_day) = \
            self.matcher.user.profile.google_calendar.event_bounds(event)
        task = self.matcher.user.profile.clickup.update_task(
            task_id=self.task_id,
            start_date=start_date,
            due_date=due_date,
            all_day=all_day,
            **data
            )
        self.start = start_date
        self.end = due_date
        return task

    def delete_task(self) -> dict:
        return self.matcher.user.profile.clickup.delete_task(
            task_id=self.task_id
            )

    def update_event(self, task=None):
        if task is None:
            task = self.task
        print(task)
        logging.debug(f'Updating event from task {task["name"]}')
        raise NotImplementedError

    @classmethod
    def create(cls, matcher, match, *, event=None, task=None) -> 'SyncedEvent':
        if event and task is None:
            (task, start, end) = matcher._create_task(event, match)
            task_id = task['id']
            event_id = event['id']
            sync_description = SYNC_GOOGLE_CALENDAR_DESCRIPTION
        elif task and event is None:
            (event, start, end) = matcher._create_event(task, match)
            event_id = event['id']
            task_id = task['id']
            sync_description = SYNC_CLICKUP_DESCRIPTION
        else:
            raise AttributeError(
                f'''Either "event" or "task" must be a non empty dictionary.
                But not both.
                event={event}
                task={task}'''
                )
        return cls(
            matcher=matcher,
            task_id=task_id,
            event_id=event_id,
            start=start,
            end=end,
            sync_description=sync_description,
            )
