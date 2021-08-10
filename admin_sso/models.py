from django.db import models
from django.core.cache import cache
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.contrib.auth.models import User, Permission

from gcal2clickup.google_calendar import GoogleCalendar

BASE_PROFILE_PERMISSIONS = [
    'Can add clickup user',
    'Can change clickup user',
    'Can delete clickup user',
    ]

FULL_PROFILE_PERMISSIONS = [
    'Can add matcher',
    'Can change matcher',
    'Can delete matcher',
    'Can view synced event',
    'Can change synced event',
    'Can delete synced event',
    'Can view google calendar webhook',
    'Can view clickup webhook',
    ]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    google_auth_token = models.CharField(
        blank=True, max_length=255, editable=False
        )
    google_auth_refresh_token = models.CharField(
        blank=True, max_length=255, editable=False
        )
    # google_auth_expiry = models.DateTimeField(blank=True, editable=False)
    _google_calendar = None

    def __str__(self):
        return str(self.user)

    @property
    def google_calendar(self):
        if self._google_calendar is None:
            self._google_calendar = GoogleCalendar(
                token=self.google_auth_token,
                refresh_token=self.google_auth_refresh_token
                )
        return self._google_calendar

    @property
    def calendar_choices(self):
        choices = cache.get('cal-' + str(self))
        if choices is None:
            choices = [(c['id'], c['summary'])
                       for c in self.google_calendar.list_calendars()]
            cache.set('cal-' + str(self), choices, 600)
        return choices

    @property
    def list_choices(self):
        choices = []
        for u in self.user.clickupuser_set.all():
            u_choices = cache.get('lst-' + u.token)
            if u_choices is None:
                u_choices = u.list_choices
                cache.set('lst-' + u.token, u_choices, 60)
            choices += u_choices
        return choices

    def save(self, *args, **kwargs):
        permissions = BASE_PROFILE_PERMISSIONS
        # Add full permissions if a clickup account has been linked
        if self.user.clickupuser_set.exists():
            permissions = permissions + FULL_PROFILE_PERMISSIONS
        self.user.user_permissions.set(
            Permission.objects.filter(name__in=permissions)
            )
        super().save(*args, **kwargs)

    def refresh_webhooks(self):
        for webhooks in [
            self.user.google_calendar_webhook_set,
            self.user.clickupuser_set,
            ]:
            for webhook in webhooks:
                webhook.refresh()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()