from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


@csrf_exempt
def google_calendar_endpoint(request):
    print(request)
    print(request.body)
    return HttpResponse('Hello wolrd')
