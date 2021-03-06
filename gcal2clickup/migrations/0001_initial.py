# Generated by Django 3.2.5 on 2021-08-10 10:32

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import sort_order_field.fields
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ClickupUser',
            fields=[
                ('id', models.PositiveIntegerField(editable=False, primary_key=True, serialize=False)),
                ('token', models.CharField(blank=True, help_text='Check <a\n            href=https://docs.clickup.com/en/articles/1367130-getting-started-with-the-clickup-api#personal-api-key>\n            how to find the personal API key</a>', max_length=255, verbose_name='Clickup personal API key')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='ClickupWebhook',
            fields=[
                ('webhook_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ],
        ),
        migrations.CreateModel(
            name='GoogleCalendarWebhook',
            fields=[
                ('calendar_id', models.CharField(max_length=256, unique=True)),
                ('channel_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('resource_id', models.CharField(editable=False, max_length=256)),
                ('expiration', models.DateTimeField()),
                ('checked_at', models.DateTimeField(editable=False, help_text='Last time that the given calendar has been checked for\n            updated events', null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Matcher',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('list_id', models.CharField(help_text='Clickup list.', max_length=64)),
                ('_tags', models.CharField(blank=True, help_text='Clickup tag name that will be added to matched events.\n            One can add more than one tag by separating them with commas', max_length=64, null=True)),
                ('_name_regex', models.CharField(blank=True, help_text='Regular expression that will be used with the event name\n            in order to decide if a calendar event should be synced with a\n            clickup task', max_length=1024, null=True)),
                ('_description_regex', models.CharField(blank=True, help_text='Regular expression that will be used with the event description\n            in order to decide if a calendar event should be synced with a\n            clickup task', max_length=1024, null=True)),
                ('order', sort_order_field.fields.SortOrderField(db_index=True, default=0, verbose_name='Order')),
                ('clickup_user', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='gcal2clickup.clickupuser')),
                ('google_calendar_webhook', models.ForeignKey(editable=False, on_delete=django.db.models.deletion.CASCADE, to='gcal2clickup.googlecalendarwebhook')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ('user__username', 'order'),
                'unique_together': {('user', 'list_id')},
            },
        ),
        migrations.CreateModel(
            name='SyncedEvent',
            fields=[
                ('task_id', models.CharField(max_length=64, primary_key=True, serialize=False)),
                ('event_id', models.CharField(max_length=64)),
                ('start', models.DateTimeField()),
                ('end', models.DateTimeField()),
                ('sync_description', models.BooleanField(null=True)),
                ('matcher', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gcal2clickup.matcher')),
            ],
        ),
    ]
