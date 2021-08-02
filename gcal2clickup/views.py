from django.http import HttpResponse
from django.http.response import HttpResponseForbidden
from django.views.decorators.csrf import csrf_exempt

from gcal2clickup.models import GoogleCalendarWebhook

import logging


@csrf_exempt
def google_calendar_endpoint(request):
    state = request.headers.get('X-Goog-Resource-State', None)
    if state:
        channel_id = request.headers['X-Goog-Channel-Id']
        resource_id = request.headers['X-Goog-Resource-Id']
        try:
            webhook = GoogleCalendarWebhook.get(
                channel_id=channel_id, resource_id=resource_id
                )
        except GoogleCalendarWebhook.DoesNotExist:
            # ? Try to stop the webhook?
            logging.warnign(
                f'Google Calendar notification not recognized: '
                f'{request.headers}'
                )
            return HttpResponseForbidden()
        calendarId = webhook.matcher.calendar_id
        print('GOOGLE CALENDAR')
        print(calendarId)
        # TODO check events
        # TODO Create or update clickup task
        # TODO Delete clickup task or ignore
        return HttpResponse('Done')
    return HttpResponse('Hello wolrd')


@csrf_exempt
def clickup_endpoint(request):
    print('CLICKUP!')
    print(request.body)
    return HttpResponse('Hello wolrd')


# If due date is at 2:00:00 AM then it is the whole day

# {
#     "endpoint": "https://gcal2clickup.herokuapp.com/api/clickup/",
#     "events": [
#         "taskCreated",
#         "taskUpdated",
#         "taskDeleted",
#         "taskMoved",
#     ]
# }