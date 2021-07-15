from django.http import HttpResponse
from .settings import BASE_DIR
from gcal2clickup.gcal import Gcal


def google_verification(request):
    f = open(BASE_DIR / 'google_verification.html', 'r')
    return HttpResponse(f.read())


def oauth_redirect_uri(request):
    print(request.build_absolute_uri())
    flow = Gcal.credentials_flow()
    flow.fetch_token(authorization_response=request.build_absolute_uri())
    print(flow.credentials)
    return HttpResponse('Hello wolrd')