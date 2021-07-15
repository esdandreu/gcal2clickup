import os

from google_auth_oauthlib.flow import Flow

SCOPES = [
    'https://www.googleapis.com/auth/calendar.readonly',
    'https://www.googleapis.com/auth/calendar.events',
    ]


class Gcal:
    def __init__(access_token=None, refresh_token=None):
        pass

    def authenticate(self, access_token, refresh_token):
        pass

    @staticmethod
    def get_credentials(redirect_uri='http://127.0.0.1:8000/oauth'):
        CLIENT_ID = os.getenv('G_CLIENT_ID')
        CLIENT_SECRET = os.getenv('G_CLIENT_SECRET')
        error_msg = '''Google project credentials should not be empty, see 
            https://github.com/esdandreu/gcal2clickup/tree/main#get-google-credentials'''
        assert CLIENT_ID is not None and CLIENT_SECRET is not None, error_msg
        client_config = {
            "web": {
                "client_id":
                    CLIENT_ID,
                "project_id":
                    "esdandreu",
                "auth_uri":
                    "https://accounts.google.com/o/oauth2/auth",
                "token_uri":
                    "https://oauth2.googleapis.com/token",
                "auth_provider_x509_cert_url":
                    "https://www.googleapis.com/oauth2/v1/certs",
                "client_secret":
                    CLIENT_SECRET,
                "redirect_uris": [redirect_uri]
                }
            }
        flow = Flow.from_client_config(client_config, SCOPES)
        return flow

    def watch(self, id, address, ttl=604800):
        pass