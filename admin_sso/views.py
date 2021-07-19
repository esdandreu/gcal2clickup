from pathlib import PureWindowsPath
from django.contrib.auth import authenticate, login
from django.http import HttpResponseRedirect
from django.urls import reverse

from oauth2client.client import OAuth2WebServerFlow, FlowExchangeError
from google_auth_oauthlib.flow import Flow

from app import settings

# TODO delete
flow_kwargs = {
    "client_id": settings.GOOGLE_OAUTH_CLIENT_ID,
    "client_secret": settings.GOOGLE_OAUTH_CLIENT_SECRET,
    "scope": "email",
    }
if settings.GOOGLE_OAUTH_AUTH_URI:
    flow_kwargs["auth_uri"] = settings.GOOGLE_OAUTH_AUTH_URI

if settings.GOOGLE_OAUTH_TOKEN_URI:
    flow_kwargs["token_uri"] = settings.GOOGLE_OAUTH_TOKEN_URI

if settings.GOOGLE_OAUTH_REVOKE_URI:
    flow_kwargs["revoke_uri"] = settings.GOOGLE_OAUTH_REVOKE_URI

flow_override = None

error_msg = '''Google project credentials should not be empty, see 
    https://github.com/esdandreu/gcal2clickup/tree/main#get-google-credentials'''
assert (
    settings.GOOGLE_OAUTH_CLIENT_ID is not None
    and settings.GOOGLE_OAUTH_CLIENT_SECRET is not None
    ), error_msg
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
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    ]


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
    flow.redirect_uri = request.build_absolute_uri(
        reverse("admin:admin_sso_assignment_end")
        )

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
    flow.redirect_uri = request.build_absolute_uri(
        reverse("admin:admin_sso_assignment_end")
        )

    authorization_response = request.get_full_path()

    # Handle localhost in DEBUG mode
    if settings.DEBUG:
        authorization_response = authorization_response.replace(
            'http://127.0.0.1:8000', 'https://127.0.0.1:8000'
            )
        print(authorization_response)

    flow.fetch_token(authorization_response=authorization_response)

    # if flow_override is None:
    #     flow = OAuth2WebServerFlow(
    #         redirect_uri=request.build_absolute_uri(
    #             reverse("admin:admin_sso_assignment_end")
    #             ),
    #         **flow_kwargs
    #         )
    # else:
    #     flow = flow_override

    code = request.GET.get("code", None)
    if not code:
        return HttpResponseRedirect(reverse("admin:index"))
    try:
        credentials = flow.credentials
        print(credentials)
    except FlowExchangeError:
        return HttpResponseRedirect(reverse("admin:index"))

    if credentials.id_token["email_verified"]:
        email = credentials.id_token["email"]
        user = authenticate(request, sso_email=email)
        if user and user.is_active:
            login(request, user)
            return HttpResponseRedirect(reverse("admin:index"))

    # if anything fails redirect to admin:index
    # TODO add an error message
    return HttpResponseRedirect(reverse("admin:index"))
