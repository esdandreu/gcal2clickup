from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def google_calendar_endpoint(request):
    # TODO If it is a sync message save the webhook data
    # TODO If it is a notification, check the resource that was changed
    print(request)
    print(request.body)
    print(request.POST)
    print(request.META)
    print(request.headers)
    return HttpResponse('Hello wolrd')
