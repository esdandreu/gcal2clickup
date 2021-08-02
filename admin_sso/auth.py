from django.contrib.auth import get_user_model, user_login_failed
from django.contrib.auth.models import User, Permission

import jwt

ADD_PERMISSIONS = [
    'Can change profile',
    'Can add matcher',
    'Can change matcher',
    'Can delete matcher',
    'Can change synced_event',
    'Can view google_calendar_webhook',
    'Can view clickup_webhook',
    'Can delete google_calendar_webhook',
    'Can delete clickup_webhook',
    ]


class DjangoSSOAuthBackend(object):
    def get_user(self, user_id):
        cls = get_user_model()
        try:
            return cls.objects.get(pk=user_id)
        except cls.DoesNotExist:
            return None

    def authenticate(self, request, google_auth_credentials={}, **kwargs):

        _id = google_auth_credentials.get('_id_token', None)
        if _id:
            _id = jwt.decode(
                google_auth_credentials['_id_token'],
                options={"verify_signature": False}
                )
            if _id['email_verified']:
                email = _id['email']
                user, created = User.objects.get_or_create(username=email)
                print(user)
                if created:
                    user.email = email
                    user.set_unusable_password()
                    user.is_staff = True
                    user.user_permissions.set(
                        Permission.objects.filter(name__in=ADD_PERMISSIONS)
                        )

                # Save credentials
                user.profile.google_auth_token = \
                    google_auth_credentials.get('token', None)
                user.profile.google_auth_refresh_token = \
                    google_auth_credentials.get('_refresh_token', None)
                user.save()
                return user

        return None
