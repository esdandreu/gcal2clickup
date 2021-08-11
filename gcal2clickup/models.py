from typing import Tuple

from django.db import models
from django.urls import reverse
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.utils.timezone import make_aware
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import pre_delete, post_delete

from app.settings import DOMAIN, SYNCED_TASK_TAG
from gcal2clickup.clickup import Clickup

from datetime import datetime
from markdownify import markdownify
from sort_order_field import SortOrderField

import logging
import uuid
import pytz
import re

logger = logging.getLogger('django')


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
        expiration = make_aware(
            datetime.fromtimestamp(int(response['expiration']) / 1000)
            )
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
                    synced_event.delete(with_task=True)
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
    webhook_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
        )
    clickup_user = models.ForeignKey('ClickupUser', on_delete=models.CASCADE)
    team_id = models.PositiveIntegerField()
    _team = None

    @property
    def team(self):
        if self._team is None:
            for team in self.clickup_user.api.list_teams():
                if int(team['id']) == self.team_id:
                    self._team = team['name']
                    break
            else:
                self.delete()
                return 'Deleted! Please refresh'
        return self._team

    @classmethod
    def create(
        cls,
        clickup_user: 'ClickupUser',
        team: dict,
        endpoint: str = None,
        ) -> 'ClickupWebhook':
        if endpoint is None:
            endpoint = f'{DOMAIN}{reverse("clickup_endpoint")}'
        webhook_id = clickup_user.api.create_webhook(
            team=team, endpoint=endpoint
            )['id']
        return cls(
            webhook_id=webhook_id,
            clickup_user=clickup_user,
            team_id=team['id']
            )

    def check_task(self, task_id: str):
        return self.clickup_user.check_task(task_id)

    @staticmethod
    def is_sync_tag_added(history_items: list) -> bool:
        for i in history_items:
            if i['field'] == 'tag':
                for tag in i['after']:
                    if tag['name'] == SYNCED_TASK_TAG:
                        return True
        return False


@receiver(pre_delete, sender=ClickupWebhook)
def delete_clickup_webhook(sender, instance, **kwargs):
    instance.clickup_user.api.delete_webhook({'id': instance.webhook_id})


class ClickupUserQuerySet(models.QuerySet):
    def check_webhooks(self, *args, **kwargs) -> int:
        created = 0
        for cu in self:
            _created = cu.check_webhooks(*args, **kwargs)
            logger.info(
                f'Created {created} clickup webhooks for {cu.username}'
                )
            created += _created
        return created


class ClickupUserManager(models.Manager):
    def get_queryset(self):
        return ClickupUserQuerySet(self.model, using=self._db)


class ClickupUser(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    id = models.PositiveIntegerField(primary_key=True, editable=False)
    # TODO Validate always starts with pk
    token = models.CharField(
        blank=True,
        max_length=255,
        verbose_name='Clickup personal API key',
        help_text='''Check <a
            href=https://docs.clickup.com/en/articles/1367130-getting-started-with-the-clickup-api#personal-api-key>
            how to find the personal API key</a>''',
        )
    objects = ClickupUserManager()
    _api = None
    _username = None

    def __str__(self):
        return self.username

    @property
    def api(self):
        if self._api is None:
            self._api = Clickup(token=self.token)
        return self._api

    @property
    def username(self):
        if self._username is None:
            self._username = self.api.user['username']
        return self._username

    @property
    def list_choices(self):
        return [(
            str(self.pk) + ',' + l['id'],
            self.username + ': ' + self.api.repr_list(l)
            ) for l in self.api.list_lists()]

    def create_webhook(self, team: dict, endpoint: str = None):
        return ClickupWebhook.create(
            clickup_user=self, team=team, endpoint=endpoint
            )
        
    def remove_sync_tag(self, task_id: str):
        logger.debug(f'Removing sync tag from {task_id}')
        return self.api.delete(f'task/{task_id}/tag/{SYNCED_TASK_TAG}')

    def check_webhooks(self) -> int:
        created = 0
        webhooks = ClickupWebhook.objects.filter(clickup_user=self)
        # Ensure there is a webhook for every team
        for team in self.api.list_teams():
            try:
                w = webhooks.get(team_id=team['id'])
            except ClickupWebhook.DoesNotExist:
                w = self.create_webhook(team=team)
                w.save()
                created += 1
            webhooks = webhooks.exclude(pk=w.pk)
        # Delete extra webhooks (not usual)
        for webhook in webhooks:
            webhook.delete()
        return created

    def check_task(self, task_id: str) -> bool:
        task = self.api.get(f'task/{task_id}')
        # Is task valid?
        if all([SYNCED_TASK_TAG in task.get('tags', []),
                task.get('due_date')]):
            match, matcher = self.matcher_set.order_by('order').match(
                task=task
                )
            if match:
                SyncedEvent.create(matcher, match, task=task).save()
                return True
        self.remove_sync_tag(task_id)
        return False

    def save(self, *args, **kwargs):
        # Add the clickup user id
        self.id = self.api.user['id']
        super().save(*args, **kwargs)
        # Check webhooks
        created = self.check_webhooks()
        logger.info(f'Created {created} clickup webhooks for {self.username}')
        # Enforce permissions check by saving the user
        self.user.save()


@receiver(post_delete, sender=ClickupUser)
def refresh_user(sender, instance, **kwargs):
    instance.user.save()


class MatcherQuerySet(models.QuerySet):
    def match(self, **kwargs) -> Tuple[re.Match, 'Matcher']:
        for matcher in self:
            match = matcher.match(**kwargs)
            if match:
                return match, matcher
        return None, None

    @property
    def google_calendar_webhooks(self):
        return set(m.google_calendar_webhook for m in self)


class MatcherManager(models.Manager):
    def get_queryset(self):
        return MatcherQuerySet(self.model, using=self._db)


class Matcher(models.Model):

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    google_calendar_webhook = models.ForeignKey(
        GoogleCalendarWebhook, on_delete=models.CASCADE, editable=False
        )
    clickup_user = models.ForeignKey(
        ClickupUser, on_delete=models.CASCADE, editable=False
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
        return [s.strip() for s in self._tags.split(',')] if self._tags else []

    @property
    def name_regex(self):
        return re.compile(self._name_regex) if self._name_regex else None

    @property
    def calendar_id(self):
        return self.google_calendar_webhook.calendar_id

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

    def _match_task(self, task: dict) -> bool:
        return task.get('list', {}).get('id', None) == self.list_id

    def _create_task(
        self,
        event: dict,
        match: re.Match = None,
        ) -> Tuple[dict, datetime, datetime]:
        logger.debug(f'Creating task from event {event["summary"]}')
        data = {
            'name': event['summary'],
            'tags': [SYNCED_TASK_TAG] + self.tags,
            }
        if 'description' in event:
            data['markdown_description'] = markdownify(event['description'])
        (start_date, due_date, all_day) = \
            self.user.profile.google_calendar.event_bounds(event)
        task = self.clickup_user.api.create_task(
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
        logger.debug(f'Creating event from task {task["name"]}')
        print(task)
        end_time = datetime.fromtimestamp(int(task['due_date']) / 1000)
        end_time = pytz.utc.localize(end_time)
        # if end_date.
        if not task.get('start_date', None):
            start_time = end_time
        else:
            start_time = datetime.fromtimestamp(int(task['start_date']) / 1000)
            start_time = pytz.utc.localize(start_time)
        kwargs = {}
        if task['description']:
            kwargs['description'] = task['description']
        return self.user.profile.google_calendar.create_event(
            calendarId=self.calendar_id,
            summary=task['name'],
            end_time=end_time,
            start_time=start_time,
            **kwargs,
            )


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
            calendarId=self.matcher.calendar_id,
            eventId=self.event_id,
            ).execute()

    @property
    def task(self):
        return self.matcher.clickup_user.api.get(f'task/{self.task_id}')

    def update_task(self, event: dict = None) -> dict:
        if event is None:
            event = self.event
        logger.debug(f'Updating task from event {event["summary"]}')
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
        task = self.matcher.clickup_user.api.update_task(
            task_id=self.task_id,
            start_date=start_date,
            due_date=due_date,
            all_day=all_day,
            **data
            )
        self.start = start_date
        self.end = due_date
        return task

    def update_event(self, history_items: list):
        print(history_items)
        kwargs = {}
        for i in history_items:
            field = i['field']
            if field == 'name':
                kwargs['summary'] = i['after']
            elif field == 'description':
                if self.sync_description is SYNC_CLICKUP_DESCRIPTION:
                    kwargs['description'] = self.task['description']
                else:
                    self.sync_description = None
            elif field in ['due_date', 'start_date']:
                # * This is UTC
                date = datetime.fromtimestamp(int(i['after']) / 1000)
                date = pytz.utc.localize(date)
                if i['data'][f'{field}_time']:
                    date = date.date()
                if field == 'due_date':
                    kwargs['end_date'] = date
                else:
                    kwargs['start_date'] = date
        return self.matcher.user.profile.google_calendar.update_event(
            calendarId=self.matcher.calendar_id,
            eventId=self.event_id,
            **kwargs,
            )

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

    def delete_task(self) -> dict:
        return self.matcher.clickup_user.api.delete_task(task_id=self.task_id)

    def delete_event(self) -> dict:
        return self.matcher.user.profile.google_calendar.events.delete(
            calendarId=self.matcher.calendar_id, eventId=self.event_id
            ).execute()

    def delete(self, *args, with_task=False, with_event=False, **kwargs):
        super().delete(*args, **kwargs)
        if with_task:
            self.delete_task()
        if with_event:
            self.delete_event()