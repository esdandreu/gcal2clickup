from django.http import HttpResponse


def google_calendar_endpoint(request):
    print(request)
    print(request.body)
    return HttpResponse('Hello wolrd')


