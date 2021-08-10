from django.http import HttpResponse
from django.http.response import HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from gcal2clickup.models import GoogleCalendarWebhook, ClickupUser

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
    user_id = body['history_items']['user']['id']
    try:
        clickup = ClickupUser.objects.get(pk=user_id).api
    except ClickupUser.DoesNotExist:
        return HttpResponse('Unauthorized', status=401)
    event = body['event']
    if event == 'taskCreated':
        pass
    elif event == 'taskUpdated':
        pass
    elif event == 'taskDeleted':
        pass
    elif event == 'taskMoved':
        pass
    else:
        return HttpResponse('Unauthorized', status=401)
    # "taskCreated",
    #         "taskUpdated",
    #         "taskDeleted",
    #         "taskMoved",
    return HttpResponse('Hello wolrd')

