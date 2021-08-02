from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app import settings

import datetime


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

    def list_calendars(self):
        items = []
        page_token = None
        while True:
            calendar_list = self.service.calendarList().list(
                pageToken=page_token
                ).execute()
            items.extend(calendar_list['items'])
            page_token = calendar_list.get('nextPageToken')
            if not page_token:
                break
        return items

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