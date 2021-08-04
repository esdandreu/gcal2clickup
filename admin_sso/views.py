from django.contrib.auth import authenticate, login, user_login_failed
from django.http import HttpResponseRedirect
from django.urls import reverse

from google_auth_oauthlib.flow import Flow

from app import settings

client_config = {
    'web': {
        "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
        "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
        "scope": "email",
        }
    }
if settings.GOOGLE_OAUTH_AUTH_URI:
    client_config['web']["auth_uri"] = settings.GOOGLE_OAUTH_AUTH_URI

if settings.GOOGLE_OAUTH_TOKEN_URI:
    client_config['web']["token_uri"] = settings.GOOGLE_OAUTH_TOKEN_URI

if settings.GOOGLE_OAUTH_REVOKE_URI:
    client_config['web']["revoke_uri"] = settings.GOOGLE_OAUTH_REVOKE_URI

SCOPES = [
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    'openid',
    ]


# Utility function
def get_redirect_uri(request) -> str:
    return request.build_absolute_uri(reverse("admin:admin_sso_profile_end"))


def start(request):
    # Use the environemental variables to identify the application
    # requesting authorization. The client ID, client secret and access
    # scopes are required.
    flow = Flow.from_client_config(client_config, SCOPES)

    # Indicate where the API server will redirect the user after the user
    # completes the authorization flow. The redirect URI is required. The
    # value must exactly match one of the authorized redirect URIs for the
    # OAuth 2.0 client, which you configured in the API Console. If this
    # value doesn't match an authorized URI, you will get a
    # 'redirect_uri_mismatch' error.
    flow.redirect_uri = get_redirect_uri(request)

    # Generate URL for request to Google's OAuth 2.0 server. Use kwargs to
    # set optional request parameters.
    authorization_url, state = flow.authorization_url(
        # Enable offline access so that you can refresh an access token
        # without re-prompting the user for permission. Recommended for web
        # server apps.
        access_type='offline',
        # Enable incremental authorization. Recommended as a best practice.
        include_granted_scopes='true'
        )

    return HttpResponseRedirect(authorization_url)


def end(request):
    flow = Flow.from_client_config(client_config, SCOPES)
    flow.redirect_uri = get_redirect_uri(request)

    authorization_response = request.build_absolute_uri()

    # Handle localhost in DEBUG mode
    if settings.DEBUG:
        authorization_response = authorization_response.replace(
            'http://127.0.0.1:8000', 'https://127.0.0.1:8000'
            )
        print(authorization_response)

    flow.fetch_token(authorization_response=authorization_response)

    code = request.GET.get("code", None)
    if not code:
        return HttpResponseRedirect(reverse("admin:index"))
    try:
        credentials = flow.credentials
    except Exception:
        # TODO add an error message, this doesn't work
        user_login_failed.send(sender=__name__, request=request)
        return HttpResponseRedirect(reverse("admin:index"))

    if credentials.id_token is not None:
        user = authenticate(
            request, google_auth_credentials=credentials.__dict__
            )
        if user and user.is_active:
            login(request, user)
            return HttpResponseRedirect(reverse("admin:index"))

    # if anything fails redirect to admin:index
    # TODO add an error message
    return HttpResponseRedirect(reverse("admin:index"))
