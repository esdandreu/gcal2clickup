from django.http import HttpResponse
from .settings import BASE_DIR


def google_verification(request):
    f = open(BASE_DIR / 'google_verification.html', 'r')
    return HttpResponse(f.read())


def oauth_redirect_uri(request):
    print(request)
    return HttpResponse('Hello wolrd')