from django.contrib import admin

from gcal2clickup.forms import MatcherForm
from gcal2clickup.models import Matcher, GoogleCalendarWebhook, ClickupWebhook, SyncedEvent


@admin.register(Matcher)
class MatcherAdmin(admin.ModelAdmin):
    form = MatcherForm
    list_display = [
        'get_user', '_name_regex', '_description_regex', 'get_calendar',
        'get_checked_at'
        ]
    actions = ['check_events', 'delete_selected']

    @admin.display(ordering='user', description='User')
    def get_user(self, obj):
        return obj.user.username

    @admin.display(ordering='checked_at', description='Checked at')
    def get_checked_at(self, obj):
        return obj.google_calendar_webhook.checked_at

    @admin.display(ordering='calendar', description='Calendar')
    def get_calendar(self, obj):
        return obj.google_calendar_webhook.calendar[0]

    @admin.action(
        description=
        'Check the related google calendar webhooks for updated events'
        )
    def check_events(modeladmin, request, queryset):
        for obj in queryset:
            obj.google_calendar_webhook.check_events()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        return Matcher.objects.filter(user=request.user) or qs.none()

    def get_form(self, request, obj, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # TODO add dynamic calendar_id and set user already if is not superuser
        print(form)
        return form

    def save_model(self, request, obj, form, change):
        calendar_id = form.data['calendar_id']
        if (
            getattr(self, 'google_calendar_webhook', None) is None
            or obj.google_calendar_webhook.calendar_id != calendar_id
            ):
            # get_or_create with a custom create method
            try:
                obj.google_calendar_webhook = GoogleCalendarWebhook.objects.get(
                    calendar_id=calendar_id,
                    )
            except GoogleCalendarWebhook.DoesNotExist:
                obj.google_calendar_webhook = GoogleCalendarWebhook.create(
                    user=obj.user,
                    calendarId=calendar_id,
                    )
        super().save_model(request, obj, form, change)


@admin.register(GoogleCalendarWebhook)
class GoogleCalendarWebhookAdmin(admin.ModelAdmin):
    list_display = ['get_user', 'calendar_id']
    actions = ['check_events', 'delete_selected']

    @admin.display(ordering='user', description='User')
    def get_user(self, obj):
        return obj.user.username

    @admin.action(
        description=
        'Check the calendars through the related matchers for updated events'
        )
    def check_events(modeladmin, request, queryset):
        for obj in queryset:
            obj.check_events()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        return GoogleCalendarWebhook.objects.filter(user=request.user
                                                    ) or qs.none()


@admin.register(ClickupWebhook)
class ClickupWebhookAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        return ClickupWebhook.objects.filter(user=request.user) or qs.none()


@admin.register(SyncedEvent)
class SyncedEventAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        return SyncedEvent.objects.filter(user=request.user) or qs.none()