from django.contrib import admin

from gcal2clickup.models import Matcher, GoogleCalendarWebhook, ClickupWebhook, SyncedEvent


@admin.register(Matcher)
class MatcherAdmin(admin.ModelAdmin):
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        return Matcher.objects.filter(user=request.user) or qs.none()


@admin.register(GoogleCalendarWebhook)
class GoogleCalendarWebhookAdmin(admin.ModelAdmin):
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