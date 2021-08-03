from django.core.management.base import BaseCommand, CommandError
from admin_sso.models import Profile


class Command(BaseCommand):
    def handle(self, *args, **options):
        for profile in Profile.objects.filter(user__is_active=True):
            profile.refresh_gooogle_calendar_webhooks()
            # gcal = user.profile.google_calendar
            # # print(gcal)
            # # calendars = gcal.list_calendars
            # # print(calendars)
            # # _id = str(uuid.uuid1())
            # # print(_id)
            # # watch_result = gcal.add_events_watch(
            # #     calendarId='esdandreu@gmail.com',
            # #     id=_id,
            # #     address='https://gcal2clickup.herokuapp.com/api/gcal/'
            # #     )
            # # print(watch_result)
            # now = (datetime.datetime.utcnow() - datetime.timedelta(minutes=10)).isoformat() + 'Z' # 'Z' indicates UTC time
            # print(now)
            # events = gcal.events.list(calendarId='primary', updatedMin=now, maxResults=10).execute()
            # print(events)
