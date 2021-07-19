from django.conf.urls import url
from django.contrib import admin

from admin_sso import settings
from admin_sso.models import Assignment


class AssignmentAdmin(admin.ModelAdmin):
    list_display = ["__str__", "user", "weight"]
    raw_id_fields = ["user"]

    def get_urls(self):
        from admin_sso.views import start, end

        info = (self.model._meta.app_label, self.model._meta.model_name)
        return [
            url(r"^start/$", start, name="%s_%s_start" % info),
            url(r"^end/$", end, name="%s_%s_end" % info),
        ] + super(AssignmentAdmin, self).get_urls()


admin.site.register(Assignment, AssignmentAdmin)


if settings.DJANGO_ADMIN_SSO_ADD_LOGIN_BUTTON:
    admin.site.login_template = "admin_sso/login.html"
