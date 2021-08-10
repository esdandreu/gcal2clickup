from django.http import HttpResponse
from django.http.response import HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from gcal2clickup.models import GoogleCalendarWebhook, ClickupWebhook, SyncedEvent

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
        clickup = ClickupWebhook.objects.get(pk=body['webhook_id']).api
    except ClickupWebhook.DoesNotExist:
        return HttpResponse('Unauthorized', status=401)
    task_id = body['task_id']
    try:
        synced_event = SyncedEvent.objects.get(task_id=task_id)
    except SyncedEvent.DoesNotExist:
        synced_event = None
    event = body['event']
    # fields to watch out
    # if the synced_event does not exists
    # "tag" if "google_calendar" added create event
    # if the synced_event exists
    # "d"
    if event == 'taskCreated':
        # TODO does it have
        pass
    elif event == 'taskUpdated':
        pass
    elif event == 'taskDeleted':
        # Delete event
        pass
    elif event == 'taskMoved':
        pass
    else:
        return HttpResponse('Unauthorized', status=401)
    return HttpResponse('Hello wolrd')

