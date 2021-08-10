from django.contrib import admin
from django.contrib import messages

from gcal2clickup.forms import matcher_form_factory
from gcal2clickup.models import (
    ClickupWebhook, Matcher, GoogleCalendarWebhook, ClickupUser, SyncedEvent
    )


class UserModelAdmin(admin.ModelAdmin):
    def get_list_display(self, request):
        # Add user if superuser
        if request.user.is_superuser:
            return ['get_user'] + self.list_display
        return self.list_display

    @admin.display(ordering='user', description='User')
    def get_user(self, obj):
        return obj.user.username

    def get_queryset(self, request):
        # Restrict to user
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return self.model.objects.filter(user=request.user) or qs.none()


@admin.register(GoogleCalendarWebhook)
class GoogleCalendarWebhookAdmin(UserModelAdmin):
    list_display = ['get_calendar', 'checked_at']
    actions = ['check_events', 'delete_selected']
    readonly_fields = ['checked_at']

    @admin.action(description='Check updated events')
    def check_events(modeladmin, request, queryset):
        for obj in queryset:
            created, updated = obj.check_events()
            messages.add_message(
                request, messages.INFO,
                f'''Checked {obj}: Created {created} synced events, 
                updated {updated} existing ones'''
                )

    @admin.display(ordering='calendar', description='Calendar')
    def get_calendar(self, obj):
        return obj.calendar[1]


@admin.register(ClickupUser)
class ClickupUserAdmin(UserModelAdmin):
    list_display = ['get_username']
    actions = ['check_webhooks', 'delete_selected']

    @admin.action(description='Check webhooks')
    def check_webhooks(modeladmin, request, queryset):
        for obj in queryset:
            created = obj.check_webhooks()
            messages.add_message(
                request, messages.INFO,
                f'Created {created} clickup webhooks for {obj.username}'
                )

    @admin.display(ordering='username', description='Username')
    def get_username(self, obj):
        return obj.username

    def get_form(self, request, obj, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        # Add user
        if not request.user.is_superuser:
            form.base_fields['user'].initial = request.user
            form.base_fields['user'].disabled = True
        return form


@admin.register(ClickupWebhook)
class ClickupWebhookAdmin(admin.ModelAdmin):
    list_display = ['get_clickup_user', 'get_team']

    def get_list_display(self, request):
        # Add user if superuser
        if request.user.is_superuser:
            return ['get_user'] + self.list_display
        return self.list_display

    @admin.display(ordering='user', description='User')
    def get_user(self, obj):
        return obj.clickup_user.user.username

    @admin.display(ordering='clickup_user', description='Clickup User')
    def get_clickup_user(self, obj):
        return obj.clickup_user

    @admin.display(ordering='workspace', description='Workspace')
    def get_team(self, obj):
        return obj.team

    def get_queryset(self, request):
        # Restrict to user
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return self.model.objects.filter(clickup_user__user=request.user
                                         ) or qs.none()


@admin.register(Matcher)
class MatcherAdmin(UserModelAdmin):
    list_display = [
        '_name_regex', '_description_regex', 'get_calendar', '_tags',
        'get_checked_at'
        ]
    actions = ['check_events', 'delete_selected']

    @admin.action(description='Check updated events')
    def check_events(modeladmin, request, queryset):
        for obj in queryset.google_calendar_webhooks:
            (created, updated) = obj.check_events()
            messages.add_message(
                request, messages.INFO,
                f'''Checked {obj}: Created {created} synced events, 
                updated {updated} existing ones'''
                )

    @admin.display(ordering='calendar', description='Calendar')
    def get_calendar(self, obj):
        return obj.google_calendar_webhook.calendar[1]

    @admin.display(ordering='checked_at', description='Checked at')
    def get_checked_at(self, obj):
        return obj.google_calendar_webhook.checked_at

    def get_form(self, request, obj, **kwargs):
        if request.user.is_superuser:
            return super().get_form(request, obj, **kwargs)
        # Add user and choices for the calendar and list
        opt = {}
        if obj:
            opt['calendar_initial'] = obj.google_calendar_webhook.calendar_id
            opt['list_initial'] = obj.list_id
        return matcher_form_factory(
            user=request.user,
            calendar_choices=request.user.profile.calendar_choices,
            list_choices=request.user.profile.list_choices,
            **opt
            )

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
        print('Hello world')
        clickup_user_pk, obj.list_id = form.data['clickup_list'].split(',')
        obj.clickup_user = ClickupUser.objects.get(pk=clickup_user_pk)
        print(obj.clickup_user)
        super().save_model(request, obj, form, change)


@admin.register(SyncedEvent)
class SyncedEventAdmin(admin.ModelAdmin):
    list_display = ['task_id', 'event_id', 'start', 'end']
    ordering = ['start', 'end']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return SyncedEvent.objects.filter(matcher__user=request.user
                                          ) or qs.none()
