from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from gcal2clickup.google_calendar import GoogleCalendar


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # TODO Validate always starts with pk
    clickup_pk = models.CharField(blank=True, max_length=255)
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


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()