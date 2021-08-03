from django.contrib import admin

from gcal2clickup.models import Matcher, GoogleCalendarWebhook, ClickupWebhook, SyncedEvent


@admin.register(Matcher)
class MatcherAdmin(admin.ModelAdmin):
    list_display = [
        'get_user', '_name_regex', '_description_regex',
        'google_calendar_checked_at'
        ]

    @admin.display(ordering='user', description='User')
    def get_user(self, obj):
        return obj.user.username

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        return Matcher.objects.filter(user=request.user) or qs.none()


@admin.register(GoogleCalendarWebhook)
class GoogleCalendarWebhookAdmin(admin.ModelAdmin):
    list_display = ['get_user', 'calendar_id']
    actions = ['check_events', 'delete_selected']

    @admin.display(ordering='user', description='User')
    def get_user(self, obj):
        return obj.user.username
    
    @admin.action(description='Check the calendars through the related matchers for updated events')
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