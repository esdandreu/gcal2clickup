from typing import Tuple

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app import settings


class GoogleCalendar:
    def __init__(self, token, refresh_token):
        credentials = Credentials(
            token=token,
            refresh_token=refresh_token,
            token_uri=settings.GOOGLE_OAUTH_TOKEN_URI,
            client_id=settings.GOOGLE_OAUTH_CLIENT_ID,
            client_secret=settings.GOOGLE_OAUTH_CLIENT_SECRET
            )
        self.service = build('calendar', 'v3', credentials=credentials)

    def __getattr__(self, name: str):
        return getattr(self.service, name)()

    def list_calendars(self, **kwargs):
        nextPageToken = True
        while nextPageToken:
            if isinstance(nextPageToken, str):
                kwargs['pageToken'] = nextPageToken
            response = self.service.calendarList().list(**kwargs).execute()
            nextPageToken = response.get('nextPageToken', None)
            for calendar in response['items']:
                yield calendar

    def list_events(self, calendarId, **kwargs):
        nextPageToken = True
        while nextPageToken:
            if isinstance(nextPageToken, str):
                kwargs['pageToken'] = nextPageToken
            response = self.events.list(
                calendarId=calendarId, singleEvents=True, **kwargs
                ).execute()
            nextPageToken = response.get('nextPageToken', None)
            for event in response['items']:
                yield event

    def add_events_watch(self, calendarId, id, address, ttl=604800):
        return self.events.watch(
            calendarId=calendarId,
            body={
                'id': id,
                'address': address,
                'type': 'webhook',
                'params': {
                    'ttl': ttl
                    }
                }
            ).execute()

    def stop_watch(self, id, resourceId):
        return self.channels.stop(id=id, resourceId=resourceId).execute()