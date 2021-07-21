from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def google_calendar_endpoint(request):
    state = request.headers.get('X-Goog-Resource-State', None)
    if state:
        watcher_id = request.headers['X-Goog-Channel-Id']
        watcher_id_2 = request.headers['X-Goog-Resource-Id']
        # TODO Save the webhook data
        # TODO check events
        # TODO Create or update clickup task
        # TODO Delete clickup task or ignore
        print('GOOGLE CALENDAR')
        print(request.headers)
        # X-Goog-Channel-Id is the id provided to watch
        # X-Goog-Resource-Id is the event
        return HttpResponse('Done')
    return HttpResponse('Hello wolrd')

@csrf_exempt
def clickup_endpoint(request):
    print('CLICKUP!')
    print(request.body)
    print(request.POST)
    print(request.META)
    print(request.headers)
    return HttpResponse('Hello wolrd')
