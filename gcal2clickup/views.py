from django.http import HttpResponse


def google_calendar_endpoint(request):
    print(request)
    print(str(request))
    return HttpResponse('Hello wolrd')


