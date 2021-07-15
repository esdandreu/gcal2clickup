from django.http import HttpResponse


def google_calendar_endpoint(request):
    print(request)
    return HttpResponse('Hello wolrd')


