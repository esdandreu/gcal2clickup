from django.conf.urls import url
from django.contrib import admin

from admin_sso import settings
from admin_sso.models import Profile

from app.utils import readme_image_url

if settings.GOOGLE_OAUTH_ADD_LOGIN_BUTTON:
    admin.site.login_template = "admin_sso/login.html"


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    # yapf: disable
    fieldsets = [
        [None, {
            'fields': ('user', 'clickup_pk', ),
            # 'description': f'<img src="{readme_image_url("google_calendar_to_clickup.drawio.svg")}" alt="My image">',
            }],
        ['Google Auth', {
            'fields': ('google_auth_token', 'google_auth_refresh_token', ),
            'classes': ('collapse', )
            }]
        ]
    # yapf: enable
    readonly_fields = [
        'google_auth_token',
        'google_auth_refresh_token',
        ]
    list_display = ["__str__"]

    def get_urls(self):
        from admin_sso.views import start, end

        info = (self.model._meta.app_label, self.model._meta.model_name)
        return [
            url(r"^start/$", start, name="%s_%s_start" % info),
            url(r"^end/$", end, name="%s_%s_end" % info),
            ] + super(ProfileAdmin, self).get_urls()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs

        return Profile.objects.filter(user=request.user) or qs.none()