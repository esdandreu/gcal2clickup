from django.conf import settings
from django.utils.translation import gettext_lazy as _


ASSIGNMENT_ANY = 0
ASSIGNMENT_MATCH = 1
ASSIGNMENT_EXCEPT = 2
ASSIGNMENT_CHOICES = (
    (ASSIGNMENT_ANY, _("any")),
    (ASSIGNMENT_MATCH, _("matches")),
    (ASSIGNMENT_EXCEPT, _("don't match")),
)

GOOGLE_OAUTH_ADD_LOGIN_BUTTON = getattr(
    settings, "GOOGLE_OAUTH_ADD_LOGIN_BUTTON", True
)

AUTH_USER_MODEL = getattr(settings, "AUTH_USER_MODEL", "auth.User")

GOOGLE_OAUTH_CLIENT_ID = getattr(
    settings, "GOOGLE_OAUTH_CLIENT_ID", None
)
GOOGLE_OAUTH_CLIENT_SECRET = getattr(
    settings, "GOOGLE_OAUTH_CLIENT_SECRET", None
)

GOOGLE_OAUTH_AUTH_URI = getattr(
    settings, "GOOGLE_OAUTH_AUTH_URI", "https://accounts.google.com/o/oauth2/auth"
)
GOOGLE_OAUTH_TOKEN_URI = getattr(
    settings, "GOOGLE_OAUTH_TOKEN_URI", "https://accounts.google.com/o/oauth2/token"
)
GOOGLE_OAUTH_REVOKE_URI = getattr(
    settings,
    "GOOGLE_OAUTH_REVOKE_URI",
    "https://accounts.google.com/o/oauth2/revoke",
)
