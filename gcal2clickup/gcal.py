from google_auth_oauthlib.flow import Flow

from app import settings

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


class GoogleCalendar:
    def __init__(access_token=None, refresh_token=None):
        pass

    def authenticate(self, access_token, refresh_token):
        pass

    @staticmethod
    def credentcwfials_flow():
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
        flow.redirect_uri = redirect_uri
        return flow

    @staticmethod
    def get_credentials(redirect_uri='https://127.0.0.1:8000/oauth'):
        flow = GoogleCalendar.credentials_flow(redirect_uri=redirect_uri)

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
        return authorization_url

    def watch(self, id, address, ttl=604800):
        pass