from django.http import HttpResponse
from django.http.response import HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from gcal2clickup.models import GoogleCalendarWebhook, ClickupWebhook, SyncedEvent
from app.settings import SYNCED_TASK_TAG

import logging
import json


@csrf_exempt
def google_calendar_endpoint(request):
    state = request.headers.get('X-Goog-Resource-State', None)
    if state:
        channel_id = request.headers['X-Goog-Channel-Id']
        resource_id = request.headers['X-Goog-Resource-Id']
        try:
            webhook = GoogleCalendarWebhook.objects.get(
                channel_id=channel_id, resource_id=resource_id
                )
        except GoogleCalendarWebhook.DoesNotExist:
            # ? Try to stop the webhook?
            logging.warning(
                f'Google Calendar notification not recognized: '
                f'{request.headers}'
                )
            return HttpResponseForbidden()
        webhook.check_events()
        return HttpResponse('Done')
    return HttpResponse('Hello wolrd')


@csrf_exempt
def clickup_endpoint(request):
    print('CLICKUP!')
    print(request.body)
    body = json.loads(request.body)
    try:
        webhook = ClickupWebhook.objects.get(pk=body['webhook_id'])
    except ClickupWebhook.DoesNotExist:
        return HttpResponse('Unauthorized', status=401)
    task_id = body['task_id']
    event = body['event']
    items = body['history_items']
    try:
        synced_event = SyncedEvent.objects.get(task_id=task_id)
        if event == 'taskDeleted':
            synced_event.delete(with_event=True)
        else:
            synced_event.update_event(items)
    except SyncedEvent.DoesNotExist:
        # Was sync tag added?
        if event != 'taskDeleted' and ClickupWebhook.is_sync_tag_added(items):
            webhook.check_task(task_id=webhook)
    return HttpResponse('Hello wolrd')
