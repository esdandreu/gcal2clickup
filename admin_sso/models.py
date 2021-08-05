from django.db import models
from django.dispatch import receiver
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.contrib.auth.models import User, Permission

from gcal2clickup.google_calendar import GoogleCalendar
from gcal2clickup.clickup import Clickup

BASE_PROFILE_PERMISSIONS = [
    'Can change profile',
    ]

FULL_PROFILE_PERMISSIONS = [
    'Can add matcher',
    'Can change matcher',
    'Can delete matcher',
    'Can change synced event',
    'Can view google calendar webhook',
    'Can view clickup webhook',
    ]


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # TODO Validate always starts with pk
    clickup_pk = models.CharField(
        blank=True,
        max_length=255,
        verbose_name='Clickup personal API key',
        help_text='''Check <a
            href=https://docs.clickup.com/en/articles/1367130-getting-started-with-the-clickup-api#personal-api-key>
            how to find the personal API key</a>''',
        )
    google_auth_token = models.CharField(
        blank=True, max_length=255, editable=False
        )
    google_auth_refresh_token = models.CharField(
        blank=True, max_length=255, editable=False
        )

    # google_auth_expiry = models.DateTimeField(blank=True, editable=False)

    def __str__(self):
        return str(self.user)

    @property
    def google_calendar(self):
        return GoogleCalendar(
            token=self.google_auth_token,
            refresh_token=self.google_auth_refresh_token
            )

    @property
    def calendar_choices(self):
        return [(c['id'], c['summary'])
                for c in self.google_calendar.list_calendars()]

    @property
    def clickup(self):
        return Clickup(token=self.clickup_pk)

    @property
    def list_choices(self):
        return [(l['id'], self.clickup.repr_list(l))
                for l in self.clickup.list_lists()]

    def save(self, *args, **kwargs):
        permissions = BASE_PROFILE_PERMISSIONS
        if self.clickup_pk:
            permissions = permissions + FULL_PROFILE_PERMISSIONS
        self.user.user_permissions.set(
            Permission.objects.filter(name__in=permissions)
            )
        super().save(*args, **kwargs)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()