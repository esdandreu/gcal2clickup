from typing import Set, Tuple, List, Optional, Any

from django.db import models
from django.urls import reverse
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.translation import ugettext_lazy as _
from django.db.models.signals import pre_delete, post_delete

from app.settings import DOMAIN, SYNCED_TASK_TAG
from gcal2clickup.clickup import Clickup, DATE_ONLY_TIME
from gcal2clickup.utils import make_aware_datetime
from gcal2clickup.validators import validate_is_clickup_token, validate_is_pattern

from datetime import datetime, date, timezone
from markdownify import markdownify
from sort_order_field import SortOrderField

import logging
import uuid
import pytz
import re

logger = logging.getLogger('gcal2clikup')


class GoogleCalendarWebhook(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    calendar_id = models.CharField(max_length=256)
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

    class Meta:
        unique_together = [['user', 'calendar_id']]

    def __str__(self):
        return self.calendar[1]

    @property
    def google_calendar(self):
        return self.user.profile.google_calendar

    @property
    def calendar(self) -> Tuple[str, str]:  # (id, name)
        name = self.google_calendar.calendars.get(calendarId=self.calendar_id
                                                  ).execute()['summary']
        return (self.calendar_id, name)

    @classmethod
    def create(
        cls,
        user: 'User',
        calendarId: str,
        ) -> 'GoogleCalendarWebhook':
        response = user.profile.google_calendar.add_events_watch(
            calendarId=calendarId,
            id=str(uuid.uuid4()),
            address=f'{DOMAIN}{reverse("google_calendar_endpoint")}',
            )
        expiration = make_aware_datetime(
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
        # Create new webhook
        new = self.create(user=self.user, calendarId=self.calendar_id)
        new.checked_at = self.checked_at
        new.matcher_set = self.matcher_set
        # Stop old webhook
        self.delete()
        return new

    def check_events(
        self,
        matchers: Optional[models.QuerySet['Matcher']] = None,
        ) -> Tuple[int, int]:  # (created, updated)
        created = 0
        updated = 0
        if matchers is None:
            matchers = self.matcher_set.order_by('order')
        # Build the query arguments
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
        # Query events and check them individually, storing some statistics
        for event in self.google_calendar.list_events(
            calendarId=self.calendar_id, **kwargs
            ):
            _created, _updated = self.check_event(event, matchers)
            created += _created
            updated += _updated
        # Update the check time
        self.checked_at = datetime.now(timezone.utc)
        self.save()
        return (created, updated)

    def check_event(
        self,
        event: dict,
        matchers: Optional[models.QuerySet['Matcher']] = None,
        ) -> Tuple[int, int]:  # (created, updated)
        created = 0
        updated = 0
        if matchers is None:
            matchers = self.matcher_set.order_by('order')
        try:
            synced_event = SyncedEvent.objects.get(event_id=event['id'])
            # Delete the task from a cancelled event
            if event['status'] == 'cancelled':
                # TODO if the description was changed in the task, remove
                # TODO sync, do not delete
                synced_event.delete(with_task=True)
            # Update the task when an event is updated, not created
            elif not self.google_calendar.is_new_event(event):
                synced_event.update_task_from_event(event)
                synced_event.save()
                updated += 1
        except SyncedEvent.DoesNotExist:
            # Create a new synced event on confirmed events that match
            if event['status'] != 'cancelled':
                match, matcher = matchers.match(event=event)
                if match:
                    SyncedEvent.create(matcher, match, event=event).save()
                    created += 1
        return (created, updated)


@receiver(pre_delete, sender=GoogleCalendarWebhook)
def stop_google_calendar_webhook(sender, instance, **kwargs):
    try:
        instance.user.profile.google_calendar.stop_watch(
            id=instance.channel_id, resourceId=instance.resource_id
            )
    except Exception as e:
        # Avoid errors when the webhook is already deleted
        if 'not found for project' not in str(e):
            raise e


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
    token = models.CharField(
        blank=True,
        max_length=255,
        validators=[validate_is_clickup_token],
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
    def list_choices(
            self
        ) -> List[Tuple[str, str]]:  # ("cu_pk,list_id", "name")
        return [(
            str(self.pk) + ',' + l['id'],
            self.username + ': ' + self.api.repr_list(l)
            ) for l in self.api.list_lists()]

    def create_webhook(self, team: dict, endpoint: str = None):
        return ClickupWebhook.create(
            clickup_user=self, team=team, endpoint=endpoint
            )

    def remove_sync_tag(self, task_id: str):
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
        if not SYNCED_TASK_TAG in [t['name'] for t in task.get('tags', [])]:
            return False
        if not task.get('due_date', None):
            self.api.task_logger(
                'Due date must not be empty for calendar synchronization',
                task_id=task['id'],
                )
            self.remove_sync_tag(task_id)
            return False
        match, matcher = self.matcher_set.order_by('order').match(task=task)
        if match:
            SyncedEvent.create(matcher, match, task=task).save()
            return True
        self.api.task_logger(
            'List is not associated to any calendar',
            task_id=task['id'],
            )
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
        validators=[validate_is_pattern],
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
        validators=[validate_is_pattern],
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

    def clean(self):
        """
        Require at least one regex
        """
        if not (self._name_regex or self._description_regex):
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
    def calendar(self) -> Tuple[str, str]:  # (id, name)
        return self.google_calendar_webhook.calendar

    @property
    def clickup_list(self) -> Tuple[str, str]:  # (id, name)
        name = Clickup.repr_list(
            self.clickup_user.api.get(f'list/{self.list_id}')
            )
        return (self.list_id, name)

    @property
    def description_regex(self):
        return re.compile(
            self._description_regex, re.MULTILINE
            ) if self._description_regex else None

    def task_logger(self, text: str, task_id: str):
        return self.clickup_user.api.task_logger(text=text, task_id=task_id)

    def comment_task(self, task_id: str, **data):
        return self.clickup_user.api.comment_task(task_id=task_id, **data)

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
        name = event.get('summary', '')
        if name and self.name_regex:
            match = self.name_regex.search(name)
        if not match:
            description = event.get('description', None)
            if description and self.description_regex:
                match = self.description_regex.search(description)
        return match

    def _match_task(self, task: dict) -> bool:
        return task.get('list', {}).get('id', None) == self.list_id

    def _create_task(self, **data):
        return self.clickup_user.api.create_task(list_id=self.list_id, **data)

    def _create_task_from_event(
        self,
        event: dict,
        match: re.Match = None,
        ) -> Tuple[dict, datetime, datetime]:
        data = {
            'assignees': [self.clickup_user.id],
            'name': event.get('summary', '(No title)'),
            'tags': [SYNCED_TASK_TAG] + self.tags,
            }
        if 'description' in event:
            data['markdown_description'] = markdownify(event['description'])
        (start_date, due_date) = \
            self.user.profile.google_calendar.event_bounds(event)
        task = self._create_task(
            start_date=start_date, due_date=due_date, **data
            )
        self.comment_task(
            task_id=task['id'],
            comment=[
                {
                    'text': 'Task created from calendar event ',
                    'attributes': {}
                    },
                {
                    'text': data['name'],
                    'attributes': {
                        'link': event['htmlLink']
                        }
                    },
                ]
            )
        return (task, start_date, due_date)

    def _delete_task(self, task_id: str):
        return self.clickup_user.api.delete_task(task_id=task_id)

    def _create_event(self, start_time: datetime, end_time: datetime, **data):
        return self.user.profile.google_calendar.create_event(
            calendarId=self.calendar_id,
            end_time=end_time,
            start_time=start_time,
            **data,
            )

    def _create_event_from_task(
        self,
        task: dict,
        match: re.Match = None,
        ) -> Tuple[dict, datetime, datetime]:
        # Tasks must have due_date to be valid
        end_time = datetime.fromtimestamp(int(task['due_date']) / 1000)
        end_time = pytz.utc.localize(end_time)
        if end_time.time() == DATE_ONLY_TIME:  # Recognize whole day due dates
            end_time = end_time.date()
        if not task.get('start_date', None):  # Start date is not mandatory
            start_time = end_time
        else:
            start_time = datetime.fromtimestamp(int(task['start_date']) / 1000)
            start_time = pytz.utc.localize(start_time)
            if type(end_time) == date:  # Start must be the same format as end
                start_time = start_time.date()
            elif end_time == start_time:  # Recognize whole day dates
                end_time = end_time.date()
                start_time = start_time.date()
        data = {'summary': task['name']}
        if task['description']:
            data['description'] = task['description']
        try:
            event = self._create_event(
                end_time=end_time,
                start_time=start_time,
                **data,
                )
        except Exception as e:
            self.task_logger(
                f'Could not create calendar event from task: ' + str(e),
                task_id=task['id'],
                )
            raise e
        self.comment_task(
            task_id=task['id'],
            comment=[
                {
                    'text': 'Created calendar event ',
                    'attributes': {}
                    },
                {
                    'text': task['name'],
                    'attributes': {
                        'link': event['htmlLink']
                        }
                    },
                {
                    'text': ' from task',
                    'attributes': {}
                    },
                ]
            )
        return (
            event,
            make_aware_datetime(start_time),
            make_aware_datetime(end_time),
            )

    def _delete_event(self, event_id: str):
        return self.user.profile.google_calendar.delete_event(
            calendarId=self.calendar_id, eventId=event_id
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
    start = models.DateTimeField(null=False, blank=False)
    end = models.DateTimeField(null=False, blank=False)
    sync_description = models.BooleanField(
        null=True,
        choices=[
            (None, 'No'),
            (SYNC_GOOGLE_CALENDAR_DESCRIPTION, 'Google Calendar -> Clickup'),
            (SYNC_CLICKUP_DESCRIPTION, 'Clickup -> Google Calendar')
            ]
        )

    @property
    def event(self):
        return self.matcher.user.profile.google_calendar.events.get(
            calendarId=self.matcher.calendar_id,
            eventId=self.event_id,
            ).execute()

    @property
    def task(self):
        return self.matcher.clickup_user.api.get(f'task/{self.task_id}')

    def task_logger(self, text: str):
        return self.matcher.clickup_user.api.task_logger(
            text=text, task_id=self.task_id
            )

    def comment_task(self, **data):
        return self.matcher.clickup_user.api.comment_task(
            task_id=self.task_id, **data
            )

    def update_task(self, **data):
        return self.matcher.clickup_user.api.update_task(
            task_id=self.task_id, **data
            )

    def update_task_from_event(self, event: dict = None) -> dict:
        if event is None:
            event = self.event
        name = event.get('summary', '(No title)')
        self.comment_task(
            comment=[
                {
                    'text': 'Updating task from changed event ',
                    'attributes': {}
                    },
                {
                    'text': f'{name}',
                    'attributes': {
                        'link': event['htmlLink']
                        }
                    },
                ]
            )
        data = {'name': name}
        if self.sync_description is SYNC_GOOGLE_CALENDAR_DESCRIPTION:
            if 'description' in event:
                data['markdown_description'] = markdownify(
                    event['description']
                    )
        elif self.sync_description is not None:
            self.task_logger(
                'Description will not be synced to google calendar anymore'
                )
            self.sync_description = None
        (start_date, due_date) = \
            self.matcher.user.profile.google_calendar.event_bounds(event)
        # TODO check if dates have been changed before updating them
        task = self.update_task(
            start_date=start_date, due_date=due_date, **data
            )
        self.start = make_aware_datetime(start_date)
        self.end = make_aware_datetime(due_date)
        return task

    def update_event(self, **data):
        return self.matcher.user.profile.google_calendar.update_event(
            calendarId=self.matcher.calendar_id,
            eventId=self.event_id,
            **data,
            )

    def update_event_from_task_history(self, history_items: list):
        data = {}
        # Iterate accross changes
        for i in history_items:
            # Avoid circular updates
            if i.get('after', None) == i.get('before', None):
                continue
            field = i['field']
            # Handle name changes
            if field == 'name':
                data['summary'] = i['after']
            # Handle description changes
            elif field == 'content':
                if self.sync_description is SYNC_CLICKUP_DESCRIPTION:
                    data['description'] = self.task['description']
                elif self.sync_description is not None:
                    self.task_logger(
                        '''Description will not be synced from google calendar
                        anymore'''
                        )
                    self.sync_description = None
            # Handle date changes
            elif field in ['due_date', 'start_date']:
                # Webhook sends utc miliseconds timestamp or None
                _date = i['after']
                if _date:
                    _date = datetime.fromtimestamp(int(_date) / 1000)
                    _date = pytz.utc.localize(_date)
                    # If "due_date_time" is false, the date has no time
                    if not i['data'][f'{field}_time']:
                        _date = _date.date()
                # Save the data to update the event
                if field == 'due_date':
                    data['end_time'] = _date
                else:
                    data['start_time'] = _date
            # Handle sync cancelation
            elif field == 'tag_removed':  # Check if sync tag was removed
                for tag in i.get('after', None) or []:
                    if tag['name'] == SYNCED_TASK_TAG:
                        break
                else:  # Delete event if the sync is cancelled from the task
                    return self.delete(with_event=True)
        # Perform the update
        if data:
            # Update the synced event
            end = data.get('end_time', self.end)
            # Task due date was removed, stop sync
            if not end:
                self.delete(with_event=True)
                return False
            self.end = make_aware_datetime(end)
            # Task start_time was removed, set use the end time
            start = data.get('start_time', self.start)
            if not start:
                start = self.end
            if type(end) is date:
                start = start.date()
            data['start_time'] = start
            self.start = make_aware_datetime(start)
            try:
                return self.update_event(**data)
            except Exception as e:
                logger.error(data)
                raise e
        return False

    @classmethod
    def create(cls, matcher, match, *, event=None, task=None) -> 'SyncedEvent':
        if event and task is None:
            (task, start, end) = matcher._create_task_from_event(event, match)
            task_id = task['id']
            event_id = event['id']
            sync_description = SYNC_GOOGLE_CALENDAR_DESCRIPTION
        elif task and event is None:
            (event, start, end) = matcher._create_event_from_task(task, match)
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

    def delete_task(self, task_id: str = None) -> dict:
        if task_id is None:
            task_id = self.task_id
        if task_id:
            return self.matcher._delete_task(task_id=task_id)

    def delete_event(self, event_id: str = None) -> dict:
        if event_id is None:
            event_id = self.event_id
        if event_id:
            return self.matcher._delete_event(event_id=event_id)

    def delete(self, *args, with_task=False, with_event=False, **kwargs):
        task_id = self.task_id
        event_id = self.event_id
        out = super().delete(*args, **kwargs)
        if with_event:
            self.delete_event(event_id=event_id)
            try:
                self.task_logger('Deleted synced google calendar event')
            except Exception as e:
                logger.error('Failed logging to task', exc_info=e)
        if with_task:
            self.delete_task(task_id=task_id)
        elif task_id:
            self.matcher.clickup_user.remove_sync_tag(task_id)
        return out