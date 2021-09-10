import unittest

from django.test import Client
from django.contrib.auth.models import User

from gcal2clickup.models import (
    GoogleCalendarWebhook, ClickupUser, Matcher, SyncedEvent, SYNCED_TASK_TAG
    )

from time import sleep
from datetime import datetime, timedelta, timezone


class TestBase(unittest.TestCase):
    event = None
    task = None
    synced_event = None

    @classmethod
    def setUpClass(cls):
        for user in User.objects.all():
            if (
                user.clickupuser_set.exists()
                and user.profile.google_auth_refresh_token
                ):
                cls.user = user
                break
        else:
            raise unittest.SkipTest('No User is usable to test with')
        # Set the user as inactive
        cls.user.is_active = False
        # Create a matcher with the personal calendar and the first list
        calendar_id = cls.user.username
        try:
            google_calendar_webhook = GoogleCalendarWebhook.objects.get(
                calendar_id=calendar_id,
                )
        except GoogleCalendarWebhook.DoesNotExist:
            google_calendar_webhook = GoogleCalendarWebhook.create(
                user=cls.user,
                calendarId=calendar_id,
                )
        cu_pk, list_id = cls.user.profile.list_choices[0][0].split(',')
        clickup_user = ClickupUser.objects.get(pk=cu_pk)
        cls.matcher = Matcher(
            user=user,
            google_calendar_webhook=google_calendar_webhook,
            clickup_user=clickup_user,
            list_id=list_id,
            _name_regex='TEST',
            )
        cls.matcher.save()
        # Define start and end dates within tomorrow
        cls.end = datetime.now(timezone.utc) + timedelta(days=1)
        cls.start = cls.end - timedelta(hours=1)

    @classmethod
    def tearDownClass(cls):
        # Let some time to ignore the webhooks requests
        sleep(1)
        # Delete the test matcher
        cls.matcher.delete()
        # Get the user and set it back as active
        cls.user.is_active = True

    # def setUp(self):
    # print('setUp')

    def tearDown(self):
        # Deactivate the webhooks
        self.user.is_active = False
        # Delete event in google calendar
        if self.event:
            self.matcher._delete_event(self.event['id'])
        # Delete task in clickup
        if self.task:
            self.matcher._delete_task(self.task['id'])
        # Delete synced event
        if self.synced_event:
            self.synced_event.delete(
                with_task=not self.task,
                with_event=not self.event,
                )

    def test_google_calendar_to_clickup(self):
        # Create event
        self.event = self.matcher._create_event(
            start_time=self.start,
            end_time=self.end,
            summary='TEST gcal2clickup',
            description='My test description',
            )
        # Create synced event from task
        self.synced_event = SyncedEvent.create(
            matcher=self.matcher, match=None, event=self.event
            )
        # Assert task information
        self.task = self.synced_event.task
        self.assertEqual(self.task['name'], 'TEST gcal2clickup')
        self.assertEqual(self.task['description'], 'My test description\n')
        # Change event
        self.synced_event.update_event(
            summary='CHANGED TEST gcal2clickup',
            description='My new test description'
            )
        self.event = self.synced_event.event
        # Update task from event
        self.synced_event.update_task_from_event(self.event)
        # Assert task information
        self.task = self.synced_event.task
        self.assertEqual(self.task['name'], 'CHANGED TEST gcal2clickup')
        self.assertEqual(self.task['description'], 'My new test description\n')

    def test_clickup_to_google_calendar(self):
        # Create task
        self.task = self.matcher._create_task(
            start_date=self.start,
            due_date=self.end,
            assignees=[self.matcher.clickup_user.id],
            name='TEST clickup2gcal',
            tags=[SYNCED_TASK_TAG],
            markdown_description='My test description',
            )
        # Create synced event from task
        self.synced_event = SyncedEvent.create(
            matcher=self.matcher, match=None, task=self.task
            )
        # Assert event information
        self.event = self.synced_event.event
        self.assertEqual(self.event['summary'], 'TEST clickup2gcal')
        self.assertEqual(self.event['description'], 'My test description\n')
        # Change task
        self.synced_event.update_task(
            name='CHANGED TEST clickup2gcal',
            description='My new test description'
            )
        self.task = self.synced_event.task